#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import argparse

def strip_front_matter(md: str) -> str:
  lines = md.splitlines()
  if len(lines) >= 3 and lines[0].strip() == "---":
    for i in range(1, len(lines)):
      if lines[i].strip() == "---":
        return "\n".join(lines[i+1:])
  return md

def md_to_text(md: str) -> str:
  out = []
  in_code = False
  for line in md.splitlines():
    s = line.rstrip()
    if s.strip().startswith("```") or s.strip().startswith("~~~"):
      in_code = not in_code
      continue
    if in_code:
      continue
    if s.strip().startswith("#"):
      title = s.strip("#").strip()
      if title:
        out.append(title)
      continue
    s = re.sub(r"^\s*[-*+]\s+", "", s)
    s = s.replace("·", "•")
    s = s.strip()
    if s:
      out.append(s)
  text = " ".join(out)
  text = re.sub(r"\s+", " ", text).strip()
  return text

def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--input", required=True)
  ap.add_argument("--output", required=True)
  args = ap.parse_args()
  with open(args.input, "r", encoding="utf-8") as f:
    md = f.read()
  md = strip_front_matter(md)
  txt = md_to_text(md)
  with open(args.output, "w", encoding="utf-8") as f:
    f.write(txt)
  print(f"Narration text saved to: {args.output}")

if __name__ == "__main__":
  main()
