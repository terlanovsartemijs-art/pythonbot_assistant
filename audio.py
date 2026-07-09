import pyaudio
import wave
import datetime
from array import array
from struct import pack
import numpy as np
import openwakeword
from openwakeword.model import Model

def record(outputFile,stream,stream_setting,model,p):
    CHUNK = stream_setting["frames_per_buffer"]
    RATE = stream_setting["rate"]
    RECORD_SECONDS = stream_setting["record_seconds"]
    CHANNELS = stream_setting["channels"]
    FORMAT = stream_setting["format"]

    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frame = np.frombuffer(data, dtype=np.int16)
        prediction = model.predict(frame)

        
        if prediction['hey_jarvis'] > 0.6:
            return 0
        if prediction['alexa'] > 0.7:
            print("Wake word detected!")
            model = Model()
            break
    print("* recording")

    frames = []

    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("* done recording")

    #stream.stop_stream()
    #stream.close()
    #p.terminate()

    wf = wave.open(outputFile, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

def play(filename):
    wf = wave.open(filename, 'rb')
    p = pyaudio.PyAudio()
    CHUNK = 1280

    p = pyaudio.PyAudio()

    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)
    data = wf.readframes(CHUNK)
    while len(data) > 0:
        stream.write(data)
        data = wf.readframes(CHUNK)
    stream.stop_stream()
    stream.close()
    p.terminate()