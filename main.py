from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict

app = FastAPI()

# Palitan mo na lang ang password na ito ng gusto mo
SECRET_PASSWORD = "password123"

class ConnectionManager:
    def __init__(self):
        # I-track kung ang isang connection ay authenticated na ba (True/False)
        self.active_connections: Dict[WebSocket, bool] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = False  # Hindi pa authenticated sa simula
        print(f"[+] May kumonekta (Naghihintay ng Password)... Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]
        print(f"[-] Nag-disconnect ang isang client. Total clients: {len(self.active_connections)}")

    async def broadcast_to_others(self, message, sender: WebSocket, is_bytes: bool):
        # I-broadcast lamang sa mga authenticated na clients
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

@app.get("/")
def read_root():
    return {"status": "Premote Secure Cloud Server ay buhay at gising!"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive()
            
            if message.get("text"):
                text_data = message["text"]
                
                # Suriin kung ito ay password authentication request
                if text_data.startswith("auth:"):
                    pwd = text_data.split(":", 1)[1]
                    if pwd == SECRET_PASSWORD:
                        manager.active_connections[websocket] = True
                        await websocket.send_text("auth_success")
                        print("[+] Tagumpay! Na-verify ang password ng client.")
                    else:
                        await websocket.send_text("auth_failed")
                        print("[-] Maling password ang ibinigay. Isasara ang koneksyon.")
                        await websocket.close()
                        break
                    continue
                
                # Kung authenticated na, ipasa ang command sa iba
                if manager.active_connections.get(websocket, False):
                    await manager.broadcast_to_others(text_data, websocket, is_bytes=False)
                    
            elif message.get("bytes"):
                # Kung authenticated na, ipasa ang video frame sa iba
                if manager.active_connections.get(websocket, False):
                    await manager.broadcast_to_others(message["bytes"], websocket, is_bytes=True)
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)
        print(f"[-] WebSocket Error: {e}")
