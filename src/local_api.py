from fastapi import FastAPI
from pydantic import BaseModel
from .shared import store

# Local API - only accessible via Unix socket
app = FastAPI(title="Local Admin API", description="Local-only administrative endpoints")

class AdminDataItem(BaseModel):
    key: str
    value: str

@app.get("/")
def read_root():
    """Local admin health check"""
    return {"status": "ok", "api": "local_admin"}

@app.get("/admin/metrics")
def get_metrics():
    """Get detailed system metrics (admin only)"""
    return store.get_metrics()

@app.get("/admin/data/all")
def get_all_data():
    """Get all data including sensitive keys (admin only)"""
    return {"data": store.get_data()}

@app.post("/admin/data")
def set_admin_data(item: AdminDataItem):
    """Set any data including sensitive keys (admin only)"""
    store.set_data(item.key, item.value)
    return {"message": f"Admin set {item.key} = {item.value}"}

@app.delete("/admin/data/reset")
def reset_all_data():
    """Reset all data (admin only - dangerous!)"""
    store.reset_data()
    return {"message": "All data reset"}

@app.get("/admin/status")
def admin_status():
    """Detailed status for admin"""
    metrics = store.get_metrics()
    data_count = len(store.get_data())
    return {
        "status": "admin_healthy",
        "metrics": metrics,
        "data_items": data_count
    }