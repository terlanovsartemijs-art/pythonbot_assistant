import ctypes
import ctypes.util
import ssl
import threading
import time
import wave
from pathlib import Path
from array import array
from struct import pack
import numpy as np
from tts import *
from audio import *
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
commands = {}

def register_command(name,function):
    commands[name] = function

def load_commands(dir_name):
    root = Path(__file__).parent / "plugins"

    for folder in root.rglob("__init__.py"):
        package = folder.parent.relative_to(root.parent)
        module_name = ".".join(package.parts)

        importlib.import_module(module_name)


