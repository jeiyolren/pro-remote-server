from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import Dict
import time

app = FastAPI()

SECRET_PASSWORD = "password123"

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, bool] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = False
        print(f"[+] May kumonekta... Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]
        print(f"[-] Nag-disconnect ang client. Total clients: {len(self.active_connections)}")

    async def broadcast_to_others(self, message, sender: WebSocket, is_bytes: bool):
        for connection, is_auth in self.active_connections.items():
            if connection != sender and is_auth:
                try:
                    if is_bytes:
                        await connection.send_bytes(message)
                    else:
                        await connection.send_text(message)
                except Exception as e:
                    print(f"[-] Error sa pag-broadcast: {e}")

manager = ConnectionManager()

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="tl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Premote Cloud Remote Desktop - Pro</title>
    <style>
        body {
            margin: 0;
            background-color: #111;
            color: #fff;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            font-family: Arial, sans-serif;
            outline: none;
            overflow: hidden;
        }
        h2 { margin: 5px 0; font-size: 1.1rem; color: #4CAF50; }
        #controlsBar {
            margin-bottom: 8px; background: #222; padding: 6px 12px;
            border-radius: 5px; border: 1px alt #443; font-size: 0.85rem;
            display: flex; gap: 12px; align-items: center; flex-wrap: wrap; justify-content: center;
        }
        input[type=range], button { cursor: pointer; }
        input[type=text] { padding: 3px 6px; background: #333; color: #fff; border: 1px solid #555; border-radius: 3px; font-size: 0.85rem; }
        button { background: #4CAF50; color: white; border: none; padding: 4px 10px; border-radius: 3px; font-weight: bold; font-size: 0.85rem; }
        button:hover { background: #45a049; }
        #streamContainer {
            border: 2px solid #333; box-shadow: 0 0 20px rgba(0,0,0,0.8);
            max-width: 95%; max-height: 72vh; cursor: default;
            background-color: #222; min-width: 320px; min-height: 200px;
            display: flex; align-items: center; justify-content: center; user-select: none;
        }
        img { display: block; max-width: 100%; height: auto; user-drag: none; }
        #stats { font-size: 0.8rem; color: #888; margin-top: 5px; }
        #status { margin-top: 5px; font-size: 0.85rem; color: #aaa; text-align: center; }
    </style>
</head>
<body tabindex="0">
    <h2>Premote Cloud Remote Desktop</h2>
    <div id="controlsBar">
        <div>
            <label for="qualityRange">Quality: <span id="qualityVal">40</span>%</label>
            <input type="range" id="qualityRange" min="10" max="90" value="40" style="vertical-align: middle;">
        </div>
        <div>
            <input type="text" id="clipboardText" placeholder="Clipboard text..." style="width: 160px;">
            <button id="sendClipboardBtn">Send</button>
        </div>
        <div>
            <button id="fullscreenBtn">Full Screen</button>
        </div>
    </div>
    
    <div id="streamContainer">
        <img id="stream" alt="Naghihintay ng stream..." />
    </div>
    
    <div id="stats">Ping: <span id="pingVal">0</span>ms | FPS: <span id="fpsVal">0</span></div>
    <div id="status">Status: Kumokonekta...</div>

    <script>
        const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
        const wsUrl = wsProtocol + window.location.host + "/ws";
        const statusElement = document.getElementById("status");
        const imgElement = document.getElementById("stream");
        const qualityRange = document.getElementById("qualityRange");
        const qualityVal = document.getElementById("qualityVal");
        const clipboardText = document.getElementById("clipboardText");
        const sendClipboardBtn = document.getElementById("sendClipboardBtn");
        const fullscreenBtn = document.getElementById("fullscreenBtn");
        const pingVal = document.getElementById("pingVal");
        const fpsVal = document.getElementById("fpsVal");

        const password = prompt("I-enter ang Premote Server Password:");
        if (!password) {
            statusElement.innerText = "Error: Kailangan ang password.";
            statusElement.style.color = "#f44336";
            throw new Error("Cancelled");
        }

        let ws = new WebSocket(wsUrl);
        ws.binaryType = "arraybuffer";

        let frameCount = 0;
        let lastTime = performance.now();

        // FPS Counter loop
        setInterval(() => {
            fpsVal.innerText = frameCount;
            frameCount = 0;
        }, 1000);

        // Ping Heartbeat
        setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                window.pingStart = performance.now();
                ws.send("ping");
            }
        }, 2000);

        ws.onopen = () => {
            statusElement.innerText = "Status: Authenticating...";
            ws.send("auth:" + password);
        };

        ws.onmessage = (event) => {
            if (typeof event.data === "string") {
                if (event.data === "auth_success") {
                    statusElement.innerText = "Status: Connected! Live na ang stream.";
                    statusElement.style.color = "#4CAF50";
                } else if (event.data === "auth_failed") {
                    statusElement.innerText = "Status: Maling password!";
                    statusElement.style.color = "#f44336";
                    ws.close();
                } else if (event.data === "pong") {
                    const latency = Math.round(performance.now() - window.pingStart);
                    pingVal.innerText = latency;
                }
            } else if (event.data instanceof ArrayBuffer) {
                frameCount++;
                const blob = new Blob([event.data], { type: "image/jpeg" });
                const imageUrl = URL.createObjectURL(blob);
                imgElement.src = imageUrl;
                imgElement.onload = () => { URL.revokeObjectURL(imageUrl); };
            }
        };

        qualityRange.addEventListener("input", (e) => {
            const q = e.target.value;
            qualityVal.innerText = q;
            if (ws.readyState === WebSocket.OPEN) ws.send(`quality:${q}`);
        });

        sendClipboardBtn.addEventListener("click", () => {
            const text = clipboardText.value;
            if (text && ws.readyState === WebSocket.OPEN) {
                ws.send(`clipboard:${text}`);
                clipboardText.value = "";
                alert("Naipadala na ang text sa clipboard!");
            }
        });

        fullscreenBtn.addEventListener("click", () => {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().catch(err => {
                    alert(`Error sa pag-fullscreen: ${err.message}`);
                });
            } else {
                document.exitFullscreen();
            }
        });

        imgElement.addEventListener("mousemove", (event) => {
            const rect = imgElement.getBoundingClientRect();
            const x = (event.clientX - rect.left) / rect.width;
            const y = (event.clientY - rect.top) / rect.height;
            if (x >= 0 && x <= 1 && y >= 0 && y <= 1) {
                if (ws.readyState === WebSocket.OPEN) ws.send(`move:${x}:${y}`);
            }
        });

        imgElement.addEventListener("mousedown", (event) => {
            if (ws.readyState === WebSocket.OPEN) {
                if (event.button === 0) ws.send("down:left");
                else if (event.button === 2) ws.send("down:right");
            }
        });

        imgElement.addEventListener("mouseup", (event) => {
            if (ws.readyState === WebSocket.OPEN) {
                if (event.button === 0) ws.send("up:left");
                else if (event.button === 2) ws.send("up:right");
            }
        });

        imgElement.addEventListener("contextmenu", (e) => e.preventDefault());

        window.addEventListener("keydown", (e) => {
            if (ws.readyState === WebSocket.OPEN) { ws.send(`keydown:${e.key}`); e.preventDefault(); }
        });
        window.addEventListener("keyup", (e) => {
            if (ws.readyState === WebSocket.OPEN) { ws.send(`keyup:${e.key}`); e.preventDefault(); }
        });
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def read_root():
    return HTML_CONTENT

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive()
            if message.get("text"):
                text_data = message["text"]
                if text_data == "ping":
                    await websocket.send_text("pong")
                    continue
                
                if text_data.startswith("auth:"):
                    pwd = text_data.split(":", 1)[1]
                    if pwd == SECRET_PASSWORD:
                        manager.active_connections[websocket] = True
                        await websocket.send_text("auth_success")
                    else:
                        await websocket.send_text("auth_failed")
                        await websocket.close()
                        break
                    continue
                
                if manager.active_connections.get(websocket, False):
                    await manager.broadcast_to_others(text_data, websocket, is_bytes=False)
                    
            elif message.get("bytes"):
                if manager.active_connections.get(websocket, False):
                    await manager.broadcast_to_others(message["bytes"], websocket, is_bytes=True)
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)
