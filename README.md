# Dexcom Reader

A Dexcom glucose monitoring and alerting system with multiple time-scale views, trendline analysis, and optional Home Assistant/Nabu Casa integration.  
This tool retrieves glucose readings from Dexcom, displays real-time BG values in a Tkinter GUI, and can send alerts to Home Assistant.

**Disclaimer:** This software is for informational and demonstration purposes only. It is not a medical device. Always consult a medical professional for any health or treatment decisions.

* * *

## Features

- **Multiple Time-Scale Plots:** 1-hour, 3-hour, 6-hour, 12-hour, 24-hour, or the full history (“Max”).
- **Trendline Calculation:** Uses a simple linear regression on recent data to estimate future BG values.
- **Tkinter GUI:** A graphical display showing current BG, trend arrows, and historical charts.
- **Home Assistant Webhook Alerts:** Optionally send notifications to a Home Assistant instance via Nabu Casa when BG is out of range.

* * *

## Requirements

- **Python 3.7+**
- **Dexcom Account:** Valid username & password to access Dexcom data via `pydexcom`.
- *(Optional)* **Home Assistant + Nabu Casa:** If you want to trigger alerts in your Home Assistant setup.

For Python dependencies, see `pyproject.toml` or `requirements.txt` (if provided). Typical libraries used are:

- `matplotlib`
- `numpy`
- `pandas`
- `pydexcom`
- `pytz`
- `python-dotenv`
- `requests`

* * *

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/jadericdawson/dexcom_reader.git
cd dexcom_reader
```

### 2. Create a Virtual Environment (Recommended)

```bash
python -m venv .venv
source .venv/bin/activate  # On Linux/macOS
# or .\.venv\Scripts\activate on Windows PowerShell
```

### 3. Install Dependencies

If you are using the `pyproject.toml` build system:

```bash
pip install .
```

* * *

## Environment Variables with `.env`

This project uses `python-dotenv` to load Dexcom credentials from a local `.env` file.

1.  Update the `.env` file in the root of your project (same folder as `dexcom_reader.py`):
    
    ```env
    DEXCOM_USER="ENTER_YOUR_DEXCOM_USERNAME"
    DEXCOM_PASS="ENTER_YOUR_DEXCOM_PASSWORD"
    ```
    
2.  Ignore `.env` in version control:  
    Add the following line to your `.gitignore`:
    
    ```bash
    .env
    ```
    
3.  The script automatically loads `.env`:
    
    ```python
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    DEXCOM_USER = os.getenv("DEXCOM_USER")
    DEXCOM_PASS = os.getenv("DEXCOM_PASS")
    # ...
    dexcom = Dexcom(username=DEXCOM_USER, password=DEXCOM_PASS)
    ```
    

* * *

## Home Assistant & Nabu Casa Setup

### 1. Sign Up for Nabu Casa

Subscribe to Nabu Casa to access remote webhook capabilities. After subscribing, you’ll get a globally accessible URL for your Home Assistant instance (e.g., `https://<random>.ui.nabu.casa/`).

#### Yes! If you want a notification on your google home speakers, it will cost money. About $6.50/month in 2024.

### 2. Create a Webhook in Home Assistant

** If you do not already have a home assistant setup, start here: https://www.home-assistant.io/installation/

1.  In Home Assistant, navigate to **Settings > Automations & Scenes > Automations** (or set up a Webhook automation directly). (Name it 'glucose_alert')
2.  Use 'When a Webhook payload has been received' --> Then do 'Play Glucose Alert on YOUR_DEVICE'
3.  Once created, your final webhook URL will look like:
    
    ```perl
    https://<your-nabu-casa-url>/api/webhook/glucose_alert
    ```
    
    Where your-nabu-casa-url can be found on https://www.nabucasa.com/ under the 'Remote UI' section as 'Remote Address'

### 3. Update the Code with Your Webhook URL

Replace the default `webhook_url` in the code:

```python
webhook_url = "https://<your-nabu-casa-url>/api/webhook/glucose_alert"
```

Whenever the script detects an out-of-range BG, it will send a POST request with data (BG value, trend, timestamp, etc.) to this endpoint.

* * *

## Usage

1.  Activate your virtual environment (if using one):
    
    ```bash
    source .venv/bin/activate
    ```
    
2.  Run the script:
    
    ```bash
    python main.py
    ```
    
    *(Adjust for the actual filename if it’s something else.)*

A Tkinter window should appear, showing:

- A checkbox to toggle trend arrows
- Current BG and trend description
- Expected BG in 20 minutes (based on regression)
- Multiple time-window tabs for historical BG graphs

If you configured the Nabu Casa webhook URL, you’ll receive alerts on Home Assistant whenever BG is out of the desired range.

* * *

## Troubleshooting

- **No Dexcom readings?** Check your Dexcom credentials (`DEXCOM_USER`, `DEXCOM_PASS`).
- **Home Assistant alerts not firing?** Verify your Nabu Casa webhook URL and Home Assistant configuration.
- **Install errors?** Ensure your Python, pip, and setuptools are up to date.
- **Permissions errors on `.env`?** Confirm its location and the script’s working directory.

* * *

## Project Structure

```bash
DEXCOM_READER/
├── .venv/                     # Virtual environment folder (optional, not version-controlled)
├── build/                     # Temporary build artifacts (auto-generated by pip)
├── delete/                    # Custom folder (possibly for temporary files or testing)
├── dexcom_reader.egg-info/    # Metadata folder generated by pip
├── .env                       # Environment file for storing sensitive credentials (not version-controlled)
├── dexcom_reader.py           # Main script for running the Dexcom Reader application
├── glucose_monitor.log        # Log file for application activity
├── glucose_readings.csv       # CSV file for storing glucose readings
├── pyproject.toml             # Modern build configuration for Python packaging
├── README.md                  # Project documentation (this file)
└── requirements.txt           # List of Python dependencies
```

* * *

## Contributing

Pull requests are welcome!  
For major changes, please open an issue first to discuss your ideas.  
Consider adding or updating documentation and tests if you introduce new features.

* * *

## License

This project is licensed under the MIT License. See LICENSE for details.

Enjoy monitoring your Dexcom data with a neat GUI and optional Home Assistant integration!