from fastapi import FastAPI, Request

app = FastAPI()
active_hosts = {}

@app.post("/register")
async def register_host(request: Request):
    data = await request.json()
    host_id = data.get("host_id")
    host_ip = request.client.host
    active_hosts[host_id] = host_ip
    print(f"[*] Host Registered: {host_id} (IP: {host_ip})")
    return {"status": "OK"}

@app.post("/connect")
async def connect_host(request: Request):
    data = await request.json()
    target_id = data.get("target_id")
    
    if target_id in active_hosts:
        host_ip = active_hosts[target_id]
        return {"status": "FOUND", "host_ip": host_ip}
    else:
        return {"status": "NOT_FOUND"}