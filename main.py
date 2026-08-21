from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json

app = FastAPI()

active_hosts = {}  # host_id -> host_websocket
relay_pairs = {}   # websocket -> partner_websocket

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
            active_hosts[my_id] = websocket
            await websocket.send_text(json.dumps({"status": "REGISTERED"}))
            print(f"[*] Host registered: {my_id}")
            
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
            password = data.get("password")
            
            if target_id not in active_hosts:
                await websocket.send_text(json.dumps({"status": "NOT_FOUND"}))
                await websocket.close()
                return
                
            host_ws = active_hosts[target_id]
            
            # Password check sa pamamagitan ng host
            await host_ws.send_text(json.dumps({"action": "check_password", "password": password}))
            auth_response = await host_ws.receive_text()
            auth_data = json.loads(auth_response)
            
            if auth_data.get("status") != "AUTH_OK":
                await websocket.send_text(json.dumps({"status": "AUTH_FAIL"}))
                await websocket.close()
                return
                
            # Tagumpay ang koneksyon! I-link na sila sa relay pairs
            await websocket.send_text(json.dumps({"status": "AUTH_OK"}))
            relay_pairs[websocket] = host_ws
            relay_pairs[host_ws] = websocket
            print(f"[*] Client relayed to Host: {target_id}")
            
            while True:
                msg = await websocket.receive()
                if host_ws in relay_pairs:
                    if "bytes" in msg:
                        await host_ws.send_bytes(msg["bytes"])
                    elif "text" in msg:
                        await host_ws.send_text(msg["text"])
                        
    except WebSocketDisconnect:
        print(f"[-] Disconnected ({my_role})")
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        if my_role == "host" and my_id in active_hosts:
            del active_hosts[my_id]
        if websocket in relay_pairs:
            partner = relay_pairs[websocket]
            if partner in relay_pairs:
                del relay_pairs[partner]
            del relay_pairs[websocket]
