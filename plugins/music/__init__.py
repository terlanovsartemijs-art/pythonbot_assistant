from command_handler import *
#plugin specific dependencies
import threading
import subprocess
from threading import Thread,Event
import yt_dlp
from urllib.parse import urlparse

# This is quite a heavy plugin, so it is unlikely to work on weak routers

curr_thread = None
event = None
ffmpeg_process = None

def is_url(text):
    parsed = urlparse(text)
    return parsed.scheme in ("http", "https")    

def find_song(text,context):
    ""
    ydl_opts = {
        "format": "bestaudio",
        "quiet": True
    }

    if is_url(text):
        query = text
    else:
        query = f"ytsearch1:{text}"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            query,
            download=False
        )
        #for something in info["entries"][0]:
        #    print(something)
        print(info)
        if(not is_url(text)):
            title = info['entries'][0]['title']
            author = info['entries'][0]['uploader']
            print(info['entries'][0]['title'])
            print(info['entries'][0]['uploader'])
            print(info['entries'][0]['duration'])
            url = info['entries'][0]['url']
        else:
            print(info['title'])
            title = info['title']
            print(info['uploader'])
            author = info['uploader']
            print(info['duration'])
            url = info['url']
        reply_to_channel(f"{author} - {title}",context)
        return url

def music_thread(url,context,event: Event):
    global curr_thread
    global ffmpeg_process
    ffmpeg_process = subprocess.Popen(
        [
            "ffmpeg",
            "-i", url,
            "-vn",
            "-f", "s16le",
            "-ar", "48000",
            "-ac", "1",
            "pipe:1"
        ],
        stdout = subprocess.PIPE,
        bufsize=0
    )

    while True:
        if event.is_set():
            print("Turning thread off...")
            break

        chunk = ffmpeg_process.stdout.read(1920)
        context["mumble"].sound_output.add_sound(chunk)
        if not chunk:
            break
    if ffmpeg_process.poll() is None:
        ffmpeg_process.kill()
    curr_thread = None

# get audiostream from youtube
def play_music(text, context):
    global curr_thread, event

    if curr_thread and curr_thread.is_alive():
        event.set()
        curr_thread.join()
    event = Event()
    url = find_song(text, context)
    curr_thread = Thread(
        target=music_thread,
        args=(url, context, event)
    )
    curr_thread.start()


def stop_music(text,context):
    print("Trying to stop the music")
    global curr_thread
    global event
    global ffmpeg_process
    if curr_thread and curr_thread.is_alive():
        event.set()
        ffmpeg_process.kill()
        curr_thread.join()


def register(register_command):
    root = Path(__file__).parent / "config"
    with open(root,"r") as fp:
        #start commands
        for line in fp:
            if line.strip() != "":
                register_command(f"{line.strip()}",play_music)
            else:
                break
        
        #stop commands
        for line in fp:
            register_command(f"{line.strip()}",stop_music)
#register command
register(register_command)