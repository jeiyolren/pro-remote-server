from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[+] May kumonekta! Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[-] Nag-disconnect ang isang client. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message, is_bytes: bool):
        for connection in self.active_connections:
            try:
                if is_bytes:
                    await connection.send_bytes(message)
                else:
                    await connection.send_text(message)
            except Exception as e:
                print(f"[-] Error sa pag-broadcast: {e}")

manager = ConnectionManager()

@app.get("/")
def read_root():
    return {"status": "Premote Cloud Server ay buhay at gising!"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive()
            if message.get("bytes"):
                await manager.broadcast(message["bytes"], is_bytes=True)
            elif message.get("text"):
                await manager.broadcast(message["text"], is_bytes=False)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)
        print(f"[-] WebSocket Error: {e}")
