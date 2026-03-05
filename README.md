Automated voice bot that acts as a **patient** to test an AI agent at **805-439-8008**. It places outbound calls, runs scripted patient scenarios (scheduling, refills, questions), records and transcribes conversations, and helps you document bugs.

## What you need

- **Python 3.9+**
- **Twilio account** (voice-capable number, Account SID, Auth Token)
- **OpenAI API key** (for GPT Model)
- **ngrok** (or another HTTPS tunnel) so Twilio can reach your local server

## Setup

1. **Clone or copy this repo**, then:

   ```bash
   cd path/to/VoiceBot
   python -m venv venv
   venv\Scripts\activate    # Windows
   # source venv/bin/activate   # macOS/Linux
   pip install fastapi uvicorn twilio websockets python-dotenv
   ```

2. **Configure environment**

   ```bash
   cp .env.example .env
   ```
   Fill in these details in the .env.example (or you can directly fill in the details in .env in which case the above cp bash statement is not needed)
   - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`,`PHONE_NUMBER_FROM` from [Twilio Console](https://console.twilio.com)
   - `OPENAI_API_KEY` from [OpenAI](https://platform.openai.com/api-keys)
   - `DOMAIN`: your public URL (e.g. `https://abc123.ngrok.io`) — **no trailing slash**

3. **Start the app and expose it**

   Terminal 1
   ```
   ngrok http 6060
   ```
   Copy the public URL (e.g. 'https://abc123.ngrok.io') and set the `DOMAIN` variable in the .env file.
   Terminal 2
   ```
   cd 'path/to/Project_root'
   python voicebot.py --call number --scenario scenario
   ```
   The number and scenario are placeholders for the receiver number and any scenario from the registry.py file in the scenarios folder. 
   
  
