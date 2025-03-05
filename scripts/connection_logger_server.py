import sqlite3
import time
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Use a relative path for local development, or absolute path in production
DB_PATH = os.environ.get("GRADIO_DB_PATH", "gradio_connections.db")

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

@app.route("/log_connection", methods=["POST"])
def log_connection():
    """Log a connection event to the database."""
    try:
        data = request.get_json()
        event_type = data.get("event_type")
        remote_addr = data.get("remote_addr")
        
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
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "detail": f"Failed to log connection: {str(e)}"}), 500

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=8000) 