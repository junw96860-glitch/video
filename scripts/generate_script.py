import argparse
import datetime as dt
import os
import pathlib
from typing import List

import yaml
from slugify import slugify

try:
    # OpenAI SDK v1.x
    from openai import OpenAI
except ImportError:
    raise SystemExit("Missing dependency. Run: pip install -r requirements.txt")

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content" / "scripts"
PROMPT_PATH = ROOT / "prompts" / "script_prompt.md"

def load_prompt_template() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()

def build_prompt(language: str,
                 topic: str,
                 target_audience: str,
                 duration_minutes: int,
                 style: str,
                 aspect_ratio: str,
                 references: List[str]) -> str:
    tmpl = load_prompt_template()
    refs = "\n".join(f"- {r.strip()}" for r in references if r.strip())
    return tmpl.format(
        language=language,
        topic=topic,
        target_audience=target_audience,
        duration_minutes=duration_minutes,
        style=style,
        aspect_ratio=aspect_ratio,
        references_block=refs if refs else "- （无）",
    )

def call_openai(model: str, system_prompt: str, user_prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set. Add it in repo Settings > Secrets and variables > Actions.")

    client_kwargs = {}
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        client_kwargs["base_url"] = base_url
    org_id = os.getenv("OPENAI_ORG_ID")
    if org_id:
        client_kwargs["organization"] = org_id

    client = OpenAI(**client_kwargs)

    resp = client.chat.completions.create(
        model=model,
        temperature=0.7,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content.strip()

def ensure_dirs():
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)

def make_front_matter(topic, target_audience, duration_minutes, style, language, model, aspect_ratio, references):
    data = {
        "title": topic,
        "date": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "topic": topic,
        "audience": target_audience,
        "duration_minutes": int(duration_minutes),
        "style": style,
        "language": language,
        "model": model,
        "aspect_ratio": aspect_ratio,
        "references": [r for r in references if r.strip()],
    }
    return "---\n" + yaml.safe_dump(data, allow_unicode=True, sort_keys=False).strip() + "\n---\n\n"

def write_markdown(topic: str, fm: str, body_md: str) -> pathlib.Path:
    slug = slugify(topic)[:80] or "video-script"
    today = dt.datetime.utcnow().strftime("%Y-%m-%d")
    path = CONTENT_DIR / f"{today}-{slug}.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(fm)
        f.write(body_md.strip() + "\n")
    return path

def main():
    parser = argparse.ArgumentParser(description="Generate vertical (9:16) video script via LLM")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--target_audience", default="普通观众")
    parser.add_argument("--duration_minutes", type=int, default=5)
    parser.add_argument("--style", default="讲解")
    parser.add_argument("--language", default="zh", choices=["zh", "en"])
    parser.add_argument("--aspect_ratio", default="9:16")
    parser.add_argument("--references", default="")
    parser.add_argument("--model", default="gpt-4o-mini")
    args = parser.parse_args()

    ensure_dirs()

    refs = [line for line in args.references.splitlines() if line.strip()]

    system_prompt = (
        "You are an expert video scriptwriter and content strategist. "
        "Produce clear, structured, production-ready scripts with visual direction, beats, and timings."
        if args.language == "en" else
        "你是一名资深视频编导与文案，擅长为不同受众与平台生成清晰、结构化、可拍摄的视频脚本，包含画面与节奏指引。"
    )
    user_prompt = build_prompt(
        language=args.language,
        topic=args.topic,
        target_audience=args.target_audience,
        duration_minutes=args.duration_minutes,
        style=args.style,
        aspect_ratio=args.aspect_ratio,
        references=refs,
    )

    try:
        content_md = call_openai(args.model, system_prompt, user_prompt)
    except Exception as e:
        raise SystemExit(f"LLM 调用失败: {e}")

    front_matter = make_front_matter(
        topic=args.topic,
        target_audience=args.target_audience,
        duration_minutes=args.duration_minutes,
        style=args.style,
        language=args.language,
        model=args.model,
        aspect_ratio=args.aspect_ratio,
        references=refs,
    )

    out_path = write_markdown(args.topic, front_matter, content_md)
    print(f"Script saved to: {out_path}")

if __name__ == "__main__":
    main()