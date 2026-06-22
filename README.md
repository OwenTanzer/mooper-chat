# Mooper Chat

A minimal private chat room — password-protected, real-time, single-file. Built with FastAPI and WebSockets, deployed on Railway.

## Usage

Open the app URL in a browser. Enter your name and the room password, then click **Join**.

Messages appear as chat bubbles. Send with the **Send** button or press **Enter**. Anyone who joins after you will see the last 50 messages replayed automatically.

## Running locally

```bash
pip install -r requirements.txt
ROOM_PASSWORD=yourpassword uvicorn main:app --reload
```

Then open `http://localhost:8000`.

## Deployment (Railway)

The `railway.toml` configures the start command automatically:

```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Set the `ROOM_PASSWORD` environment variable in the Railway dashboard. If unset, it defaults to `changeme`.

## How it works

- FastAPI serves the entire frontend as an HTML string from `GET /`
- On join, the browser opens a WebSocket connection to `/ws?name=...&password=...`
- The server verifies the password and either sends `auth_ok` or closes the socket
- After auth, messages are broadcast to all connected clients in real time
- The server keeps a rolling buffer of the last 50 messages (`collections.deque`) and replays them to new joiners
