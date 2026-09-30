"""
transcription.py — transcribe_audio() with a remote GPU (Colab) and a local CPU fallback.

Setup (values are printed by the Colab notebook; they change every session):
    PowerShell:  $env:OPENVERSE_COLAB_URL="https://xxxx.trycloudflare.com"
                 $env:OPENVERSE_COLAB_TOKEN="..."

Modes:
    auto   (default) try the Colab server, fall back to local CPU if unreachable/failing
    remote           Colab only; raise on failure (useful to test the tunnel)
    local            local CPU only

Returns the same shape the rest of OpenVerse expects:
    {"text": str, "segments": [{"start": float, "end": float, "text": str}, ...]}

Needs: pip install requests faster-whisper
"""

from dotenv import load_dotenv
import json
import os

load_dotenv(".env")


def _remote_config():
    url = os.environ.get("OPENVERSE_COLAB_URL", "").strip().rstrip("/")
    token = os.environ.get("OPENVERSE_COLAB_TOKEN", "").strip()
    return url, token

# var= _remote_config()
# print(var)

def _transcribe_remote(filename, language, url, token):
    import requests  # lazy: local mode shouldn't require it

    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(f"{url}/health", headers=headers, timeout=5)
    if r.status_code == 401:
        raise PermissionError("server rejected the token (stale OPENVERSE_COLAB_TOKEN?)")
    r.raise_for_status()
    info = r.json()
    print(f"Remote server reachable (device={info.get('device')}, model={info.get('model')}). Uploading...")

    segs, done = [], False
    with open(filename, "rb") as f:
        with requests.post(
            f"{url}/transcribe",
            headers=headers,
            files={"file": f},
            data={"language": language or ""},
            stream=True,
            timeout=(10, 120),  # connect, max silence between streamed lines
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                msg = json.loads(line)
                kind = msg.get("type")
                if kind == "segment":
                    segs.append({"start": msg["start"], "end": msg["end"], "text": msg["text"]})
                    print(f"  [{msg['start']:7.1f}s] {msg['text'].strip()}")
                elif kind == "error":
                    raise RuntimeError(f"server error: {msg['message']}")
                elif kind == "done":
                    done = True
    if not done:
        raise RuntimeError("stream ended before the server finished (connection dropped?)")
    return segs


def _transcribe_local(filename, model_name, language):
    from faster_whisper import WhisperModel

    print(f"Loading faster-whisper {model_name} on cpu...")
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    print("Transcribing locally....")
    segments, _info = model.transcribe(filename, language=language or None, vad_filter=True)
    return [{"start": s.start, "end": s.end, "text": s.text} for s in segments]


def transcribe_audio(filename, model_name="small", language="en", mode="auto"):
    """model_name applies to the LOCAL fallback; the remote model is set in the notebook."""
    if mode not in ("auto", "remote", "local"):
        raise ValueError("mode must be 'auto', 'remote' or 'local'")

    segs = None
    if mode in ("auto", "remote"):
        url, token = _remote_config()
        if not url:
            if mode == "remote":
                raise RuntimeError("OPENVERSE_COLAB_URL is not set")
            print("OPENVERSE_COLAB_URL not set; using local CPU.")
        else:
            try:
                segs = _transcribe_remote(filename, language, url, token)
            except Exception as e:
                if mode == "remote":
                    raise
                print(f"Remote transcription failed ({type(e).__name__}: {e}); falling back to local CPU.")

    if segs is None:
        segs = _transcribe_local(filename, model_name, language)

    text = "".join(s["text"] for s in segs).strip()
    print("\n--- Transcription Result ---")
    print(text)
    print("------------------------------")
    return {"text": text, "segments": segs}
