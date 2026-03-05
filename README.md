# Pretty Good AI — Voice Patient Bot

Automated voice bot that acts as a **patient** to test an AI agent at **805-439-8008**. It places outbound calls, runs scripted patient scenarios (scheduling, refills, questions), records and transcribes conversations, and helps to document bugs.

## What you need

- **Python 3.9+**
- **Twilio account** (voice-capable number, Account SID, Auth Token)
- **OpenAI API key** (for GPT Model Reasoning)
- **ngrok** so Twilio can reach your local server

## Setup

1. **Clone or copy this repo**, then:

   ```bash
   cd VoiceBot
   python -m venv venv
   venv\Scripts\activate    # Windows
   # source venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```

2. **Configure environment**
   '''bash
   Cp .env.example .env
   '''
    Fill in `env.example` with these(or you can fill in `.env` with these in which case the above copy bash command is not required):

   - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` from [Twilio Console](https://console.twilio.com)
   - `OPENAI_API_KEY` from [OpenAI](https://platform.openai.com/api-keys)
   - `DOMAIN`: your public URL (e.g. `https://abc123.ngrok.io`) — **no trailing slash**

3. **Start the app and expose it**

   Terminal 1:

   ```bash
   ngrok http 6060
   ```

   Terminal 2:

   ```bash
   python voicebot.py --call number --scenario scenario
   ```
   nuber and scenario are placeholders that need to be replaced with the reciever number and one of the available scenarios from the registry.
   Copy the `https://...` URL ngrok shows and set `DOMAIN` in `.env` to that URL (e.g. `BASE_URL=https://abc123.ngrok.io`). Restart `python voicebot.py` if you had already started it before setting `DOMAIN`, or set `DOMAIN` before the first run.
