from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json

app = FastAPI()

active_hosts = {}
relay_pairs = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    my_role = None
    my_id = None
    
    try:
        init_msg = await websocket.receive_text()
        data = json.loads(init_msg)
        action = data.get("action")
        
        if action == "register_host":
            my_role = "host"
            my_id = data.get("host_id")
            # Ise-save na agad ang password sa server
            my_password = data.get("password", "admin123")
            active_hosts[my_id] = {"ws": websocket, "password": my_password}
            
            await websocket.send_text(json.dumps({"status": "REGISTERED"}))
            
            while True:
                msg = await websocket.receive()
                if websocket in relay_pairs:
                    client_ws = relay_pairs[websocket]
                    if "bytes" in msg:
                        await client_ws.send_bytes(msg["bytes"])
                    elif "text" in msg:
                        await client_ws.send_text(msg["text"])
                        
        elif action == "connect_client":
            my_role = "client"
            target_id = data.get("target_id")
            client_password = data.get("password")
            
            if target_id not in active_hosts:
                await websocket.send_text(json.dumps({"status": "NOT_FOUND"}))
                await websocket.close()
                return
                
            host_data = active_hosts[target_id]
            
            # Server na mismo ang magche-check ng password para walang crash!
            if client_password != host_data["password"]:
                await websocket.send_text(json.dumps({"status": "AUTH_FAIL"}))
                await websocket.close()
                return
                
            host_ws = host_data["ws"]
            await websocket.send_text(json.dumps({"status": "AUTH_OK"}))
            
            # I-link sila at sabihan ang host na simulan ang video
            relay_pairs[websocket] = host_ws
            relay_pairs[host_ws] = websocket
            await host_ws.send_text(json.dumps({"action": "start_stream"}))
            
            while True:
                msg = await websocket.receive()
                if host_ws in relay_pairs:
                    if "bytes" in msg:
                        await host_ws.send_bytes(msg["bytes"])
                    elif "text" in msg:
                        await host_ws.send_text(msg["text"])
                        
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if my_role == "host" and my_id in active_hosts:
            del active_hosts[my_id]
        if websocket in relay_pairs:
            partner = relay_pairs[websocket]
            if partner in relay_pairs:
                del relay_pairs[partner]
            del relay_pairs[websocket]
