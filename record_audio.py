import pyaudio
import wave
# import whisper
from faster_whisper import WhisperModel
import os
# import subprocess

# print(subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout)

# os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

# Recording settings
FORMAT = pyaudio.paInt16   # 16-bit resolution
CHANNELS = 1                # mono
RATE = 44100                 # samples per second
CHUNK = 1024                 # buffer size
RECORD_SECONDS = 10
OUTPUT_FILENAME = "test.wav"
for_whisper = r"C:\Users\Joseph\Desktop\OpenVerse\sermon.mp3"

def record_audio(seconds=RECORD_SECONDS, filename=OUTPUT_FILENAME):
    audio = pyaudio.PyAudio()

    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    print(f"Recording for {seconds} seconds...")

    frames = []
    for _ in range(0, int(RATE / CHUNK * seconds)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("Finished recording.")

    stream.stop_stream()
    stream.close()
    audio.terminate()

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))

    print(f"Saved to {filename}")
    return filename

def transcrib_audio(filename, model_name="small", mode="auto", language="en"):
    from transcription import transcribe_audio
    return transcribe_audio(filename=filename, model_name=model_name, mode=mode, language=language)
    # import ctranslate2

    # use_gpu = ctranslate2.get_cuda_device_count() > 0
    # device = "cuda" if use_gpu else "cpu"
    # compute_type = "float16" if use_gpu else "int8"

    # print(f"Loading faster-whisper {model_name} on {device}...")
    # model = WhisperModel(model_name, device=device, compute_type=compute_type)

    # print("Transcribing....")
    # segments, info = model.transcribe(filename, language=language, vad_filter=True)
    # segs = [{"start": s.start, "end": s.end, "text": s.text} for s in segments]
    # text = "".join(s["text"] for s in segs).strip()

    # print("\n--- Transcription Result ---")
    # print(text)
    # print("------------------------------")
    # return {"text": text, "segments": segs}

if __name__ == "__main__":
    # record_audio()
    from transcription import transcribe_audio
    transcrib_audio(for_whisper)
