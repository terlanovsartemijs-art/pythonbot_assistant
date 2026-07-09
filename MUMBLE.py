import ctypes
import ctypes.util
import ssl
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ---  Force opuslib to find opus.dll --------------------------------------------------------------------------------------------------------------------------------------------------------
dll_path = r"C:\Users\vvour\OneDrive\Desktop\Python_client_bot\opus.dll"
ctypes.CDLL(dll_path)

_original_find_library = ctypes.util.find_library
def _patched_find_library(name):
    if name == 'opus':
        return dll_path
    return _original_find_library(name)
ctypes.util.find_library = _patched_find_library

# --- Restore ssl.wrap_socket (removed in Python 3.13) --------------------------------------------------------------------------------------------------------------------------------------------------------
if not hasattr(ssl, 'wrap_socket'):
    def wrap_socket(sock, keyfile=None, certfile=None, server_side=False,
                     cert_reqs=ssl.CERT_NONE, ssl_version=ssl.PROTOCOL_TLS,
                     ca_certs=None, do_handshake_on_connect=True,
                     suppress_ragged_eofs=True, ciphers=None):
        context = ssl.SSLContext(ssl_version)
        context.verify_mode = cert_reqs
        context.check_hostname = False
        if certfile:
            context.load_cert_chain(certfile, keyfile)
        if ca_certs:
            context.load_verify_locations(ca_certs)
        if ciphers:
            context.set_ciphers(ciphers)
        return context.wrap_socket(sock, server_side=server_side,
                                    do_handshake_on_connect=do_handshake_on_connect,
                                    suppress_ragged_eofs=suppress_ragged_eofs)
    ssl.wrap_socket = wrap_socket

import pymumble_py3 as pymumble
import paho.mqtt.client as mqtt
import time
import re
import requests
from datetime import datetime
from zoneinfo import ZoneInfo


# --- MUMBLE CONFIG --------------------------------------------------------------------------------------------------------------------------------------------------------
HOST = "e.tgt.lv"
PORT = 35678
NAME = "Damovoi"
PASSWORD = "T9-SF(8gYU)"
CHANNEL = "Root"

# --- MQTT CONFIG --------------------------------------------------------------------------------------------------------------------------------------------------------
MQTT_HOST = "10.10.0.2"
MQTT_PORT = 1883

 
# --- NORDPOOL CONFIG --------------------------------------------------------------------------------------------------------------------------------------------------------
NORDPOOL_AREA = "LV"
NORDPOOL_CURRENCY = "EUR"
NORDPOOL_TZ = ZoneInfo("Europe/Riga")
 

# --- DEVICES --------------------------------------------------------------------------------------------------------------------------------------------------------
DEVICES = {
    "vanna_pol":      {"topic": "E98300", "relay": "POWER1", "name": "Vanna pol"},
    "boiler":         {"topic": "B52533", "relay": "POWER",  "name": "boiler"},
    "radiator_vanna": {"topic": "079256", "relay": "POWER",  "name": "Radiator vanna"},
    #"": {"topic": "", "relay": "POWER",  "name": ""},
    #"": {"topic": "", "relay": "POWER",  "name": ""}, # add devices ass needed for yourself
}

# --- DEVICE ALIASES (used for status lookups) --------------------------------------------------------------------------------------------------------------------------------------------------------
DEVICE_ALIASES = {
    "vanna_pol":      ["пол в ванной", "пол", "floor", "vanna pol", ],
    "vanna_pol_2":    ["пол 2", "floor 2", "vanna pol 2"],
    "boiler":         ["бойлер", "basement", "podval","boiler"],
    "radiator_vanna": ["радиатор", "батарея", "батарею", "radiator"],
}
# --- LIVE STATUS CACHE (populated from MQTT stat/ messages) ---
DEVICE_STATUS = {key: None for key in DEVICES}
 

# --- COMMANDS --------------------------------------------------------------------------------------------------------------------------------------------------------
COMMANDS = [
    (["включи пол в ванной", "включить пол", "turn on floor", "floor on",
      "вкл пол", "пол вкл", "включи пол"],
     "vanna_pol", "ON"),
    (["выключи пол в ванной", "выключить пол", "turn off floor", "floor off",
      "выкл пол", "пол выкл", "выключи пол"],
     "vanna_pol", "OFF"),

    (["включи подвал", "включи бойлер", "turn on boiler", "boiler on",
      "вкл подвал", "подвал вкл"],
     "boiler", "ON"),
    ([ "выключить бойлер", "выключи бойлер",  "turn off boiler", "boiler off",
      "выкл подвал", "подвал выкл"],
     "boiler", "OFF"),

    (["включи радиатор", "включить радиатор", " turn on radiator", "radiator on",
      "вкл радиатор", "радиатор вкл", "включи батарею"],
     "radiator_vanna", "ON"), 
    (["выключи радиатор", "выключить радиатор", "turn off radiator", "radiator off",
      "выкл радиатор", "радиатор выкл", "выключи батарею"],
     "radiator_vanna", "OFF"),

    (["включи свет", "включить свет", "turn on lights", "lights on", "свет вкл"],
     "vanna_pol", "ON"),
    (["выключи свет", "выключить свет", "turn off lights", "lights off", "свет выкл"],
     "vanna_pol", "OFF"),
]

STATUS_KEYWORDS = ["статус", "status"]
TARIFF_KEYWORDS = ["kakoj tarif", "какой тариф", "какой тариф электричества","price","тариф"]
 
# --- HELPERS -----------------------------------------------------------------------------------------------------------------------------------------------------
def strip_html(text):
    return re.sub(r"<[^>]+>", "", text).strip()
 
def parse_command(text_lower):
    for keywords, device_key, action in COMMANDS:
        for kw in keywords:
            if kw in text_lower:
                return device_key, action
    return None, None
 
def find_device_by_alias(text_lower):
    # Check longer aliases first so "пол 2" wins over plain "пол"
    candidates = []
    for key, aliases in DEVICE_ALIASES.items():
        for alias in aliases:
            candidates.append((alias, key))
    candidates.sort(key=lambda x: len(x[0]), reverse=True)
    for alias, key in candidates:
        if alias in text_lower:
            return key
    return None
 
def parse_status_command(text_lower):
    if any(kw in text_lower for kw in STATUS_KEYWORDS):
        return find_device_by_alias(text_lower)
    return None
 
def parse_tariff_command(text_lower):
    return any(kw in text_lower for kw in TARIFF_KEYWORDS)
 
def get_username(actor_id):
    try:
        return mumble.users[actor_id]["name"]
    except Exception:
        return f"User#{actor_id}"
 

 
def send_mqtt(device_key, action):
    device = DEVICES[device_key]
    topic = f"cmnd/{device['topic']}/{device['relay']}"
    mqtt_client.publish(topic, action, qos=0)
    print(f"[MQTT] {topic} -> {action}")
    return device["name"]
 
def request_status(device_key, timeout=2.0):
    """Ask the device for its current state and wait briefly for the reply."""
    device = DEVICES[device_key]
    topic = f"cmnd/{device['topic']}/{device['relay']}"
    mqtt_client.publish(topic, "", qos=0)  # empty payload = query current state
    start = time.time()
    while time.time() - start < timeout:
        if DEVICE_STATUS.get(device_key) is not None:
            return DEVICE_STATUS[device_key]
        time.sleep(0.1)
    return DEVICE_STATUS.get(device_key)
 
def get_nordpool_price():
    """Return (price_cents_per_kwh, interval_start, interval_end, next_price_cents, next_start, next_end)."""
    now = datetime.now(NORDPOOL_TZ)
    date_str = now.strftime("%Y-%m-%d")
    url = "https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices"
    params = {
        "date": date_str,
        "market": "DayAhead",
        "deliveryArea": NORDPOOL_AREA,
        "currency": NORDPOOL_CURRENCY,
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[NORDPOOL] Request failed: {e}")
        return None, None, None, None, None, None

    entries = data.get("multiAreaEntries", [])
    for i, entry in enumerate(entries):
        try:
            start = datetime.fromisoformat(entry["deliveryStart"].replace("Z", "+00:00")).astimezone(NORDPOOL_TZ)
            end = datetime.fromisoformat(entry["deliveryEnd"].replace("Z", "+00:00")).astimezone(NORDPOOL_TZ)
        except Exception:
            continue
        if start <= now < end:
            price_mwh = entry.get("entryPerArea", {}).get(NORDPOOL_AREA)
            if price_mwh is None:
                continue
            price_cents = (price_mwh / 1000) * 100  # EUR/MWh -> cents/kWh

            next_price_cents, next_start, next_end = None, None, None
            if i + 1 < len(entries):
                next_entry = entries[i + 1]
                try:
                    next_start = datetime.fromisoformat(next_entry["deliveryStart"].replace("Z", "+00:00")).astimezone(NORDPOOL_TZ)
                    next_end = datetime.fromisoformat(next_entry["deliveryEnd"].replace("Z", "+00:00")).astimezone(NORDPOOL_TZ)
                    next_price_mwh = next_entry.get("entryPerArea", {}).get(NORDPOOL_AREA)
                    if next_price_mwh is not None:
                        next_price_cents = (next_price_mwh / 1000) * 100
                except Exception:
                    pass

            return price_cents, start, end, next_price_cents, next_start, next_end

    return None, None, None, None, None, None

 



 # --- MQTT CALLBACKS --------------------------------------------------------------------------------------------------------------------------------------------------------
def on_mqtt_connect(client, userdata, flags, rc):
    print("[MQTT] Connected to broker")
    unique_topics = set(d["topic"] for d in DEVICES.values())
    for t in unique_topics:
        client.subscribe(f"stat/{t}/+")
 
def on_mqtt_message(client, userdata, msg):
    parts = msg.topic.split("/")
    if len(parts) == 3 and parts[0] == "stat":
        mqtt_topic, relay = parts[1], parts[2]
        payload = msg.payload.decode(errors="replace").strip().upper()
        if payload not in ("ON", "OFF"):
            return
        for key, dev in DEVICES.items():
            if dev["topic"] == mqtt_topic and dev["relay"] == relay:
                DEVICE_STATUS[key] = payload
                print(f"[MQTT] Status update: {dev['name']} -> {payload}")
 

# --- MQTT SETUP --------------------------------------------------------------------------------------------------------------------------------------------------------
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message
mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
mqtt_client.loop_start()
print("[MQTT] Connected to broker")

# --- MUMBLE CALLBACKS --------------------------------------------------------------------------------------------------------------------------------------------------------
def message_callback(message):
    text = strip_html(message.message)
    text_lower = text.lower()
    username = get_username(message.actor)
    print(f"[MUMBLE] {username}: {text}")
    
    channel = None
    try:
        channel = mumble.channels.find_by_name(CHANNEL)
    except Exception:
        pass
 
    def reply_to_channel(msg):
        print(f"[MUMBLE] -> {msg}")
        if channel:
            try:
                channel.send_text_message(msg)
            except Exception as e:
                print(f"[WARN] Could not send reply: {e}")
 



    # 1. Tariff command
    if parse_tariff_command(text_lower):
        now = datetime.now()
        minutes_left = 15 - (now.minute % 15)
        result = f" ближайшие {minutes_left}  минут "
        price_cents, start, end, next_price_cents, next_start, next_end = get_nordpool_price()
        if price_cents is not None:
            reply = (
                f" {result}"
                f" цена :  {price_cents:.2f} цента за киловатт час"
            )
            if next_price_cents is not None:
                reply += f" | следующиe 15 минут: {next_price_cents:.2f} цента за киловатт час"
            reply_to_channel(reply)
        else:
            reply_to_channel("Could not fetch the current Nordpool tariff.")
        return
 
    # 2. Status command
    status_device = parse_status_command(text_lower)
    if status_device:
        
        device_name = DEVICES[status_device]["name"]
        state = request_status(status_device)
        
        if state:
            state_ru = "включён" if state == "ON" else "выключен"
            reply_to_channel(f"<b>{device_name}</b> сейчас: <b>{state_ru}</b>")
        else:
            reply_to_channel(f"Нет ответа от <b>{device_name}</b> повторите попытку скоро.")
        return
    
    # 3. ON/OFF command
    device_key, action = parse_command(text_lower)
    if device_key:
        device_name = DEVICES[device_key]["name"]
        current_state = request_status(device_key)

        if current_state == action:
            state_ru = "уже включён" if action == "ON" else "уже выключен"
            reply_to_channel( 
                f"<b>{device_name}</b> {state_ru} "
            )
        else:
            send_mqtt(device_key, action)
            action_ru = "включён" if action == "ON" else "выключен"
            reply_to_channel(
                f"<b>{device_name}</b> {action_ru}"
            )
        return
 
    print(f"[MUMBLE] команда не распознана  {username}")
 
def audio_callback(user, soundchunk):
    print(f"[AUDIO] {user['name']}: {len(soundchunk.pcm)} bytes")
 

# --- MUMBLE SETUP --------------------------------------------------------------------------------------------------------------------------------------------------------
mumble = pymumble.Mumble(HOST, NAME, port=PORT, password=PASSWORD)
mumble.callbacks.set_callback(
    pymumble.constants.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, message_callback)
mumble.callbacks.set_callback(
    pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, audio_callback)

mumble.start()
mumble.is_ready()

target_channel = mumble.channels.find_by_name(CHANNEL)
if target_channel:
    target_channel.move_in()
    print(f"[MUMBLE] Joined channel: {CHANNEL}")
else:
    print(f"[MUMBLE] Channel '{CHANNEL}' not found")

print("[MUMBLE] Listening for commands...")

try:
    while mumble.is_alive():
        time.sleep(1)
except KeyboardInterrupt:
    print("[BOT] Shutting down...")
    mqtt_client.loop_stop()
    mumble.stop()