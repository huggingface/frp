# connection_logger.py
import sqlite3
import sys
import time
import os

DB_PATH = "gradio_connections.db"

def init_db():
    """Initialize the SQLite database with a simple schema."""
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

def log_connection(event_type, remote_addr):
    """Log a simple connection event."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO connections 
    (timestamp, event_type, remote_addr)
    VALUES (?, ?, ?)
    ''', (
        int(time.time()),
        event_type,
        remote_addr
    ))
    
    conn.commit()
    conn.close()
    print(f"Logged {event_type} from {remote_addr}")

if __name__ == '__main__':
    # Create the database directory if it doesn't exist
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else '.', exist_ok=True)
    
    # Initialize the database
    init_db()
    
    # Simple command line arguments
    if len(sys.argv) < 3:
        print("Usage: python connection_logger.py [connect|disconnect] [remote_addr]")
        sys.exit(1)
        
    event_type = sys.argv[1]
    remote_addr = sys.argv[2]
    
    log_connection(event_type, remote_addr)