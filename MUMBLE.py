from command_handler import *
load_commands()
reload_plugin("parrot")
print(commands)   

#model = WhisperModel("small", device="cpu", compute_type="int8")


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

# Load the DLL into memory right now
print("Loading DLL into memory...")
#ctypes.CDLL(dll_path)
dll_path = "/usr/lib/x86_64-linux-gnu/libopus.so.0"
ctypes.CDLL(dll_path)

# Force find_library to return our path instead of searching
_original_find_library = ctypes.util.find_library
def _patched_find_library(name):
    if name == 'opus':
        return dll_path
    return _original_find_library(name)
ctypes.util.find_library = _patched_find_library

# --- MUMBLE CONFIG --------------------------------------------------------------------------------------------------------------------------------------------------------
HOST = "e.tgt.lv"
PORT = 35678                    # Standard Mumble voice port
NAME = ["JansBot","BotJans","Botyara","жан-бот"]             # Change the name of the bot to anything you like
PASSWORD = "T9-SF(8gYU)"        # Server password if applicable
CHANNEL = "Root"                # Target channel name to join
 
# --- HELPERS -----------------------------------------------------------------------------------------------------------------------------------------------------
def strip_html(text):
    return re.sub(r"<[^>]+>", "", text).strip()
  
def get_username(actor_id):
    try:
        return mumble.users[actor_id]["name"]
    except Exception:
        return f"User#{actor_id}"
 
#-----------HELPER FUNCTIONS -------------------------------------------------
def is_authorized(username,masters):
    return username in masters

def load_masters(filename):
    with open(filename) as file:
        masters = [line.rstrip() for line in file]
    return masters
masters = load_masters("masters")  

def reply_to_channel(msg):
    channel = mumble.channels.find_by_name(CHANNEL)
    print(f"[MUMBLE] -> {msg}")
    if channel:
        try:
            channel.send_text_message(msg)
        except Exception as e:
            print(f"[WARN] Could not send reply: {e}")

def message_callback(message):
    """Triggered whenever someone sends a text message in the channel"""
    text = strip_html(message.message)
    username = get_username(message.actor)
    print(f"[MUMBLE] {username}: {text}")

    # separate command logic from message_callback
    # Commands
    do_command(text,username)    

# Turned off right now
def audio_callback(user, soundchunk):
    """Triggered continuously when a user is speaking in the channel"""
    # soundchunk.pcm contains the raw 16-bit 48kHz stereo/mono PCM audio bytes
    #user_id = user["session"]

    #if user_id not in buffers:
    #    buffers[user_id] = bytearray()

    #buffers[user_id].extend(soundchunk.pcm)
    #last_audio[user_id] = time.time()

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

    recordings_dir = Path("recordings")
    recordings_dir.mkdir(exist_ok=True)

    filename = f"user_{user_id}.wav"

    with wave.open(str(recordings_dir / filename), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(48000)
        wav_file.writeframes(pcm_bytes)

    print(f"Saved {filename}")

    # safe as audio file

    segments, info = model.transcribe(filename)
    print("Detected language '%s' with probability %f" % (info.language, info.language_probability))

    text = ""
    for segment in segments:
        text += segment.text

    print("Recognized:", text)
    sender = mumble.users[user_id]["name"]
    do_command(text,sender)

def do_command(clean_text, username):
    # check for bot names in text
    name_in_text = 0
    found_name = ""
    for name_variant in NAME:
        if name_variant.lower() in clean_text.lower():
            name_in_text = 1
            found_name = name_variant
            break
    if(not name_in_text):
        return

    copy = clean_text.split()
    for w in copy:
        if found_name.lower() == w.lower():
            print(found_name.lower() + " is equal to " + w.lower())
            copy.remove(w)
            break
    clean_text = " ".join(copy)
    print(clean_text)

    # check if user is one of masters
    if not is_authorized(username,masters):
        reply_to_channel(f"{username} you are not my master !")
        print(f"[AUTH] Rejected command from unauthorized user: {username}")
        return
    
    # important information that might be used in commands.
    context = {
        "mumble_settings" : [HOST,PORT,NAME,PASSWORD,CHANNEL],
        "mumble" : mumble,
        "username" : username
    }
 
    # Plugin commands
    if clean_text.lower() in commands:
        commands[clean_text.lower()](clean_text,context)
        return

    command,_,text_copy = clean_text.partition(" ")
    command = command.lower()

    if command.lower() in commands:
        commands[command.lower()](text_copy,context)
        return
    
    print(f"{username} [MUMBLE] команда не распознана ")

# 1. Initialize the Mumble client
mumble = pymumble.Mumble(HOST, NAME[0], port=PORT, password=PASSWORD)

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
    print(f"[MUMBLE] Joined channel: {CHANNEL}")
else:
    print(f"[MUMBLE] Channel '{CHANNEL}' not found")
print("[MUMBLE] Listening for commands...")

print(f"Bot successfully connected as client and joined channel: {CHANNEL}")

# 6. Keep main thread alive to listen for data
try:
    while mumble.is_alive():
        time.sleep(1)
except KeyboardInterrupt:
    print("[BOT] Shutting down...")
    mqtt_client = commands["get_mqtt"](1)
    mqtt_client.loop_stop()
    mumble.stop()