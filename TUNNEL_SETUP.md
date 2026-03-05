# Tunnel setup for Twilio Media Streams (WebSocket)

## Why ngrok free breaks calls (0–4 sec duration)

On **ngrok free** (`*.ngrok-free.dev`), the first request to your URL often gets a **browser warning page** (HTML) instead of being forwarded. When Twilio tries to open the **WebSocket** to `wss://your-url/media`, it receives that HTML instead of a WebSocket handshake, so the media stream never connects and the call drops quickly.

You cannot add the bypass header for **incoming** requests on ngrok free, and Twilio does not send that header.

---

## Best option: Cloudflare Tunnel with free account (STABLE URL)

**This gives you a stable URL that doesn't change!**

### Setup steps:

1. **Create a free Cloudflare account** at https://dash.cloudflare.com/sign-up

2. **Install cloudflared:**
   - **Windows (winget):** `winget install cloudflare.cloudflared`
   - Or download: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

3. **Login to Cloudflare:**
   ```bash
   cloudflared tunnel login
   ```
   This opens your browser to authorize cloudflared.

4. **Create a named tunnel:**
   ```bash
   cloudflared tunnel create voice-bot
   ```
   This creates a tunnel named "voice-bot" (you can use any name).

5. **Create a route (hostname):**
   ```bash
   cloudflared tunnel route dns voice-bot your-subdomain.trycloudflare.com
   ```
   Replace `your-subdomain` with your preferred subdomain (e.g., `my-voice-bot`). This gives you a **stable URL** like `https://my-voice-bot.trycloudflare.com` that won't change.

6. **Run the tunnel:**
   ```bash
   cloudflared tunnel run voice-bot
   ```
   In a separate config file (or use the command), configure it to forward to `localhost:5000`:
   
   Create `~/.cloudflared/config.yml` (or `C:\Users\USER\.cloudflared\config.yml` on Windows):
   ```yaml
   tunnel: voice-bot
   ingress:
     - hostname: your-subdomain.trycloudflare.com
       service: http://localhost:5000
     - service: http_status:404
   ```

7. **Set BASE_URL in `.env`:**
   ```env
   BASE_URL=https://your-subdomain.trycloudflare.com
   ```
   This URL will **never change** as long as you use the same tunnel.

**Benefits:**
- ✅ Stable URL that doesn't change
- ✅ Free forever
- ✅ Works with WebSockets
- ✅ No browser warning page

---

## Alternative: LocalTunnel (free, stable subdomain possible)

**LocalTunnel** is a free npm-based tunnel that sometimes allows custom subdomains.

### Setup:

1. **Install Node.js** (if not already installed): https://nodejs.org/

2. **Install localtunnel globally:**
   ```bash
   npm install -g localtunnel
   ```

3. **Run tunnel with custom subdomain (if available):**
   ```bash
   lt --port 5000 --subdomain your-subdomain
   ```
   If the subdomain is taken, it will assign a random one. You can try different subdomains.

4. **Set BASE_URL** to the provided URL (e.g., `https://your-subdomain.loca.lt`)

**Note:** Custom subdomains may not always be available. If unavailable, you'll get a random URL that changes each time.

---

## Quick option: localhost.run (URLs change)

**localhost.run** works great with WebSockets but URLs change each time you reconnect.

### Setup:

1. **Run the tunnel:**
   ```bash
   ssh -R 80:localhost:5000 nokey@localhost.run
   ```

2. **Copy the URL** and update `BASE_URL` in `.env` each time.

**Note:** URLs change when you reconnect, so you'll need to update `.env` and restart your app each time.

---

## Other options

### serveo.net (SSH tunnel, URLs change)
```bash
ssh -R 80:localhost:5000 serveo.net
```
Works with WebSockets but URLs change each time.

### bore.pub (Simple tunnel, URLs change)
```bash
bore local 5000 --to bore.pub
```
Very simple but URLs change each time.

### zrok (Open source, can self-host for stable URLs)
If you have a server, you can self-host zrok for stable URLs. See: https://github.com/openziti/zrok

---

## Paid options (stable URLs guaranteed)

- **ngrok paid:** Skip browser warning + stable custom domains
- **Cloudflare Tunnel paid:** More features, custom domains
- **PageKite:** Paid tunnel service with stable URLs

---

## Recommendation

**For stable URLs:** Use **Cloudflare Tunnel with free account** (Option 1 above). It's free, gives you a stable URL, and works perfectly with WebSockets.

**For quick testing:** Use **localhost.run** if you don't mind updating the URL occasionally.

---

## Check Twilio

In **Twilio Console → Monitor → Logs → Calls** (or **Debugger**), open a failed call. Look for errors like:
- "Stream connection failed" 
- "Connection reset without closing handshake" (often Cloudflare Tunnel quick tunnel issue)
- Non-2xx response when connecting to your `wss://.../media` URL
