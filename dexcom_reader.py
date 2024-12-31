import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from pydexcom import Dexcom
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime
import requests
import numpy as np
import pandas as pd
import pytz
from requests.exceptions import RequestException
from dotenv import load_dotenv
import os
import logging
from time import sleep
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("glucose_monitor.log"),
        logging.StreamHandler()
    ]
)

# Trend descriptions based on Dexcom trend codes with Unicode arrows
trend_descriptions = {
    1: 'Going up fast',   # DoubleUp
    2: 'Going up',         # SingleUp
    3: 'Trending up',      # FortyFiveUp
    4: 'Steady',           # Flat
    5: 'Trending down',    # FortyFiveDown
    6: 'Going down',       # SingleDown
    7: 'Going down fast'  # DoubleDown
}

# Unicode arrows for trends
trend_unicode_arrows = {
    1: '↑↑',  # DoubleUp
    2: '↑',   # SingleUp
    3: '↗',   # FortyFiveUp
    4: '→',   # Flat
    5: '↘',   # FortyFiveDown
    6: '↓',   # SingleDown
    7: '↓↓'   # DoubleDown
}

# Function to trigger an alert in Home Assistant using Nabu Casa
def trigger_home_assistant_alert(glucose_value, expected_bg, trend, timestamp):
    print("Triggering Home Assistant alert...")
    webhook_url = "https://home.jadericdawson.com/api/webhook/glucose_alert"
    trend_description = trend_descriptions.get(trend, 'Unknown')
    payload = {
        "Current BG": glucose_value,
        "Expected BG": expected_bg,
        "Trend": trend_description,
        "Timestamp": timestamp.strftime('%H:%M')
    }
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            print("Home Assistant alert triggered successfully.")
        else:
            print(f"Failed to trigger Home Assistant alert: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Error triggering Home Assistant alert: {e}")

# 1) Load .env
load_dotenv()

# 2) Retrieve credentials
DEXCOM_USER = os.getenv("DEXCOM_USER")
DEXCOM_PASS = os.getenv("DEXCOM_PASS")

if not DEXCOM_USER or not DEXCOM_PASS:
    raise ValueError("Dexcom credentials not set. Check your .env file for DEXCOM_USER and DEXCOM_PASS.")

# 3) Initialize Dexcom with credentials from .env
dexcom = Dexcom(username=DEXCOM_USER, password=DEXCOM_PASS)

# Retrieve and load initial historical data
max_minutes = 1440  # 24 hours
glucose_data = dexcom.get_glucose_readings(minutes=max_minutes)

# Reverse the data to have the oldest readings first
glucose_data = glucose_data[::-1]

# Ensure all timestamps are timezone-aware in UTC
timestamps = []
for reading in glucose_data:
    if reading.datetime.tzinfo is None:
        # If naive, assume UTC
        reading_time = pytz.utc.localize(reading.datetime)
    else:
        reading_time = reading.datetime.astimezone(pytz.utc)
    timestamps.append(reading_time)

values = [reading.value for reading in glucose_data]
trends = [reading.trend for reading in glucose_data]
# Data storage

data_file = 'glucose_readings.csv'
def save_data(timestamp, value, trend, insulin=None, carbs=None):
    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S%z')
    data_entry = {'timestamp': timestamp_str, 'value': value, 'trend': trend, 'insulin': insulin, 'carbs': carbs}
    df = pd.DataFrame([data_entry])
    if not os.path.isfile(data_file):
        df.to_csv(data_file, index=False)
    else:
        df.to_csv(data_file, mode='a', header=False, index=False)

for t, v, tr in zip(timestamps, values, trends):
    save_data(t, v, tr)

# Function to calculate the least squares trend line
def calculate_trend_line(timestamps, values, num_points=6):
    if len(values) < num_points:
        return None, None, None, None
    # Use the most recent num_points data
    recent_timestamps = timestamps[-num_points:]
    recent_values = values[-num_points:]
    # Convert timestamps to elapsed minutes since the first timestamp
    x = np.array([(t - recent_timestamps[0]).total_seconds() / 60.0 for t in recent_timestamps])
    y = np.array(recent_values)
    # Perform linear regression to find the slope (m) and intercept (c)
    A = np.vstack([x, np.ones(len(x))]).T
    m, c = np.linalg.lstsq(A, y, rcond=None)[0]
    trend_line = m * x + c
    # The slope m is in mg/dL per minute
    # Expected BG in 20 minutes
    expected_bg = y[-1] + m * 20
    return recent_timestamps, trend_line, m, expected_bg

# Create the main application window
root = tk.Tk()
root.title("Glucose Monitor")

# Main Frame Layout
main_frame = ttk.Frame(root)
main_frame.pack(fill="both", expand=True)

# Variable to control the display of trend arrows
show_trend_arrows_var = tk.BooleanVar(value=True)

# Checkbox to toggle trend arrows
toggle_trend_arrows = ttk.Checkbutton(main_frame, text="Show Trend Arrows", variable=show_trend_arrows_var, command=lambda: create_plots())
toggle_trend_arrows.pack(side=tk.TOP, anchor='w', padx=5)

# Current BG and Trend Display
bg_frame = ttk.Frame(main_frame)
bg_frame.pack(side=tk.TOP, fill=tk.X, pady=5, padx=5)

# Variables to update labels
current_bg_var = tk.StringVar(value=f"Current BG: {values[-1]} mg/dL")
current_trend_code = trends[-1]
current_trend_description = trend_descriptions.get(current_trend_code, "Unknown")
current_trend_var = tk.StringVar(value=f"Trend: {current_trend_description}")
expected_bg_var = tk.StringVar(value=f"Expected BG in 20 mins: Calculating...")

# BG Label
bg_label = tk.Label(bg_frame, textvariable=current_bg_var, font=("Arial", 24), fg="blue")
bg_label.pack(side=tk.LEFT, padx=5)

# Right Frame for Trend and Expected BG
trend_right_frame = ttk.Frame(bg_frame)
trend_right_frame.pack(side=tk.RIGHT, padx=5)

# Trend Label
trend_label = tk.Label(trend_right_frame, textvariable=current_trend_var, font=("Arial", 18), fg="green")
trend_label.pack(anchor='w')

# Expected BG Label
expected_bg_label = tk.Label(trend_right_frame, textvariable=expected_bg_var, font=("Arial", 16), fg="blue")
expected_bg_label.pack(anchor='w')

# Tabbed Notebook for Plots
notebook = ttk.Notebook(main_frame)
notebook.pack(expand=1, fill="both", padx=5, pady=5)

# Define time windows in hours, including the 1-hour window
time_windows = [1, 3, 6, 12, 24, 'Max']

# Create figures and axes for each tab
figures = {}
axes = {}
canvases = {}

for window in time_windows:
    tab = ttk.Frame(notebook)
    tab_text = f"{window}-Hour View" if window != 'Max' else "Max View"
    notebook.add(tab, text=tab_text)
    fig, ax = plt.subplots(figsize=(8, 5))
    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    figures[window] = fig
    axes[window] = ax
    canvases[window] = canvas

# Plot initialization function
def init_plot(ax, title):
    ax.clear()
    ax.set_title(title)
    ax.set_xlabel("Timestamp (EDT)")
    ax.set_ylabel("Glucose Level (mg/dL)")
    ax.set_ylim(0, 400)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.grid(True)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

# Set your local timezone (e.g., 'US/Eastern')
local_tz = pytz.timezone('US/Eastern')

# Ensure all timestamps are converted to the local timezone
timestamps = [
    (t.astimezone(local_tz) if t.tzinfo else pytz.utc.localize(t).astimezone(local_tz))
    for t in timestamps
]

def create_plots():
    _, _, m, expected_bg = calculate_trend_line(timestamps, values, num_points=6)
    expected_bg_var.set(f"Expected BG in 20 mins: {int(expected_bg)} mg/dL")

    for window in time_windows:
        ax = axes[window]
        fig = figures[window]
        canvas = canvases[window]

        # Select data within the time window
        if window == 'Max':
            window_timestamps = timestamps
            window_values = values
            window_trends = trends
        else:
            # Get the current local time with pytz
            now_local = datetime.datetime.now(local_tz)
            time_delta = datetime.timedelta(hours=window+1)
            print("Time delta: ")
            cutoff_time = now_local - time_delta

            # Filter timestamps and corresponding values and trends
            indices = [i for i, t in enumerate(timestamps) if t >= cutoff_time]
            window_timestamps = [timestamps[i] for i in indices]
            window_values = [values[i] for i in indices]
            window_trends = [trends[i] for i in indices]

        # Skip if no data is available for the window
        if not window_timestamps:
            print(f"No data for {window}-hour window.")
            continue

        # Initialize and plot
        init_plot(ax, f"{window}-Hour Glucose Levels" if window != 'Max' else "Max Glucose Levels")
        ax.plot(window_timestamps, window_values, label='Glucose Level', color='blue')

        # Add trend arrows if enabled
        if show_trend_arrows_var.get():
            for i, trend_code in enumerate(window_trends):
                if trend_code in trend_unicode_arrows:
                    arrow = trend_unicode_arrows[trend_code]
                    ax.annotate(
                        arrow,
                        xy=(window_timestamps[i], window_values[i]),
                        xytext=(0, 10),
                        textcoords="offset points",
                        ha='center',
                        va='bottom',
                        fontsize=10,
                        color='blue'
                    )

        # Add trend line if sufficient data is available
        if len(window_timestamps) >= 10:  # Ensure sufficient data points
            x_dates, trend_line, m, _ = calculate_trend_line(window_timestamps, window_values, num_points=6)
            if x_dates is not None:
                x_dates = [t.astimezone(local_tz) for t in x_dates]  # Convert to local timezone
                ax.plot(x_dates, trend_line, color="red", linestyle="--", linewidth=2, label="Trend Line")
                print(f"{window}-Hour Trend Line Slope: {m:.4f} mg/dL per minute")
            else:
                print(f"Not enough data for {window}-hour trend line.")

        # Format x-axis labels
        ax.set_xlim(window_timestamps[0], window_timestamps[-1])  # Set correct limits
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=local_tz))  # Ensure local timezone
        fig.autofmt_xdate()  # Rotate and format date labels
        ax.legend()
        canvas.draw()


# Create the initial plots
create_plots()

# Updated `update_data` function with logging
def update_data():
    try:
        logging.info("Starting data update...")

        # Retry loop to ensure script keeps running
        for attempt in range(5):  # Retry 5 times before pausing
            try:
                glucose_reading = dexcom.get_current_glucose_reading()
                if glucose_reading:
                    logging.info(f"Successfully fetched glucose reading on attempt {attempt + 1}.")
                    break
            except requests.ConnectionError as conn_err:
                logging.warning(f"Connection error on attempt {attempt + 1}: {conn_err}")
                sleep(10)  # Wait 10 seconds before retrying
            except Exception as e:
                logging.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                sleep(10)
                continue
        else:
            logging.error("Failed to fetch glucose reading after multiple attempts.")
            # Retry after a longer delay to avoid quitting
            root.after(60000, update_data)  # Retry in 60 seconds
            return

        # Process the reading
        if not glucose_reading:
            logging.warning("No new glucose reading available.")
            root.after(300000, update_data)  # Retry after 5 minutes
            return

        current_value = glucose_reading.value
        current_trend = glucose_reading.trend
        current_timestamp = glucose_reading.datetime.astimezone(local_tz)

        logging.info(f"Processing new glucose reading: BG={current_value}, Trend={current_trend}, Timestamp={current_timestamp}")

        # Update data and UI
        timestamps.append(current_timestamp)
        values.append(current_value)
        trends.append(current_trend)
        save_data(current_timestamp, current_value, current_trend)
        logging.info("Data saved successfully.")

        current_bg_var.set(f"Current BG: {current_value} mg/dL")
        current_trend_var.set(f"Trend: {trend_descriptions.get(current_trend, 'Unknown')}")

        # Calculate expected BG based on current trend
        _, _, _, expected_bg = calculate_trend_line(timestamps, values, num_points=6)
        logging.info(f"Calculated expected BG in 20 mins: {expected_bg}")

        print("Current BG: ", current_value)
        print("Expected BG: ", expected_bg)

        if current_value < 80 or current_value > 250:
            if expected_bg < 70 or expected_bg > 300:
                alert_message = (
                    f"ALERT! BG out of range: {current_value} mg/dL - "
                    f"Expected BG: {int(expected_bg)} mg/dL - "
                    f"Current Trend: {trend_descriptions.get(current_trend, 'Unknown')} - "
                    f"Current Time: {current_timestamp.strftime('%H:%M')}"
                )
                logging.warning(alert_message)
                print(alert_message)
                #COMMENT OUT HOME ASSISTANT IF NOT NEEDED
                trigger_home_assistant_alert(current_value, int(expected_bg), current_trend, current_timestamp)

        create_plots()
        logging.info("Plots updated successfully.")

        logging.info(f"Updated with new data: {current_value} mg/dL at {current_timestamp}")

    except RequestException as req_err:
        logging.error(f"Network error during update: {req_err}")
    except Exception as e:
        logging.error(f"Unexpected error during update: {e}")
    finally:
        # Schedule the next update attempt
        logging.info("Scheduling the next data update in 5 minutes.")
        root.after(300000, update_data)  # Retry every 5 minutes



# Start the periodic data update
root.after(600, update_data)  # Start after 6 seconds

# Start the Tkinter main loop
root.mainloop()
