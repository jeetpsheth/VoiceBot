import os
import json
import base64
import asyncio
import argparse
import audioop
import socket
import threading
import time
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.rest import Client
import websockets
from dotenv import load_dotenv
import uvicorn
import re
from starlette.websockets import WebSocketState

import config
from scenarios import get_scenario
from bug_report import suggest_bugs

load_dotenv()

# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('PHONE_NUMBER_FROM')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain) # Strip protocols and trailing slashes from DOMAIN

PORT = int(os.getenv('PORT', 6060))
SYSTEM_MESSAGE = (
    "You are roleplaying as a real patient on a phone call. "
    "Speak naturally like a normal person, with everyday language and a calm, human tone. "
    "Do not mention AI, testing, prompts, system instructions, or that this is an evaluation. "
    "Stay fully in character throughout the call. "
    "Your goal is to book, change, or ask about a doctor's appointment as a patient would. "
    "If the other side is unclear, ask follow-up questions naturally and continue the conversation."
)
VOICE = 'echo'
TEMPERATURE = float(os.getenv('TEMPERATURE', 0.8))
AUDIO_GAIN = max(0.1, min(4.0, float(os.getenv('AUDIO_GAIN', '1.0'))))
LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'response.audio_transcript.done', 'response.output_text.done',
    'rate_limits.updated', 'response.done', 'session.updated',
    'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started', 'session.created',
    'conversation.item.input_audio_transcription.completed'
]

app = FastAPI()
LAST_REQUESTED_SCENARIO_ID = None


def safe_filename_part(value: str) -> str:
    """Normalize free-form IDs for safe cross-platform filenames."""
    if not value:
        return "unknown"
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return cleaned or "unknown"


def apply_ulaw_gain(base64_ulaw_audio: str) -> str:
    """Apply gain to base64-encoded mu-law audio and return base64 mu-law audio."""
    if AUDIO_GAIN == 1.0:
        return base64_ulaw_audio

    ulaw_bytes = base64.b64decode(base64_ulaw_audio)
    linear_pcm = audioop.ulaw2lin(ulaw_bytes, 2)
    boosted_pcm = audioop.mul(linear_pcm, 2, AUDIO_GAIN)
    boosted_ulaw = audioop.lin2ulaw(boosted_pcm, 2)
    return base64.b64encode(boosted_ulaw).decode('utf-8')


def wait_for_server(host: str, port: int, timeout_sec: float = 20.0) -> bool:
    """Wait until a TCP listener is available on host:port."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.2)
    return False

if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and PHONE_NUMBER_FROM and OPENAI_API_KEY):
    raise ValueError('Missing Twilio and/or OpenAI environment variables. Please set them in the .env file.')

# Initialize Twilio client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@app.websocket('/media-stream')
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    print("Client connected")
    await websocket.accept()

    # Prefer explicit query param, then Twilio customParameters from the first "start" event.
    query_scenario_id = websocket.query_params.get('scenario')
    pending_twilio_events = []
    start_scenario = None

    try:
        first_message = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
        first_data = json.loads(first_message)
        pending_twilio_events.append(first_data)
        if first_data.get('event') == 'start':
            start_params = first_data.get('start', {}).get('customParameters', {}) or {}
            start_scenario = start_params.get('scenario')
    except asyncio.TimeoutError:
        pass
    except Exception as e:
        print(f"Could not inspect initial Twilio event for scenario selection: {e}")

    scenario_id = start_scenario or query_scenario_id or LAST_REQUESTED_SCENARIO_ID or 'schedule_new'
    scenario = get_scenario(scenario_id)

    current_system_message = SYSTEM_MESSAGE
    opener = "Hi, I'm calling about an appointment."
    if scenario:
        current_system_message += (
            f"\n\nSCENARIO ID: {scenario.id}"
            f"\nSCENARIO NAME: {scenario.name}"
            f"\nSCENARIO DETAILS: {scenario.description}"
            "\nStay aligned with this scenario for the entire call."
            "\nDo not switch to appointment scheduling unless the selected scenario is explicitly about scheduling."
            "\nBe varied and natural in wording, but keep the call goal consistent with the selected scenario."
        )
        opener = scenario.opener
    else:
        current_system_message += (
            "\n\nNo scenario was matched. Use a general appointment inquiry and ask clarifying questions."
        )

    print(
        "Resolved scenario selection: "
        f"start={start_scenario}, "
        f"query={query_scenario_id}, "
        f"last_requested={LAST_REQUESTED_SCENARIO_ID}, "
        f"resolved={scenario_id}, "
        f"scenario_found={bool(scenario)}, "
        f"opener={opener}"
    )

    transcript = []
    session_error = None
    last_patient_turn = None

    try:
        async with websockets.connect(
            f"wss://api.openai.com/v1/realtime?model=gpt-realtime&temperature={TEMPERATURE}",
            additional_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
        ) as openai_ws:
            await initialize_session(openai_ws, current_system_message, opener)
            stream_sid = None
            
            async def close_openai_ws_quickly():
                """Close OpenAI websocket without blocking shutdown for long."""
                if openai_ws.state.name != 'OPEN':
                    return
                try:
                    await asyncio.wait_for(openai_ws.close(), timeout=1.0)
                except Exception:
                    pass

            async def receive_from_twilio():
                """Receive audio data from Twilio and send it to the OpenAI Realtime API."""
                nonlocal stream_sid, session_error

                async def process_twilio_event(data):
                    nonlocal stream_sid
                    if data['event'] == 'media' and openai_ws.state.name == 'OPEN':
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": data['media']['payload']
                        }
                        await openai_ws.send(json.dumps(audio_append))
                    elif data['event'] == 'start':
                        stream_sid = data['start']['streamSid']
                        start_params = data.get('start', {}).get('customParameters', {}) or {}
                        start_scenario = start_params.get('scenario')
                        if start_scenario and start_scenario != scenario_id:
                            print(f"Twilio start custom scenario={start_scenario} differs from resolved scenario={scenario_id}")
                        print(f"Incoming stream has started {stream_sid}")

                try:
                    for data in pending_twilio_events:
                        await process_twilio_event(data)

                    async for message in websocket.iter_text():
                        data = json.loads(message)
                        await process_twilio_event(data)
                except WebSocketDisconnect:
                    print("Client disconnected.")
                    await close_openai_ws_quickly()
                except Exception as e:
                    session_error = session_error or f"receive_from_twilio: {e}"
                    print(f"Error in receive_from_twilio: {e}")
                    await close_openai_ws_quickly()

            async def send_to_twilio():
                """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
                nonlocal stream_sid, session_error, last_patient_turn
                try:
                    async for openai_message in openai_ws:
                        response = json.loads(openai_message)
                        event_type = response.get('type')
                        if event_type in LOG_EVENT_TYPES:
                            print(f"Received event: {event_type}", response)
                        if event_type == 'error' and response.get('error', {}).get('code') == 'insufficient_quota':
                            print("\nCRITICAL: OpenAI API quota exceeded. Please check your billing details.\n")
                        if event_type == 'conversation.item.input_audio_transcription.completed':
                            text = response.get('transcript', '')
                            if text:
                                transcript.append({"role": "agent", "text": text})
                                last_patient_turn = None
                                print(f"Agent: {text}")
                        if event_type == 'response.content.done':
                            part = response.get('part', {})
                            text = part.get('transcript', '') or part.get('text', '')
                            if text:
                                if text != last_patient_turn:
                                    transcript.append({"role": "patient", "text": text})
                                    last_patient_turn = text
                                    print(f"Patient: {text}")
                        if event_type in ('response.audio_transcript.done', 'response.output_text.done'):
                            text = response.get('transcript', '') or response.get('text', '')
                            if text:
                                if text != last_patient_turn:
                                    transcript.append({"role": "patient", "text": text})
                                    last_patient_turn = text
                                    print(f"Patient: {text}")
                        if event_type == 'response.done':
                            # Some realtime responses only carry transcript text in response.output content.
                            for item in response.get('response', {}).get('output', []):
                                if item.get('role') != 'assistant':
                                    continue
                                for content in item.get('content', []):
                                    text = content.get('transcript', '') or content.get('text', '')
                                    if text:
                                        if text != last_patient_turn:
                                            transcript.append({"role": "patient", "text": text})
                                            last_patient_turn = text
                                            print(f"Patient: {text}")
                        if event_type == 'session.updated':
                            print("Session updated successfully:", response)
                        if event_type == 'response.output_audio.delta' and response.get('delta'):
                            try:
                                audio_payload = apply_ulaw_gain(response['delta'])
                                audio_delta = {
                                    "event": "media",
                                    "streamSid": stream_sid,
                                    "media": {
                                        "payload": audio_payload
                                    }
                                }
                                await websocket.send_json(audio_delta)
                            except Exception as e:
                                print(f"Error processing audio data: {e}")
                except Exception as e:
                    session_error = session_error or f"send_to_twilio: {e}"
                    print(f"Error in send_to_twilio: {e}")

            async def monitor_connection_state():
                """Exit quickly when either websocket is no longer connected."""
                while True:
                    if websocket.client_state != WebSocketState.CONNECTED:
                        return
                    if openai_ws.state.name != 'OPEN':
                        return
                    await asyncio.sleep(0.2)

            receive_task = asyncio.create_task(receive_from_twilio())
            send_task = asyncio.create_task(send_to_twilio())
            monitor_task = asyncio.create_task(monitor_connection_state())
            done, pending = await asyncio.wait(
                {receive_task, send_task, monitor_task},
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in done:
                exc = task.exception()
                if exc and not isinstance(exc, asyncio.CancelledError):
                    session_error = session_error or str(exc)

            for task in pending:
                task.cancel()

            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
    except Exception as e:
        session_error = str(e)
        print(f"Error in handle_media_stream: {e}")
    finally:
        # Always persist a transcript file, even if the call ended early or errored.
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_scenario_id = safe_filename_part(str(scenario_id))
        filename = f"call_{safe_scenario_id}_{ts}.json"
        config.TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        path = config.TRANSCRIPTS_DIR / filename
        data = {
            "scenario_id": scenario_id,
            "transcript": transcript,
            "timestamp": ts,
            "error": session_error
        }
        transcript_saved = False
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            transcript_saved = True
            print(f"Transcript saved to {path.resolve()}")
        except Exception as e:
            print(f"Failed to save transcript to {path}: {e}")

        bug_report = {
            "scenario_id": scenario_id,
            "timestamp": ts,
            "transcript_path": str(path),
            "bugs": []
        }

        if transcript and transcript_saved:
            try:
                bug_report["bugs"] = suggest_bugs([{"path": str(path), **data}]) or []
            except Exception as e:
                print(f"Failed to generate bug suggestions: {e}")
                bug_report["bugs"] = []

        bug_filename = f"bug_report_{safe_scenario_id}_{ts}.json"
        config.BUGS_DIR.mkdir(parents=True, exist_ok=True)
        bug_path = config.BUGS_DIR / bug_filename
        try:
            with open(bug_path, "w") as f:
                json.dump(bug_report, f, indent=2)
            print(f"Bug report saved to {bug_path.resolve()}")
        except Exception as e:
            print(f"Failed to save bug report to {bug_path}: {e}")

        if not transcript:
            print("\nNo transcript turns captured for this call.")

async def send_initial_conversation_item(openai_ws, opener):
    """Send initial conversation so AI talks first."""
    initial_conversation_item = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": f"Say exactly this as the patient opener: '{opener}'"
                }
            ]
        }
    }
    await openai_ws.send(json.dumps(initial_conversation_item))
    await openai_ws.send(json.dumps({"type": "response.create"}))

async def initialize_session(openai_ws, system_message, opener):
    """Control initial session with OpenAI."""
    session_update = {
        "type": "session.update",
        "session": {
            "type": "realtime",
            "model": "gpt-realtime",
            "output_modalities": ["audio"],
            "audio": {
                "input": {
                    "format": {"type": "audio/pcmu"},
                    "transcription": {
                        "model": os.getenv("INPUT_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")
                    },
                    "turn_detection": {"type": "server_vad"}
                },
                "output": {
                    "format": {"type": "audio/pcmu"},
                    "voice": VOICE
                }              
            },
        
                "instructions": system_message,                        
    }   
    }
    print('Sending session update:', json.dumps(session_update))
    await openai_ws.send(json.dumps(session_update))

    # Have the AI speak first
    await send_initial_conversation_item(openai_ws, opener)


        
async def make_call(phone_number_to_call: str, scenario_id: str):
    """Make an outbound call."""
    global LAST_REQUESTED_SCENARIO_ID
    if not phone_number_to_call:
        raise ValueError("Please provide a phone number to call.")

   
    # Ensure compliance with applicable laws and regulations
    # All of the rules of TCPA apply even if a call is made by AI.
    # Do your own diligence for compliance.

    LAST_REQUESTED_SCENARIO_ID = safe_filename_part(scenario_id)
    safe_scenario = LAST_REQUESTED_SCENARIO_ID
    outbound_twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Connect><Stream url="wss://{DOMAIN}/media-stream?scenario={safe_scenario}">'
        f'<Parameter name="scenario" value="{safe_scenario}" />'
        f'</Stream></Connect></Response>'
        )
    print(f"Placing call with scenario={safe_scenario}")

    call = client.calls.create(
        from_=PHONE_NUMBER_FROM,
        to=phone_number_to_call,
        twiml=outbound_twiml
        )

    await log_call_sid(call.sid)

async def log_call_sid(call_sid):
    """Log the call SID."""
    print(f"Call started with SID: {call_sid}")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Twilio AI voice assistant server.")
    parser.add_argument('--call', required=True, help="The phone number to call, e.g., '--call=+18005551212'")
    parser.add_argument('--scenario', required=True, help="Scenario ID to use")
    parser.add_argument('--no-server', action='store_true', help="Place the call but do not start the local server.")
    args = parser.parse_args()

    phone_number = args.call
    print(
    'Our recommendation is to always disclose the use of AI for outbound or inbound calls.\n'
    'Reminder: All of the rules of TCPA apply even if a call is made by AI.\n'
    'Check with your counsel for legal and compliance advice.'
    )

    print(f"Transcripts directory: {config.TRANSCRIPTS_DIR.resolve()}")
    print(f"Bug reports directory: {config.BUGS_DIR.resolve()}")

    if args.no_server:
        asyncio.run(make_call(phone_number, args.scenario))
    else:
        server_thread = threading.Thread(
            target=uvicorn.run,
            kwargs={"app": app, "host": "0.0.0.0", "port": PORT},
            daemon=True,
        )
        server_thread.start()

        if not wait_for_server("127.0.0.1", PORT):
            raise RuntimeError(f"Server did not start on port {PORT}.")

        asyncio.run(make_call(phone_number, args.scenario))
        server_thread.join()
