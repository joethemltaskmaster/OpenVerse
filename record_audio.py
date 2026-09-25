import pyaudio
import wave
import whisper
import os
# import subprocess

# print(subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout)

os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

# Recording settings
FORMAT = pyaudio.paInt16   # 16-bit resolution
CHANNELS = 1                # mono
RATE = 44100                 # samples per second
CHUNK = 1024                 # buffer size
RECORD_SECONDS = 10
OUTPUT_FILENAME = "test.wav"
for_whisper = r"C:\Users\Joseph\Desktop\OpenVerse\test_1.mp3"

def record_audio():
    audio = pyaudio.PyAudio()

    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    print(f"Recording for {RECORD_SECONDS} seconds...")

    frames = []
    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("Finished recording.")

    stream.stop_stream()
    stream.close()
    audio.terminate()

    with wave.open(OUTPUT_FILENAME, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))

    print(f"Saved to {OUTPUT_FILENAME}")

def transcribe_audio(filename):
    print("Loading Whisper base model...")
    model= whisper.load_model('small')

    print("Transcribing....")
    result= model.transcribe(filename)

    print("\n--- Transcription Result ---")
    print(result["text"])
    print("------------------------------")

if __name__ == "__main__":
    record_audio()
    transcribe_audio(for_whisper)
