#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shlex
import argparse
import subprocess
import tempfile
import requests
from pathlib import Path

def run(cmd: list[str]):
  print("+", " ".join(shlex.quote(x) for x in cmd))
  subprocess.run(cmd, check=True)

def ffprobe_duration(path: str) -> float:
  cmd = [
    "ffprobe", "-v", "error",
    "-show_entries", "format=duration",
    "-of", "default=nokey=1:noprint_wrappers=1",
    path
  ]
  out = subprocess.check_output(cmd).decode("utf-8", errors="ignore").strip()
  try:
    return float(out)
  except Exception:
    return 0.0

def ensure_dir(p: str):
  Path(p).mkdir(parents=True, exist_ok=True)

def parse_urls(csv: str) -> list[str]:
  if not csv:
    return []
  return [u.strip() for u in csv.split(",") if u.strip()]

def download_images(urls: list[str], out_dir: str) -> list[str]:
  ensure_dir(out_dir)
  paths = []
  for i, u in enumerate(urls, 1):
    ext = os.path.splitext(u.split("?")[0])[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
      ext = ".jpg"
    out = os.path.join(out_dir, f"img_{i:02d}{ext}")
    print(f"Downloading {u} -> {out}")
    r = requests.get(u, timeout=60)
    r.raise_for_status()
    with open(out, "wb") as f:
      f.write(r.content)
    paths.append(out)
  return paths

def list_local_images(images_dir: str) -> list[str]:
  if not images_dir:
    return []
  p = Path(images_dir)
  if not p.exists():
    return []
  files = []
  for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
    files += [str(x) for x in sorted(p.glob(ext))]
  return files

def make_segment_from_image(img: str, dur: float, out_path: str):
  vf = (
    "scale=w=1080:h=-2:force_original_aspect_ratio=decrease,"
    "pad=1080:1920:(1080-iw)/2:(1920-ih)/2,"
    "format=yuv420p"
  )
  run([
    "ffmpeg", "-y",
    "-loop", "1", "-i", img,
    "-t", f"{dur:.3f}",
    "-r", "30",
    "-vf", vf,
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    out_path
  ])

def concat_segments(seg_paths: list[str], out_path: str):
  with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
    for p in seg_paths:
      f.write(f"file '{os.path.abspath(p)}'\n")
    list_path = f.name
  try:
    run([
      "ffmpeg", "-y",
      "-f", "concat", "-safe", "0",
      "-i", list_path,
      "-r", "30",
      "-c:v", "libx264",
      "-pix_fmt", "yuv420p",
      out_path
    ])
  finally:
    os.unlink(list_path)

def make_solid_bg(duration: float, out_path: str):
  run([
    "ffmpeg", "-y",
    "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30",
    "-t", f"{duration:.3f}",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    out_path
  ])

def merge_audio(video_in: str, narration_mp3: str, out_path: str, bgm_path: str | None):
  if bgm_path and Path(bgm_path).exists():
    run([
      "ffmpeg", "-y",
      "-i", video_in, "-i", narration_mp3, "-i", bgm_path,
      "-filter_complex", "[2:a]volume=0.15[bg];[1:a][bg]amix=inputs=2:duration=shortest:dropout_transition=2[aout]",
      "-map", "0:v:0", "-map", "[aout]",
      "-shortest",
      "-c:v", "libx264",
      "-c:a", "aac", "-b:a", "192k",
      out_path
    ])
  else:
    run([
      "ffmpeg", "-y",
      "-i", video_in, "-i", narration_mp3,
      "-map", "0:v:0", "-map", "1:a:0",
      "-shortest",
      "-c:v", "libx264",
      "-c:a", "aac", "-b:a", "192k",
      out_path
    ])

def burn_subs(video_in: str, srt_path: str, out_path: str):
  style = "Fontsize=40,Outline=2,Shadow=0,PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&"
  vf = f"subtitles={shlex.quote(os.path.abspath(srt_path))}:force_style='{style}'"
  run([
    "ffmpeg", "-y",
    "-i", video_in,
    "-vf", vf,
    "-c:v", "libx264",
    "-c:a", "copy",
    out_path
  ])

def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--audio", required=True, help="Narration audio (mp3)")
  ap.add_argument("--srt", required=True, help="Subtitle file (srt)")
  ap.add_argument("--output", required=True, help="Final mp4 path")
  ap.add_argument("--image-urls", default="", help="Comma-separated image URLs")
  ap.add_argument("--images-dir", default="", help="Local images directory")
  ap.add_argument("--burn-subtitles", default="true", help="true/false")
  ap.add_argument("--bgm-url", default="", help="Optional background music URL")
  args = ap.parse_args()

  ensure_dir(os.path.dirname(args.output) or ".")
  audio_dur = ffprobe_duration(args.audio)
  print(f"Audio duration: {audio_dur:.3f}s")

  urls = parse_urls(args.image_urls)
  img_paths = []
  workdir = tempfile.mkdtemp(prefix="imgs_")
  if urls:
    img_paths = download_images(urls, workdir)
  else:
    img_paths = list_local_images(args.images_dir)

  segments = []
  base_video = os.path.join(workdir, "base.mp4")

  if img_paths:
    seg_dur = max(2.0, audio_dur / max(1, len(img_paths)))
    for i, img in enumerate(img_paths, 1):
      seg = os.path.join(workdir, f"seg_{i:02d}.mp4")
      make_segment_from_image(img, seg_dur, seg)
      segments.append(seg)
    concat_segments(segments, base_video)
  else:
    make_solid_bg(audio_dur, base_video)

  bgm_path = ""
  if args.bgm_url.strip():
    try:
      r = requests.get(args.bgm_url.strip(), timeout=60)
      r.raise_for_status()
      bgm_path = os.path.join(workdir, "bgm.mp3")
      with open(bgm_path, "wb") as f:
        f.write(r.content)
      print(f"Downloaded BGM to {bgm_path}")
    except Exception as e:
      print(f"Warn: failed to download BGM: {e}")

  merged = os.path.join(workdir, "merged.mp4")
  merge_audio(base_video, args.audio, merged, bgm_path if bgm_path else None)

  burn = str(args.burn_subtitles).strip().lower() in ("1","true","yes","y","on")
  if burn:
    burn_subs(merged, args.srt, args.output)
  else:
    run([
      "ffmpeg", "-y",
      "-i", merged,
      "-c:v", "copy", "-c:a", "copy",
      args.output
    ])

  print(f"Final video saved to: {args.output}")

if __name__ == "__main__":
  main()
