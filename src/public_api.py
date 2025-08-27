from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .database import store

# Public API - exposed to the world
app = FastAPI(title="Public API", description="World-accessible endpoints")

class DataItem(BaseModel):
    key: str
    value: str

@app.get("/")
def read_root():
    """Public health check"""
    return {"status": "ok", "api": "public"}

@app.get("/data")
def get_public_data():
    """Get public data (safe for external access)"""
    data = store.get_data()
    # Filter out sensitive keys
    public_data = {k: v for k, v in data.items() if not k.startswith('_')}
    return {"data": public_data}

@app.post("/data")
def set_public_data(item: DataItem):
    """Set data through public API (with restrictions)"""
    # Prevent setting sensitive keys
    if item.key.startswith('_'):
        raise HTTPException(status_code=403, detail="Cannot set private keys via public API")
    
    success = store.set_data(item.key, item.value)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to store data")
    return {"message": f"Set {item.key} = {item.value}"}

@app.get("/health")
def health_check():
    """Public health endpoint"""
    return {"status": "healthy", "uptime": store.get_metrics()["uptime"]}