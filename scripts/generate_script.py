import os
import argparse
from datetime import datetime
from slugify import slugify

from openai import OpenAI

TEMPLATE = """---
title: "{title}"
model: "{model}"
audience: "{audience}"
duration_minutes: {duration}
created_at: "{created_at}"
---

# 标题
{title}

## 开场 Hook（3-7 秒）
- 用一句有冲击力的话点题
- 提出痛点/收益

## 大纲
{outline}

## 正文脚本（竖屏 9:16）
{script}

## 结尾 Call-to-Action
- 关注/收藏/评论引导
"""

SYSTEM = (
    "You are a professional short-video scriptwriter producing concise, high-retention 9:16 vertical scripts. "
    "Keep language vivid and practical for Chinese audiences. Output strictly in Markdown."
)

USER_PROMPT = """请为以下主题生成一个竖屏短视频脚本（9:16）：
- 主题: {topic}
- 目标受众: {audience}
- 目标时长: {duration} 分钟
- 风格: {style}

请包含：
1) 吸引人的开场 Hook
2) 3-5 个要点式大纲
3) 可直接口播的逐段正文（分镜可选）
4) 清晰的结尾 CTA

避免空话、冗长；给出具体事实、步骤或示例。"""

def to_bool(v):
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--audience", default="")
    parser.add_argument("--duration", default=1, type=float)
    parser.add_argument("--style", default="清晰、实用、节奏快")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--dry-run", dest="dry_run", default="false")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    if not api_key or not base_url:
        raise RuntimeError("Missing OPENAI_API_KEY or OPENAI_BASE_URL secrets.")

    client = OpenAI(api_key=api_key, base_url=base_url)

    user_text = USER_PROMPT.format(
        topic=args.topic,
        audience=args.audience or "泛用户",
        duration=args.duration,
        style=args.style,
    )

    resp = client.chat.completions.create(
        model=args.model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_text},
        ],
        temperature=0.7,
    )
    content = resp.choices[0].message.content

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    md = TEMPLATE.format(
        title=args.topic,
        model=args.model,
        audience=args.audience or "泛用户",
        duration=args.duration,
        created_at=now,
        outline="（由模型在正文中体现）",
        script=content.strip(),
    )

    out_dir = os.path.join("content", "scripts")
    os.makedirs(out_dir, exist_ok=True)
    filename = f"{slugify(args.topic)}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.md"
    out_path = os.path.join(out_dir, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"Script saved to: {out_path}")

    if to_bool(args.dry_run):
        print("Dry run enabled: PR step will be skipped by workflow condition.")


if __name__ == "__main__":
    main()