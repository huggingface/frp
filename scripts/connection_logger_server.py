import sqlite3
import time
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager
import gradio as gr
from typing import Optional
from datetime import datetime
import pandas as pd
import numpy as np

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
    remote_addr: Optional[str] = None
    run_id: Optional[str] = None
    visitor_ip: Optional[str] = None

def init_db():
    """Initialize the SQLite database with a schema that supports the new fields."""
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else '.', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if we need to update the schema
    cursor.execute("PRAGMA table_info(connections)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'connections' not in columns:
        # Create the table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER,
            event_type TEXT,
            remote_addr TEXT,
            run_id TEXT,
            visitor_ip TEXT
        )
        ''')
    else:
        # Add new columns if they don't exist
        if 'run_id' not in columns:
            cursor.execute('ALTER TABLE connections ADD COLUMN run_id TEXT')
        if 'visitor_ip' not in columns:
            cursor.execute('ALTER TABLE connections ADD COLUMN visitor_ip TEXT')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

@app.post("/log_connection")
async def log_connection(event: ConnectionEvent):
    """Log a connection event to the database with the new fields."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO connections 
        (timestamp, event_type, remote_addr, run_id, visitor_ip)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            int(time.time()),
            event.event_type,
            event.remote_addr,
            event.run_id,
            event.visitor_ip
        ))
        
        conn.commit()
        conn.close()
        
        log_message = f"Logged {event.event_type}"
        if event.run_id:
            log_message += f" - RunID: {event.run_id}"
        if event.remote_addr:
            log_message += f" - Remote: {event.remote_addr}"
        if event.visitor_ip:
            log_message += f" - Visitor IP: {event.visitor_ip}"
        
        print(log_message)
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
    Only counts "connect" events.
    """    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    current_time = int(time.time())
    fifteen_minutes_ago = current_time - (15 * 60)
    twenty_four_hours_ago = current_time - (24 * 60 * 60)
    
    # Get data for the last 15 minutes - only "connect" events
    cursor.execute('SELECT timestamp, event_type, remote_addr FROM connections WHERE timestamp >= ? AND event_type = "connect"', 
                  (fifteen_minutes_ago,))
    recent_connections = cursor.fetchall()
    
    # Get data for the last 24 hours - only "connect" events
    cursor.execute('SELECT timestamp, event_type, remote_addr FROM connections WHERE timestamp >= ? AND event_type = "connect"', 
                  (twenty_four_hours_ago,))
    daily_connections = cursor.fetchall()
    
    # Get connection durations for the last week
    one_week_ago = current_time - (7 * 24 * 60 * 60)
    cursor.execute('''
        SELECT run_id, event_type, timestamp 
        FROM connections 
        WHERE timestamp >= ? AND run_id IS NOT NULL AND run_id != ""
        AND event_type IN ("connect", "disconnect")
        ORDER BY timestamp
    ''', (one_week_ago,))
    duration_data = cursor.fetchall()
    
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
        df_hours['hour'] = df_hours['datetime'].apply(lambda x: x.strftime('%H'))
        
        # Total connections per hour
        total_per_hour = df_hours.groupby('hour').size().reset_index(name='connections')
        total_per_hour['metric_type'] = 'Total'
        
        # Unique connections per hour
        unique_per_hour = df_hours.groupby('hour')['remote_addr'].nunique().reset_index(name='connections')
        unique_per_hour['metric_type'] = 'Unique'
        
        # Combine the dataframes
        connections_per_hour = pd.concat([total_per_hour, unique_per_hour], ignore_index=True)
        average_hour = total_per_hour['connections'].mean()

    # Calculate connection durations
    duration_df = pd.DataFrame(columns=['duration', 'connections'])
    
    if duration_data:
        df_durations = pd.DataFrame(duration_data, columns=['run_id', 'event_type', 'timestamp'])
        
        # Group by run_id and get first connect and last disconnect
        connect_events = df_durations[df_durations['event_type'] == 'connect'].groupby('run_id')['timestamp'].min()
        disconnect_events = df_durations[df_durations['event_type'] == 'disconnect'].groupby('run_id')['timestamp'].max()
        
        # Find run_ids that have both connect and disconnect events
        valid_run_ids = set(connect_events.index) & set(disconnect_events.index)
        
        if valid_run_ids:
            # Calculate durations for valid run_ids
            durations = []
            for run_id in valid_run_ids:
                connect_time = connect_events[run_id]
                disconnect_time = disconnect_events[run_id]
                if disconnect_time > connect_time:  # Ensure valid duration
                    durations.append(disconnect_time - connect_time)
            
            if durations:
                # Define predefined bins in seconds
                bin_edges = [
                    0,                # 0 seconds
                    60,               # 1 minute
                    5 * 60,           # 5 minutes
                    10 * 60,          # 10 minutes
                    30 * 60,          # 30 minutes
                    60 * 60,          # 1 hour
                    2 * 60 * 60,      # 2 hours
                    5 * 60 * 60,      # 5 hours
                    10 * 60 * 60,     # 10 hours
                    24 * 60 * 60,     # 24 hours
                    48 * 60 * 60,     # 48 hours
                    72 * 60 * 60,     # 72 hours
                    168 * 60 * 60,    # 168 hours (1 week)
                    float('inf')      # More than a week
                ]
                
                # Define bin labels with their order
                bin_info = [
                    (0, "<1m"),
                    (1, "1-5m"),
                    (2, "5-10m"),
                    (3, "10-30m"),
                    (4, "30-60m"),
                    (5, "1-2hr"),
                    (6, "2-5hr"),
                    (7, "5-10hr"),
                    (8, "10-24hr"),
                    (9, "24-48hr"),
                    (10, "48-72hr"),
                    (11, "72-168hr"),
                    (12, ">168hr")
                ]
                
                bin_labels = [label for _, label in bin_info]
                
                # Bin the data
                binned_data = np.zeros(len(bin_labels), dtype=int)
                for duration in durations:
                    for i in range(len(bin_edges) - 1):
                        if bin_edges[i] <= duration < bin_edges[i + 1]:
                            binned_data[i] += 1
                            break
                
                # Create DataFrame for the bar plot with order column
                duration_df = pd.DataFrame({
                    'order': [order for order, _ in bin_info],
                    'duration': bin_labels,
                    'connections': binned_data
                })
                
                # Sort by the order column
                duration_df = duration_df.sort_values('order').drop('order', axis=1)

    return average_minute, connections_per_minute, average_hour, connections_per_hour, duration_df

def get_ip_address_list() -> list[list[str]]:
    """
    Read the connection data from the database and return a list of the last 
    100 connections with their details.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT event_type, remote_addr, run_id, visitor_ip, timestamp 
        FROM connections 
        ORDER BY timestamp DESC 
        LIMIT 100
    ''')
    connections = cursor.fetchall()
    conn.close()
    
    # Format the data for display
    result = []
    for conn in connections:
        event_type, remote_addr, run_id, visitor_ip, timestamp = conn
        time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        if event_type == "connect" and remote_addr:
            ip, port = remote_addr.split(":") if ":" in remote_addr else (remote_addr, "")
            result.append([event_type, ip, port, run_id, time_str])
        elif event_type == "disconnect" and run_id:
            result.append([event_type, "", "", run_id, time_str])
        elif event_type == "visit" and visitor_ip:
            ip, port = visitor_ip.split(":") if ":" in visitor_ip else (visitor_ip, "")
            result.append([event_type, ip, port, "", time_str])
        else:
            # Handle legacy data
            if remote_addr:
                ip, port = remote_addr.split(":") if ":" in remote_addr else (remote_addr, "")
                result.append([event_type, ip, port, run_id or "", time_str])
    
    return result

with gr.Blocks() as demo:
    with gr.Row():
        minute_bar_plot = gr.BarPlot(x="minute", y="connections", color="metric_type", 
                                     title="Connections per minute (last 15 minutes)")
        average_minute = gr.Label(label="Average connections per minute")
    with gr.Row():
        hour_bar_plot = gr.BarPlot(x="hour", y="connections", color="metric_type", 
                                   title="Connections per hour (last 24 hours)")
        average_hour = gr.Label(label="Average connections per hour")
    
    duration_plot = gr.BarPlot(
        x="duration", 
        y="connections", 
        title="Connection Durations (last week)",
        tooltip=["duration", "connections"],
    )

    demo.load(
        read_db_and_plot_connections, 
        None, 
        [average_minute, minute_bar_plot, average_hour, hour_bar_plot, duration_plot]
    )

    timer = gr.Timer()
    timer.tick(read_db_and_plot_connections, None, [average_minute, minute_bar_plot, average_hour, hour_bar_plot, duration_plot])

with demo.route("IP Addresses") as ip_route:
    with gr.Row():
        ip_plot = gr.Dataframe(
            headers=["Event Type", "IP Address", "Port", "RunID", "Timestamp"], 
            value=get_ip_address_list
        )
    timer = gr.Timer()
    timer.tick(get_ip_address_list, None, ip_plot)

complete_app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run("connection_logger_server:complete_app", host="127.0.0.1", port=8765) 