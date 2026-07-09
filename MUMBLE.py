import ctypes
import ctypes.util
import ssl
import threading
import time
import wave
from array import array
from struct import pack
import numpy as np
from tts import *
from audio import *
from faster_whisper import WhisperModel
import librosa
model = WhisperModel("small", device="cpu", compute_type="int8")

# Compatibility shim: ssl.wrap_socket was removed in Python 3.13
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


#dll_path = r"C:\Users\vvour\OneDrive\Desktop\opus.dll"

# Load the DLL into memory right now
#ctypes.CDLL(dll_path)

dll_path = "/usr/lib/x86_64-linux-gnu/libopus.so"
ctypes.CDLL(dll_path)

# Force find_library to return our path instead of searching
_original_find_library = ctypes.util.find_library
def _patched_find_library(name):
    if name == 'opus':
        return dll_path
    return _original_find_library(name)
ctypes.util.find_library = _patched_find_library
import pymumble_py3 as pymumble 
import time


# --- CONNECTION CONFIGURATION ---
HOST = "e.tgt.lv"
PORT = 35678         # Standard Mumble voice port
NAME = "JansBot"
PASSWORD = "T9-SF(8gYU)"        # Server password if applicable
CHANNEL = "Root"     # Target channel name to join

def load_masters(filename):
    with open(filename) as file:
        masters = [line.rstrip() for line in file]
    return masters
masters = load_masters("masters")  

def message_callback(message):
    """Triggered whenever someone sends a text message in the channel"""
    print(f"[{message.actor}] received text: {message.message}")
    
    # separate command logic from message_callback
    command,_,clean_text = message.message.partition(" ")
    # Commands
    sender = mumble.users[message.actor]
    do_command(command,clean_text,sender["name"])    

# Integrate wakeword
def audio_callback(user, soundchunk):
    """Triggered continuously when a user is speaking in the channel"""
    # soundchunk.pcm contains the raw 16-bit 48kHz stereo/mono PCM audio bytes
    user_id = user["session"]

    if user_id not in buffers:
        buffers[user_id] = bytearray()

    buffers[user_id].extend(soundchunk.pcm)
    last_audio[user_id] = time.time()

    #print(f"Listening to user  {user['name']}: {len(soundchunk.pcm)} bytes of audio data")
    # You can pass soundchunk.pcm into an STT engine or save it here
    # we're listening whether or not user stopped talking in check_silence() on separate thread
    
last_audio = {}  # time, not frame
buffers = {} # audio buffers. Each user has separate. Identified by user_id 

def check_silence():
    print("Checking for silence...")
    while True:
        now = time.time()

        for user_id in list(last_audio.keys()):
            if now - last_audio[user_id] > 1.0 and last_audio[user_id] != -1:
                # user has been silent for 1 second
                last_audio[user_id] = -1
                process_audio(user_id)

        time.sleep(0.1)
#speech-to-text
#faster whisper, maybe vox later
#save into a file
def process_audio(user_id):
    
    pcm_bytes = bytes(buffers[user_id])
    buffers[user_id].clear()

    filename = f"user_{user_id}.wav"

    with wave.open(filename, "wb") as wav_file:
        wav_file.setnchannels(1)      # mono
        wav_file.setsampwidth(2)      # 16-bit PCM = 2 bytes
        wav_file.setframerate(48000)  # Mumble audio rate
        wav_file.writeframes(pcm_bytes)

    print(f"Saved {filename}")

    # safe as audio file

    segments, info = model.transcribe(filename)
    print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

    text = ""
    for segment in segments:
        text += segment.text

    print("Recognized:", text)
    command,_,text = text.partition(" ")
    sender = mumble.users[user_id]["name"]
    do_command(command,text,sender)

def do_command(command,clean_text, name):
    if(name not in masters ):
        mumble.channels.find_by_name(CHANNEL).send_text_message(f"{name} you're not my master !")
        return
    match command.lower():
        case "hello":
            mumble.channels.find_by_name(CHANNEL).send_text_message("Hello from the Python client")
        case "parrot" | "papagailis" | "попугай":
            mumble.channels.find_by_name(CHANNEL).send_text_message(clean_text)
            # rn it voices locally on the device where bot is living
            print(clean_text)
            voice(clean_text, "ru")  # Add language recognition
            play("output.wav")       # Plays localy ! On device !
        case "send" | "aizsūti" | "отправь":
            group,_,clean_text = clean_text.partition(" ")
            # Add edge case when group or text is empty
            # Add edge case when no group with such name is found
            subprocess.run([
                "curl",
                "-X", "PUT",
                "-H", "Content-Type: text/plain",
                "--data", clean_text,
                f"https://rekini.tgt.lv/{group}",
            ], check=True)
        case "add" | "pievieno" | "добавь" :
            master,_,master_name = clean_text.partition(" ")
            if (master.lower() in ["master","masters","pavēlnieks","king","karalis"]):
                print()

def add_master(filename):
    # add to file masters
    print()

def rm_master(filename):
    # delete from file masters
    print()

# 1. Initialize the Mumble client
mumble = pymumble.Mumble(HOST, NAME, port=PORT, password=PASSWORD)

# 2. Set up event listeners for text messages and incoming audio streams
mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, message_callback)
mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, audio_callback)

# 3. Check whether user stopped talking
threading.Thread(
    target=check_silence,
    daemon=True
).start()

# 4. Start the connection thread
mumble.start()
mumble.is_ready() # Wait until connection handshake finishes
mumble.set_receive_sound(True) 

# 5. Find and switch to the target channel
target_channel = mumble.channels.find_by_name(CHANNEL)
if target_channel:
    target_channel.move_in()
else:
    print(f"Channel '{CHANNEL}' not found, staying in current channel")
target_channel.move_in()

print(f"Bot successfully connected as client and joined channel: {CHANNEL}")

# 6. Keep main thread alive to listen for data
try:
    while mumble.is_alive():
        time.sleep(1)
except KeyboardInterrupt:
    mumble.stop()