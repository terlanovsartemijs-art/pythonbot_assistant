import ctypes
import ctypes.util
import ssl
import threading
import time
import wave
import sys
from pathlib import Path
from array import array
from struct import pack
import numpy as np
from audio_scripts.tts import *
from audio_scripts.audio import *
from faster_whisper import WhisperModel
import librosa
import pymumble_py3 as pymumble
import paho.mqtt.client as mqtt
import time
import re
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import importlib
import requests
commands = {}

PLUGINS_FOLDER = "plugins"

def register_command(name,function):
    commands[name] = function

# loads all plugin
def load_commands(dir_name = PLUGINS_FOLDER):
    root = Path(__file__).parent / f"{dir_name}"

    for folder in root.rglob("__init__.py"):
        package = folder.parent.relative_to(root.parent)
        module_name = ".".join(package.parts)

        importlib.import_module(module_name)

# loads a specific plugin
# can be used to reload plugins
# TO DO : If any of commands is removed, get it out of commands
def reload_plugin(plugin_name,dir_name = PLUGINS_FOLDER):
    print(f"Trying to reload : {plugin_name} in {dir_name}")
    module_name = f"{dir_name}.{plugin_name}"

    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


def reply_to_channel(msg,context):
    channel = context["mumble"].channels.find_by_name(context["mumble_settings"][4])
    print(f"[MUMBLE] -> {msg}")
    if channel:
        try:
            channel.send_text_message(msg)
        except Exception as e:
            print(f"[WARN] Could not send reply: {e}")

def identify_lang(text):
    text = text.lower()
    if any('\u0400' <= ch <= '\u04FF' for ch in text):
        return "ru"
    if any(ch in ["ā", "ē", "ī", "ū", "č", "š", "ž", "ģ", "ķ", "ļ", "ņ"] for ch in text):
        return "lv"
    #if couldn't identify lang, use english
    return "en"