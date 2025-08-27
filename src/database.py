"""
SQLite database store for sharing data between Gunicorn worker processes.

Since Gunicorn workers are separate processes, we can't use in-memory sharing.
SQLite provides a lightweight, file-based database that all processes can access.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Database file path
DATABASE_PATH = "/tmp/fastapi-dual-socket.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# SQLAlchemy models
Base = declarative_base()

class DataItem(Base):
    __tablename__ = "data_items"
    
    key = Column(String(255), primary_key=True)
    value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Metrics(Base):
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True)
    requests = Column(Integer, default=0)
    last_access = Column(DateTime)
    uptime = Column(DateTime, default=datetime.utcnow)

class DatabaseStore:
    """SQLite-based data store for production use"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        # Configure SQLite for better concurrent access
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={
                "check_same_thread": False,
                "timeout": 30
            },
            echo=False  # Disable SQLAlchemy logging
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._ensure_tables()
        self._ensure_metrics_row()
    
    def _ensure_tables(self):
        """Create tables if they don't exist"""
        Base.metadata.create_all(bind=self.engine)
    
    def _ensure_metrics_row(self):
        """Ensure metrics table has at least one row - with better error handling"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self.SessionLocal() as session:
                    # Use a transaction to prevent race conditions
                    session.begin()
                    metrics = session.query(Metrics).with_for_update().first()
                    if not metrics:
                        # Check again in case another process created it
                        metrics = session.query(Metrics).first()
                        if not metrics:
                            metrics = Metrics(requests=0, uptime=datetime.utcnow())
                            session.add(metrics)
                    session.commit()
                    break
            except SQLAlchemyError as e:
                if attempt == max_retries - 1:
                    # Last attempt failed, create a simple metrics entry
                    try:
                        with self.SessionLocal() as session:
                            session.execute("INSERT OR IGNORE INTO metrics (requests, uptime) VALUES (0, ?)", 
                                          (datetime.utcnow().isoformat(),))
                            session.commit()
                    except:
                        pass  # If this fails, we'll handle it in get_metrics
                continue
    
    def get_data(self) -> Dict[str, Any]:
        """Get all data and increment request counter"""
        # First get data without transaction to avoid locks
        data = {}
        try:
            with self.SessionLocal() as session:
                items = session.query(DataItem).all()
                data = {item.key: item.value for item in items}
        except SQLAlchemyError:
            pass
        
        # Then update metrics in separate transaction
        try:
            with self.SessionLocal() as session:
                metrics = session.query(Metrics).first()
                if metrics:
                    metrics.requests += 1
                    metrics.last_access = datetime.utcnow()
                    session.commit()
        except SQLAlchemyError:
            pass  # Don't fail if metrics update fails
        
        return data
    
    def set_data(self, key: str, value: str) -> bool:
        """Set a data item"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self.SessionLocal() as session:
                    # Check if item exists
                    item = session.query(DataItem).filter(DataItem.key == key).first()
                    
                    if item:
                        item.value = value
                        item.updated_at = datetime.utcnow()
                    else:
                        item = DataItem(key=key, value=value)
                        session.add(item)
                    
                    session.commit()
                    return True
                    
            except SQLAlchemyError as e:
                session.rollback()
                if attempt == max_retries - 1:
                    return False
                continue
        return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        with self.SessionLocal() as session:
            try:
                metrics = session.query(Metrics).first()
                if not metrics:
                    return {"requests": 0, "last_access": None, "uptime": datetime.utcnow()}
                
                return {
                    "requests": metrics.requests,
                    "last_access": metrics.last_access,
                    "uptime": metrics.uptime
                }
                
            except SQLAlchemyError:
                return {"requests": 0, "last_access": None, "uptime": datetime.utcnow()}
    
    def reset_data(self) -> bool:
        """Reset all data items (admin only)"""
        with self.SessionLocal() as session:
            try:
                session.query(DataItem).delete()
                session.commit()
                return True
                
            except SQLAlchemyError:
                session.rollback()
                return False
    
    def close(self):
        """Close database connections"""
        self.engine.dispose()

# Global store instance
store = DatabaseStore()

def cleanup_database():
    """Clean up database file on shutdown"""
    try:
        store.close()
        Path(DATABASE_PATH).unlink(missing_ok=True)
    except Exception:
        pass