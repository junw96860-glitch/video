#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import argparse
import tempfile
from typing import List

def read_text(path: str) -> str:
  with open(path, "r", encoding="utf-8") as f:
    return f.read().strip()

def split_for_tts(text: str, max_len: int = 600) -> List[str]:
  import re
  parts = []
  buf = ""
  for token in re.split(r"([。！？!?\n])", text):
    if token is None:
      continue
    buf += token
    if token in "。！？!?\n" and len(buf) >= max_len:
      parts.append(buf.strip())
      buf = ""
    elif len(buf) >= max_len:
      parts.append(buf.strip())
      buf = ""
  if buf.strip():
    parts.append(buf.strip())
  return parts

def synth_gtts(text: str, out_path: str, language: str = "zh"):
  from gtts import gTTS
  from pydub import AudioSegment
  chunks = split_for_tts(text, 400)
  segs = []
  for ch in chunks:
    tts = gTTS(text=ch, lang=language)
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tts.write_to_fp(tmp)
    tmp.close()
    segs.append(AudioSegment.from_file(tmp.name))
    os.unlink(tmp.name)
  total = segs[0] if segs else AudioSegment.silent(duration=500)
  for s in segs[1:]:
    total += s
  total.export(out_path, format="mp3", bitrate="192k")
  print(f"TTS (gTTS) saved to: {out_path}")

def synth_openai(text: str, out_path: str, model: str, voice: str):
  from openai import OpenAI
  from pydub import AudioSegment
  client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL"),
  )
  chunks = split_for_tts(text, 600)
  segs = []
  for ch in chunks:
    try:
      with client.audio.speech.with_streaming_response.create(
        model=model,
        voice=voice,
        input=ch,
        format="mp3",
      ) as response:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        response.stream_to_file(tmp.name)
        segs.append(AudioSegment.from_file(tmp.name))
        os.unlink(tmp.name)
    except Exception:
      resp = client.audio.speech.create(
        model=model,
        voice=voice,
        input=ch,
        format="mp3",
      )
      audio_bytes = None
      for attr in ("content", "read", "read_bytes"):
        if hasattr(resp, attr):
          v = getattr(resp, attr)
          audio_bytes = v if isinstance(v, (bytes, bytearray)) else v()
          break
      if audio_bytes is None:
        audio_bytes = bytes(resp) if hasattr(resp, "__bytes__") else None
      if audio_bytes is None:
        raise RuntimeError("OpenAI TTS: cannot extract audio bytes from response")
      tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
      with open(tmp.name, "wb") as f:
        f.write(audio_bytes)
      segs.append(AudioSegment.from_file(tmp.name))
      os.unlink(tmp.name)
  total = segs[0] if segs else AudioSegment.silent(duration=500)
  for s in segs[1:]:
    total += s
  total.export(out_path, format="mp3", bitrate="192k")
  print(f"TTS (OpenAI) saved to: {out_path}")

def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--input", required=True)
  ap.add_argument("--output", required=True)
  ap.add_argument("--provider", choices=["gtts", "openai"], default="gtts")
  ap.add_argument("--language", default="zh")
  ap.add_argument("--openai-model", default="gpt-4o-mini-tts")
  ap.add_argument("--openai-voice", default="alloy")
  args = ap.parse_args()

  text = read_text(args.input)
  if not text:
    text = "这是一个空白脚本的占位旁白。"

  if args.provider == "openai":
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("OPENAI_BASE_URL"):
      raise RuntimeError("OPENAI_API_KEY or OPENAI_BASE_URL is missing for OpenAI TTS.")
    synth_openai(text, args.output, args.openai_model, args.openai_voice)
  else:
    synth_gtts(text, args.output, args.language)

if __name__ == "__main__":
  main()
