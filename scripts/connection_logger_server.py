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
    """
    import pandas as pd
    from datetime import datetime
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    current_time = int(time.time())
    fifteen_minutes_ago = current_time - (15 * 60)
    twenty_four_hours_ago = current_time - (24 * 60 * 60)
    
    # Get data for the last 15 minutes
    cursor.execute('SELECT timestamp, event_type FROM connections WHERE timestamp >= ?', 
                  (fifteen_minutes_ago,))
    recent_connections = cursor.fetchall()
    
    # Get data for the last 24 hours
    cursor.execute('SELECT timestamp, event_type FROM connections WHERE timestamp >= ?', 
                  (twenty_four_hours_ago,))
    daily_connections = cursor.fetchall()
    conn.close()

    if not recent_connections:
        connections_per_minute = pd.DataFrame(columns=['minute', 'connections'])
        average_minute = 0
    else:
        df_minutes = pd.DataFrame(recent_connections, columns=['timestamp', 'event_type'])
        df_minutes['datetime'] = df_minutes['timestamp'].apply(lambda x: datetime.fromtimestamp(x))
        df_minutes['minute'] = df_minutes['datetime'].apply(lambda x: x.strftime('%H:%M'))
        connections_per_minute = df_minutes.groupby('minute').size().reset_index(name='connections')
        average_minute = connections_per_minute['connections'].mean()

    if not daily_connections:
        connections_per_hour = pd.DataFrame(columns=['hour', 'connections'])
        average_hour = 0
    else:
        df_hours = pd.DataFrame(daily_connections, columns=['timestamp', 'event_type'])
        df_hours['datetime'] = df_hours['timestamp'].apply(lambda x: datetime.fromtimestamp(x))
        df_hours['hour'] = df_hours['datetime'].apply(lambda x: x.strftime('%H:00'))
        connections_per_hour = df_hours.groupby('hour').size().reset_index(name='connections')
        average_hour = connections_per_hour['connections'].mean()
    
    return average_minute, connections_per_minute, average_hour, connections_per_hour

def get_map_data():
    """
    Read connection data from the database for the last 24 hours,
    determine the country for each IP address, and create a choropleth map.
    """
    import pandas as pd
    import plotly.express as px
    from collections import Counter
    from ip2geotools.databases.noncommercial import DbIpCity
    
    # Get data for the last 24 hours
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    current_time = int(time.time())
    twenty_four_hours_ago = current_time - (60)
    
    cursor.execute('SELECT remote_addr FROM connections WHERE timestamp >= ?', 
                  (twenty_four_hours_ago,))
    connections = cursor.fetchall()
    conn.close()
    
    if not connections:
        # Return empty figure if no data
        fig = px.choropleth(
            locations=[],
            color=[],
            color_continuous_scale=px.colors.sequential.Blues,
            title="Connection Locations (Last 24 Hours)"
        )
        return fig
    
    # Count connections by country
    country_counts = Counter()
    
    for (ip,) in connections:
        try:
            # Skip private IPs and localhost
            if (ip.startswith(('10.', '172.16.', '192.168.', '127.')) or 
                ip == 'localhost' or ip == '::1'):
                continue
                
            # Get country for IP
            response = DbIpCity.get(ip, api_key='free')
            if response.country:
                country_counts[response.country] += 1
        except Exception as e:
            # Skip IPs that can't be resolved
            print(f"Could not resolve country for IP {ip}: {e}")
            continue
    
    # Create dataframe for choropleth
    df = pd.DataFrame({
        'country_code': list(country_counts.keys()),
        'connections': list(country_counts.values())
    })
    
    # Create choropleth map
    fig = px.choropleth(
        df,
        locations='country_code',
        color='connections',
        hover_name='country_code',
        color_continuous_scale=px.colors.sequential.Blues,
        title="Connection Locations (Last 24 Hours)"
    )
    
    fig.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type='equirectangular'
        )
    )
    
    return fig

with gr.Blocks() as demo:
    with gr.Row():
        minute_bar_plot = gr.BarPlot(x="minute", y="connections")
        average_minute = gr.Label(label="Average connections per minute")
    with gr.Row():
        hour_bar_plot = gr.BarPlot(x="hour", y="connections")
        average_hour = gr.Label(label="Average connections per hour")
    demo.load(
        read_db_and_plot_connections, 
        None, 
        [average_minute, minute_bar_plot, average_hour, hour_bar_plot]
    )

    timer = gr.Timer()
    timer.tick(read_db_and_plot_connections, None, [average_minute, minute_bar_plot, average_hour, hour_bar_plot])

# with demo.route("Map") as map_route:
#     with gr.Row():
#         map_plot = gr.Plot(label="Connection Locations")
    
#     map_route.load(get_map_data, None, map_plot)
    
#     timer = gr.Timer()
#     timer.tick(get_map_data, None, map_plot)

gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run("connection_logger_server:app", host="127.0.0.1", port=8765, reload=True) 