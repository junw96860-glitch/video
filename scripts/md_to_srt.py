#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import argparse
from datetime import timedelta

def strip_front_matter(md: str) -> str:
  lines = md.splitlines()
  if len(lines) >= 3 and lines[0].strip() == "---":
    for i in range(1, len(lines)):
      if lines[i].strip() == "---":
        return "\n".join(lines[i+1:])
  return md

def remove_markdown_controls(md: str) -> str:
  out = []
  for line in md.splitlines():
    s = line.strip()
    if not s:
      continue
    if s.startswith("#"):
      continue
    if s.startswith(">"):
      s = s.lstrip(">").strip()
    s = re.sub(r"^\s*[-*+]\s+", "", s)
    if s.startswith("```") or s.startswith("~~~"):
      continue
    s = re.sub(r"\s+", " ", s)
    if s:
      out.append(s)
  return "\n".join(out)

PUNCT = r"[。！？!?；;…]+"

def split_sentences(text: str) -> list[str]:
  parts = re.split(f"({PUNCT})", text)
  sentences, buf = [], ""
  for p in parts:
    if not p:
      continue
    if re.fullmatch(PUNCT, p):
      sentences.append((buf + p).strip())
      buf = ""
    else:
      buf += (" " if buf else "") + p.replace("\n", " ").strip()
  if buf.strip():
    sentences.append(buf.strip())
  return [s for s in sentences if len(s) >= 2]

def chunk_sentence(s: str, max_len: int = 18) -> list[str]:
  chunks, cur = [], ""
  for ch in s:
    cur += ch
    if len(cur) >= max_len:
      chunks.append(cur.strip())
      cur = ""
  if cur.strip():
    chunks.append(cur.strip())
  return chunks

def sec_to_timestamp(t: float) -> str:
  td = timedelta(seconds=max(0, t))
  h = int(td.total_seconds() // 3600)
  m = int((td.total_seconds() % 3600) // 60)
  s = int(td.total_seconds() % 60)
  ms = int((td.total_seconds() - int(td.total_seconds())) * 1000)
  return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def to_srt(chunks: list[str], cps: float, min_sec: float, max_sec: float) -> str:
  lines, t, idx = [], 0.0, 1
  for text in chunks:
    dur = max(min_sec, min(max_sec, len(text) / max(cps, 0.1)))
    lines.append(str(idx))
    lines.append(f"{sec_to_timestamp(t)} --> {sec_to_timestamp(t + dur)}")
    lines.append(text)
    lines.append("")
    t += dur
    idx += 1
  return "\n".join(lines).strip() + "\n"

def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--input", required=True)
  ap.add_argument("--output", required=True)
  ap.add_argument("--cps", type=float, default=4.0)
  ap.add_argument("--min-sec", type=float, default=1.2)
  ap.add_argument("--max-sec", type=float, default=5.0)
  ap.add_argument("--chunk", type=int, default=18)
  args = ap.parse_args()

  with open(args.input, "r", encoding="utf-8") as f:
    md = f.read()
  md = strip_front_matter(md)
  txt = remove_markdown_controls(md)
  sentences = split_sentences(txt)
  chunks = []
  for s in sentences:
    if len(s) <= args.chunk:
      chunks.append(s)
    else:
      chunks.extend(chunk_sentence(s, args.chunk))
  srt = to_srt(chunks, args.cps, args.min_sec, args.max_sec)
  with open(args.output, "w", encoding="utf-8") as f:
    f.write(srt)
  print(f"SRT saved to: {args.output}")

if __name__ == "__main__":
  main()
