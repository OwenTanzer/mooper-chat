import os
import json
import asyncio
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse

ROOM_PASSWORD = os.environ.get("ROOM_PASSWORD", "changeme")
MAX_HISTORY = 50

app = FastAPI()
history: deque = deque(maxlen=MAX_HISTORY)
connections: list[WebSocket] = []

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chat</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #f0f0f0; height: 100dvh; display: flex; flex-direction: column; align-items: center; justify-content: center; }
  #login { background: #fff; padding: 2rem; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,.1); display: flex; flex-direction: column; gap: 1rem; width: 300px; }
  #login h2 { font-size: 1.2rem; color: #333; }
  #login input { padding: .6rem .8rem; border: 1px solid #ccc; border-radius: 6px; font-size: 1rem; }
  #login button { padding: .6rem; background: #1a1a2e; color: #fff; border: none; border-radius: 6px; font-size: 1rem; cursor: pointer; }
  #login button:hover { background: #16213e; }
  #login .err { color: #c00; font-size: .85rem; display: none; }
  #chat { display: none; flex-direction: column; width: min(700px, 98vw); height: 96dvh; background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,.1); overflow: hidden; }
  #status-bar { padding: .5rem 1rem; background: #1a1a2e; color: #aaa; font-size: .8rem; display: flex; justify-content: space-between; }
  #status-bar span.online { color: #4caf50; }
  #messages { flex: 1; overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: .5rem; }
  .msg { max-width: 75%; padding: .5rem .8rem; border-radius: 10px; font-size: .95rem; line-height: 1.4; word-break: break-word; }
  .msg.me { align-self: flex-end; background: #1a1a2e; color: #fff; border-bottom-right-radius: 2px; }
  .msg.them { align-self: flex-start; background: #e8e8e8; color: #222; border-bottom-left-radius: 2px; }
  .msg .meta { font-size: .72rem; opacity: .6; margin-bottom: .15rem; }
  .msg.system { align-self: center; background: none; color: #999; font-size: .8rem; font-style: italic; }
  #input-row { display: flex; gap: .5rem; padding: .75rem; border-top: 1px solid #eee; }
  #input-row input { flex: 1; padding: .6rem .8rem; border: 1px solid #ccc; border-radius: 20px; font-size: .95rem; outline: none; }
  #input-row input:focus { border-color: #1a1a2e; }
  #input-row button { padding: .6rem 1.2rem; background: #1a1a2e; color: #fff; border: none; border-radius: 20px; cursor: pointer; font-size: .95rem; }
  #input-row button:hover { background: #16213e; }
</style>
</head>
<body>

<div id="login">
  <h2>Enter room password</h2>
  <input id="name-input" type="text" placeholder="Your name" autocomplete="off" />
  <input id="pw-input" type="password" placeholder="Password" autocomplete="off" />
  <button onclick="join()">Join</button>
  <div class="err" id="err-msg">Wrong password.</div>
</div>

<div id="chat">
  <div id="status-bar">
    <span id="room-label">Chat</span>
    <span id="conn-status">connecting…</span>
  </div>
  <div id="messages"></div>
  <div id="input-row">
    <input id="msg-input" type="text" placeholder="Message…" autocomplete="off" onkeydown="if(event.key==='Enter')send()" />
    <button onclick="send()">Send</button>
  </div>
</div>

<script>
let ws, myName;

function join() {
  const name = document.getElementById('name-input').value.trim();
  const pw   = document.getElementById('pw-input').value;
  if (!name) { document.getElementById('name-input').focus(); return; }

  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws?name=${encodeURIComponent(name)}&password=${encodeURIComponent(pw)}`);

  ws.onopen = () => {};

  ws.onmessage = (e) => {
    const d = JSON.parse(e.data);
    if (d.type === 'auth_ok') {
      myName = name;
      document.getElementById('login').style.display = 'none';
      document.getElementById('chat').style.display = 'flex';
      document.getElementById('msg-input').focus();
      document.getElementById('conn-status').textContent = 'connected';
      document.getElementById('conn-status').className = 'online';
    } else if (d.type === 'auth_fail') {
      document.getElementById('err-msg').style.display = 'block';
      ws.close();
    } else if (d.type === 'message') {
      addMessage(d);
    } else if (d.type === 'system') {
      addSystem(d.text);
    }
  };

  ws.onclose = () => {
    document.getElementById('conn-status').textContent = 'disconnected';
    document.getElementById('conn-status').className = '';
  };
}

function addMessage(d) {
  const box = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'msg ' + (d.name === myName ? 'me' : 'them');
  const meta = document.createElement('div');
  meta.className = 'meta';
  meta.textContent = (d.name === myName ? 'You' : d.name) + ' · ' + d.time;
  div.appendChild(meta);
  div.appendChild(document.createTextNode(d.text));
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function addSystem(text) {
  const box = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'msg system';
  div.textContent = text;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function send() {
  const inp = document.getElementById('msg-input');
  const text = inp.value.trim();
  if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ text }));
  inp.value = '';
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && document.getElementById('login').style.display !== 'none') join();
});
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@app.websocket("/ws")
async def chat(ws: WebSocket, name: str = "", password: str = ""):
    await ws.accept()

    if password != ROOM_PASSWORD:
        await ws.send_text(json.dumps({"type": "auth_fail"}))
        await ws.close()
        return

    if not name:
        name = "Anonymous"

    await ws.send_text(json.dumps({"type": "auth_ok"}))

    # replay history
    for msg in history:
        await ws.send_text(json.dumps({"type": "message", **msg}))

    connections.append(ws)
    await broadcast({"type": "system", "text": f"{name} joined"}, exclude=ws)

    try:
        while True:
            data = await ws.receive_text()
            payload = json.loads(data)
            text = payload.get("text", "").strip()
            if not text:
                continue
            msg = {
                "name": name,
                "text": text,
                "time": datetime.now(timezone.utc).strftime("%H:%M"),
            }
            history.append(msg)
            await broadcast({"type": "message", **msg})
    except WebSocketDisconnect:
        connections.remove(ws)
        await broadcast({"type": "system", "text": f"{name} left"})


async def broadcast(payload: dict, exclude: WebSocket | None = None):
    text = json.dumps(payload)
    dead = []
    for conn in connections:
        if conn is exclude:
            continue
        try:
            await conn.send_text(text)
        except Exception:
            dead.append(conn)
    for conn in dead:
        connections.remove(conn)
