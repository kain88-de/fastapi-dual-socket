# Shared business logic between public and local APIs
from datetime import datetime
from typing import Dict, Any

class DataStore:
    """Simple in-memory store shared between apps"""
    
    def __init__(self):
        self._data = {}
        self._metrics = {
            "requests": 0,
            "last_access": None,
            "uptime": datetime.now()
        }
    
    def get_data(self) -> Dict[str, Any]:
        self._metrics["requests"] += 1
        self._metrics["last_access"] = datetime.now()
        return self._data.copy()
    
    def set_data(self, key: str, value: Any) -> None:
        self._data[key] = value
    
    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.copy()
    
    def reset_data(self) -> None:
        """Admin function - only available on local socket"""
        self._data.clear()

# Global instance
store = DataStore()