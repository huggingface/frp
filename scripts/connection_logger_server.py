import sqlite3
import time
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Connection Logger")

DB_PATH = "/home/ubuntu/frp/gradio_connections.db"

class ConnectionEvent(BaseModel):
    event_type: str
    remote_addr: str

def init_db():
    """Initialize the SQLite database with a simple schema."""
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else '.', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS connections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp INTEGER,
        event_type TEXT,
        remote_addr TEXT
    )
    ''')
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

@app.post("/log_connection")
async def log_connection(event: ConnectionEvent):
    """Log a connection event to the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO connections 
        (timestamp, event_type, remote_addr)
        VALUES (?, ?, ?)
        ''', (
            int(time.time()),
            event.event_type,
            event.remote_addr
        ))
        
        conn.commit()
        conn.close()
        print(f"Logged {event.event_type} from {event.remote_addr}")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log connection: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="127.0.0.1", port=8000) 