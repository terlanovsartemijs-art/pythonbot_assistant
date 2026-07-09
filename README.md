# помошничек — Mumble Voice/Text Bot

A Mumble bot that listens for text and voice commands to control Tasmota smart home devices via MQTT, and fetches Nordpool electricity prices.

## Requirements

- Python 3.10+
- Mumble server access
- MQTT broker (tested with Mosquitto )
- Tasmota devices on your local network

## Installation

### 1. Clone the repo
```bash
git clone https://github.com/terlanovsartemijs-art/pythonbot_assistant.git
cd pythonbot_assistant
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux/Mac
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. opus.dll (Windows only)
The `opus.dll` file is included in the repo. No extra steps needed on Windows.

On Linux install it via:
```bash
sudo apt install libopus0
```

### 5. Piper TTS (for parrot/voice commands)
Download the Piper executable for your platform:
- **Windows**: https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip

Extract it into a `piper/` folder inside the project directory.

Download voice models and place them in the `models/` folder:
- Russian: `ru_RU-dmitri-medium.onnx` + `.onnx.json`
- English: `en_US-lessac-medium.onnx` + `.onnx.json`
- Latvian: `lv_LV-aivars-medium.onnx` + `.onnx.json`

Models available at: https://huggingface.co/rhasspy/piper-voices

### 6. Create a `masters` file
Create a plain text file called `masters` in the project root with one authorized Mumble username per line:
```
Artemis
YourUsernameHere
```

Only users listed here can send commands to the bot.

## Configuration

Edit the config section at the top of `MUMBLE.py`:

```python
HOST = "your.mumble.server"       # Mumble server
PORT = ____             # Mumble port
NAME = "Bot"      # Bot display name
PASSWORD = ""            # Server password
CHANNEL = "Root"         # Channel to join

MQTT_HOST = "0.0.0.0"  # MQTT broker IP
MQTT_PORT = 1883       # MQTT broker port
```

Add your Tasmota devices to the `DEVICES` dict and their command aliases to `COMMANDS`.

## Running

```bash
python MUMBLE.py
```

## Supported Commands (text or voice)

| Command | Action |
|---|---|
| включи/выключи пол | Bathroom floor heating ON/OFF |
| включи/выключи бойлер | Boiler ON/OFF |
| включи/выключи радиатор | Bathroom radiator ON/OFF |
| статус [устройство] | Get current device state |
| какой тариф / price | Current + next hour Nordpool electricity price |
| parrot [text] | Bot repeats text and speaks it aloud locally |

## Project Structure

```
MUMBLE.py        # Main bot file
tts.py           # Piper TTS wrapper
masters          # Authorized usernames (one per line)
opus.dll         # Opus audio codec (Windows)
models/          # Piper voice model files (.onnx)
piper/           # Piper TTS executable
requirements.txt # Python dependencies
```
