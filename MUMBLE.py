import ctypes
import ctypes.util
import ssl
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# --- Fix 1: Force opuslib to find opus.dll ---
dll_path = r"C:\Users\vvour\OneDrive\Desktop\Python_client_bot\opus.dll"
ctypes.CDLL(dll_path)

_original_find_library = ctypes.util.find_library
def _patched_find_library(name):
    if name == 'opus':
        return dll_path
    return _original_find_library(name)
ctypes.util.find_library = _patched_find_library

# --- Fix 2: Restore ssl.wrap_socket (removed in Python 3.13) ---
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

# --- MUMBLE CONFIG ---
HOST = "e.tgt.lv"
PORT = 35678
NAME = "pitonBot"
PASSWORD = "T9-SF(8gYU)"
CHANNEL = "Root"

# --- MQTT CONFIG ---
MQTT_HOST = "10.10.0.2"
MQTT_PORT = 1883

# --- DEVICES ---
DEVICES = {
    "vanna_pol":      {"topic": "E98300", "relay": "POWER1", "name": "Vanna pol"},
    "vanna_pol_2":    {"topic": "E98300", "relay": "POWER2", "name": "Vanna pol 2"},
    "podval":         {"topic": "B52533", "relay": "POWER",  "name": "Podval"},
    "radiator_vanna": {"topic": "079256", "relay": "POWER",  "name": "Radiator vanna"},
}

# --- COMMANDS ---
COMMANDS = [
    (["включи пол в ванной", "включить пол", "turn on floor", "floor on",
      "вкл пол", "пол вкл", "включи пол"],
     "vanna_pol", "ON"),
    (["выключи пол в ванной", "выключить пол", "turn off floor", "floor off",
      "выкл пол", "пол выкл", "выключи пол"],
     "vanna_pol", "OFF"),

    (["включи подвал", "включить подвал", "turn on basement", "basement on",
      "вкл подвал", "подвал вкл"],
     "podval", "ON"),
    (["выключи подвал", "выключить подвал", "turn off basement", "basement off",
      "выкл подвал", "подвал выкл"],
     "podval", "OFF"),

    (["включи радиатор", "включить радиатор", "turn on radiator", "radiator on",
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

# --- HELPERS ---
def strip_html(text):
    return re.sub(r"<[^>]+>", "", text).strip()

def parse_command(text):
    text_lower = strip_html(text).lower()
    for keywords, device_key, action in COMMANDS:
        for kw in keywords:
            if kw in text_lower:
                return device_key, action
    return None, None

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

# --- MQTT SETUP ---
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
mqtt_client.loop_start()
print("[MQTT] Connected to broker")

# --- MUMBLE CALLBACKS ---
def message_callback(message):
    text = strip_html(message.message)
    username = get_username(message.actor)
    print(f"[MUMBLE] {username}: {text}")

    device_key, action = parse_command(text)
    if device_key:
        device_name = send_mqtt(device_key, action)
        action_ru = "включён" if action == "ON" else "выключен"
        action_en = "ON" if action == "ON" else "OFF"
        reply = (
            
            f"<b>{device_name}</b>  {action_ru}"
        )
        try:
            channel = mumble.channels.find_by_name(CHANNEL)
            if channel:
                channel.send_text_message(reply)
        except Exception as e:
            print(f"[WARN] Could not send reply: {e}")
    else:
        print(f"[MUMBLE] No command recognized from {username}")

def audio_callback(user, soundchunk):
    print(f"[AUDIO] {user['name']}: {len(soundchunk.pcm)} bytes")

# --- MUMBLE SETUP ---
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