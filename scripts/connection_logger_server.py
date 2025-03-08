import sqlite3
import time
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager
import gradio as gr

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    init_db()
    yield
    # Shutdown code (if any)

app = FastAPI(lifespan=lifespan)

# Use a relative path for local development, or absolute path in production
DB_PATH = os.environ.get("GRADIO_DB_PATH", "gradio_connections.db")

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

def read_db_and_plot_connections():
    """
    Read connection data from the database and return DataFrames 
    with minute-by-minute connection counts for the last 15 minutes
    and hourly connection counts for the last 24 hours.
    Includes both total connections and unique connections.
    """
    import pandas as pd
    from datetime import datetime
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    current_time = int(time.time())
    fifteen_minutes_ago = current_time - (15 * 60)
    twenty_four_hours_ago = current_time - (24 * 60 * 60)
    
    # Get data for the last 15 minutes
    cursor.execute('SELECT timestamp, event_type, remote_addr FROM connections WHERE timestamp >= ?', 
                  (fifteen_minutes_ago,))
    recent_connections = cursor.fetchall()
    
    # Get data for the last 24 hours
    cursor.execute('SELECT timestamp, event_type, remote_addr FROM connections WHERE timestamp >= ?', 
                  (twenty_four_hours_ago,))
    daily_connections = cursor.fetchall()
    conn.close()

    if not recent_connections:
        connections_per_minute = pd.DataFrame(columns=['minute', 'connections', 'metric_type'])
        average_minute = 0
    else:
        df_minutes = pd.DataFrame(recent_connections, columns=['timestamp', 'event_type', 'remote_addr'])
        df_minutes['datetime'] = df_minutes['timestamp'].apply(lambda x: datetime.fromtimestamp(x))
        df_minutes['minute'] = df_minutes['datetime'].apply(lambda x: x.strftime('%H:%M'))
        
        # Total connections per minute
        total_per_minute = df_minutes.groupby('minute').size().reset_index(name='connections')
        total_per_minute['metric_type'] = 'Total'
        
        # Unique connections per minute
        unique_per_minute = df_minutes.groupby('minute')['remote_addr'].nunique().reset_index(name='connections')
        unique_per_minute['metric_type'] = 'Unique'
        
        # Combine the dataframes
        connections_per_minute = pd.concat([total_per_minute, unique_per_minute], ignore_index=True)
        average_minute = total_per_minute['connections'].mean()

    if not daily_connections:
        connections_per_hour = pd.DataFrame(columns=['hour', 'connections', 'metric_type'])
        average_hour = 0
    else:
        df_hours = pd.DataFrame(daily_connections, columns=['timestamp', 'event_type', 'remote_addr'])
        df_hours['datetime'] = df_hours['timestamp'].apply(lambda x: datetime.fromtimestamp(x))
        df_hours['hour'] = df_hours['datetime'].apply(lambda x: x.strftime('%H:00'))
        
        # Total connections per hour
        total_per_hour = df_hours.groupby('hour').size().reset_index(name='connections')
        total_per_hour['metric_type'] = 'Total'
        
        # Unique connections per hour
        unique_per_hour = df_hours.groupby('hour')['remote_addr'].nunique().reset_index(name='connections')
        unique_per_hour['metric_type'] = 'Unique'
        
        # Combine the dataframes
        connections_per_hour = pd.concat([total_per_hour, unique_per_hour], ignore_index=True)
        average_hour = total_per_hour['connections'].mean()
    
    return average_minute, connections_per_minute, average_hour, connections_per_hour

def get_ip_address_list() -> list[list[str]]:
    """
    Read the connection data from the database and return a list of the last 
    100 IP addresses and ports that have connected to the server.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT remote_addr FROM connections ORDER BY timestamp DESC LIMIT 100')
    ip_addresses = cursor.fetchall()
    conn.close()
    return [ip[0].split(":") for ip in ip_addresses]

with gr.Blocks() as demo:
    with gr.Row():
        minute_bar_plot = gr.BarPlot(x="minute", y="connections", color="metric_type", 
                                     title="Connections per minute (last 15 minutes)")
        average_minute = gr.Label(label="Average connections per minute")
    with gr.Row():
        hour_bar_plot = gr.BarPlot(x="hour", y="connections", color="metric_type", 
                                   title="Connections per hour (last 24 hours)")
        average_hour = gr.Label(label="Average connections per hour")
    demo.load(
        read_db_and_plot_connections, 
        None, 
        [average_minute, minute_bar_plot, average_hour, hour_bar_plot]
    )

    timer = gr.Timer()
    timer.tick(read_db_and_plot_connections, None, [average_minute, minute_bar_plot, average_hour, hour_bar_plot])

with demo.route("IP Addresses") as ip_route:
    with gr.Row():
        ip_plot = gr.Dataframe(headers=["IP Address", "Port"], value=get_ip_address_list)
    timer = gr.Timer()
    timer.tick(get_ip_address_list, None, ip_plot)

complete_app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run("connection_logger_server:complete_app", host="127.0.0.1", port=8765) 