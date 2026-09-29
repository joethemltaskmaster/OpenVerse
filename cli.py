"""
cli.py — end-to-end test harness: record_audio.py -> Whisper -> scripture detector.

Expected layout:
    OpenVerse/
        record_audio.py
        scripture_detector/
            cli.py  detector.py  parser.py  ...

Run from anywhere:
    python scripture_detector/cli.py text "Turn to 2 John chapter 1 verse 3 to 8"
    python scripture_detector/cli.py file transcript.txt
    python scripture_detector/cli.py audio                 # uses record_audio.for_whisper (sermon.mp3)
    python scripture_detector/cli.py audio other.mp3 --model base
    python scripture_detector/cli.py record --seconds 30   # mic -> test.wav -> transcribe -> detect

--json out.json saves structured results; --show-transcript prints the full
text, the timestamped Whisper segments (audio modes), and each raw match, so
you can spot references split across segment boundaries.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                    # detector modules
sys.path.insert(0, os.path.dirname(HERE))   # record_audio.py in the parent folder


def _load_record_audio():
    # Lazy: text/file modes shouldn't need pyaudio or whisper installed.
    try:
        import record_audio
    except ImportError as e:
        sys.exit(f"[error] could not import record_audio.py ({e}). "
                 "Keep scripture_detector/ inside the OpenVerse folder and "
                 "make sure pyaudio and openai-whisper are installed.")
    return record_audio


def _fmt_time(seconds):
    if seconds is None:
        return "  --  "
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def _print_refs(refs, show_transcript=False):
    if not refs:
        print("  (no references detected)")
        return
    for r in refs:
        tag = " [inferred]" if r.inferred_from_context else ""
        print(f"  {_fmt_time(r.timestamp)}  {str(r):<28}{tag}")
        if show_transcript:
            print(f"           raw: {r.raw_text!r}")


def _detect_segments(result):
    from scripture_detector.detector import ScriptureDetector
    return ScriptureDetector().detect_segments(result["segments"])


def _finish(refs, args, transcript=None, segments=None):
    if args.show_transcript:
        if segments:
            print("\n--- segments ---")
            for seg in segments:
                print(f"  {_fmt_time(seg['start'])}  {seg['text'].strip()}")
        elif transcript:
            print("\n--- transcript ---")
            print(transcript.strip())
    print("\n--- detected references ---")
    _print_refs(refs, args.show_transcript)
    print(f"\n{len(refs)} reference(s) found.")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in refs], f, indent=2)
        print(f"Saved to {args.json}")


def _run_audio(ra, path, args):
    if not os.path.isfile(path):
        sys.exit(f"[error] audio file not found: {path}")
    result = ra.transcrib_audio(path, model_name=args.model, mode=args.mode)
    if not result or "segments" not in result:
        sys.exit("[error] transcribe_audio() returned no segments — is the patched record_audio.py in use?")
    _finish(_detect_segments(result), args, result.get("text"), result["segments"])


def cmd_text(args):
    from scripture_detector.detector import ScriptureDetector
    _finish(ScriptureDetector().detect(args.text), args, args.text)


def cmd_file(args):
    from scripture_detector.detector import ScriptureDetector
    if not os.path.isfile(args.path):
        sys.exit(f"[error] file not found: {args.path}")
    with open(args.path, encoding="utf-8") as f:
        text = f.read()
    _finish(ScriptureDetector().detect(text), args, text)


def cmd_audio(args):
    ra = _load_record_audio()
    _run_audio(ra, args.path or ra.for_whisper, args)


def cmd_record(args):
    ra = _load_record_audio()
    wav = ra.record_audio(seconds=args.seconds, filename=args.save or ra.OUTPUT_FILENAME)
    _run_audio(ra, wav, args)


def build_parser():
    p = argparse.ArgumentParser(description="OpenVerse scripture detector test CLI")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", metavar="FILE", help="save results as JSON")
    common.add_argument("--show-transcript", action="store_true")

    audio_common = argparse.ArgumentParser(add_help=False)
    audio_common.add_argument("--model", default="small", help="LOCAL fallback whisper model (tiny/base/small/...)")
    audio_common.add_argument("--mode", choices=["auto", "remote", "local"], default="auto",
                              help="auto = Colab GPU with local CPU fallback (default)")

    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("text", parents=[common], help="detect in a string")
    s.add_argument("text")
    s.set_defaults(func=cmd_text)

    s = sub.add_parser("file", parents=[common], help="detect in a transcript text file")
    s.add_argument("path")
    s.set_defaults(func=cmd_file)

    s = sub.add_parser("audio", parents=[common, audio_common], help="transcribe an audio file, then detect")
    s.add_argument("path", nargs="?", help="defaults to for_whisper in record_audio.py")
    s.set_defaults(func=cmd_audio)

    s = sub.add_parser("record", parents=[common, audio_common], help="record from mic, transcribe, detect")
    s.add_argument("--seconds", type=int, default=10)
    s.add_argument("--save", metavar="WAV", help="recording filename (default: test.wav)")
    s.set_defaults(func=cmd_record)

    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)

# path, model_name=args.model, mode=args.mode