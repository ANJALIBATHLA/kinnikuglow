#!/usr/bin/env python3
"""
Reads the first unprocessed entry from queue/posts.yaml, generates a blog post
via Gemini, writes it to content/posts/, and marks the entry as created.

Usage:
    python scripts/generate_post.py                        # Generate next post
    python scripts/generate_post.py --set-branch BRANCH   # Record branch name

Environment variables:
    GEMINI_API_KEY  — required for generation
"""

import os
import re
import sys
import time
import datetime
import yaml
import google.generativeai as genai

QUEUE_FILE = "queue/posts.yaml"
AFFILIATES_FILE = "data/affiliates.yaml"
POSTS_DIR = "content/posts"
PROMPT_FILE = "scripts/post-prompt.txt"
POST_CLOSING = "\n\n---\n\n*Hope this helps. More honest blogs coming your way every week on KinnikuGlow.*\n"

QUEUE_HEADER = """\
# KinnikuGlow post queue
# Each entry needs at minimum a title.
# publish: "YYYY-MM-DD"  → PR auto-merges on that date
# Without a publish date  → add the 'ready' label on GitHub when you're done reviewing
# tags:                   → controls which nav sections the post appears in
#                            options: tokyo, fitness, skincare, meal-prep, beginners
# affiliates:             → keys from data/affiliates.yaml relevant to this post
# notes:                  → extra context fed to Gemini for that specific post
# images:                 → shared images to embed (upload files to static/images/shared/)
# status: created         → set automatically when a PR has been generated
# branch:                 → set automatically with the branch name used

"""


def load_api_key():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print("Error: GEMINI_API_KEY is not set.")
        sys.exit(1)
    return key


def load_affiliates():
    if not os.path.exists(AFFILIATES_FILE):
        return {}
    with open(AFFILIATES_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_affiliate_block(keys, all_affiliates):
    if not keys:
        return ""
    lines = ["Affiliate products for this post (add [AFFILIATE: key] immediately after each mention):"]
    for key in keys:
        affiliate = all_affiliates.get(key)
        if affiliate:
            lines.append(f"  {key} → {affiliate.get('name', key)}")
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def load_prompt():
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_queue():
    if not os.path.exists(QUEUE_FILE):
        print(f"Queue file not found: {QUEUE_FILE}")
        sys.exit(0)
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def write_queue(entries):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        f.write(QUEUE_HEADER)
        yaml.dump(entries, f, allow_unicode=True, sort_keys=False,
                  default_flow_style=False, indent=2)


def find_next_entry(entries):
    for i, entry in enumerate(entries):
        if entry.get("status") != "created":
            return i, entry
    return None, None


def mark_as_created(entries, index):
    entries[index]["status"] = "created"
    write_queue(entries)
    print(f"Marked '{entries[index]['title']}' as created.")


def set_branch_in_queue(branch):
    entries = load_queue()
    for entry in entries:
        if entry.get("status") == "created" and not entry.get("branch"):
            entry["branch"] = branch
            break
    write_queue(entries)
    print(f"Set branch: {branch}")


def slugify(title):
    slug = title.lower()
    slug = re.sub(r"[^\w\s]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug


def build_image_block(images):
    if not images:
        return ""
    lines = ["Images to embed — use the exact markdown format at the placement hint location:"]
    for img in images:
        file_path = img.get("file", "")
        alt = img.get("alt", "")
        placement = img.get("placement", "where relevant in the post")
        lines.append(f"  - ![{alt}]({file_path})  placement hint: {placement}")
    lines.append("For any other image spots, keep using: [IMAGE: description of what would go here]")
    return "\n".join(lines)


def replace_affiliate_placeholders(content):
    def replacer(match):
        key = match.group(1).strip()
        return f'{{{{< affiliate "{key}" >}}}}'
    return re.sub(r"\[AFFILIATE:\s*([^\]]+)\]", replacer, content)


def inject_tags(content, tags):
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content
    fm = yaml.safe_load(parts[1]) or {}
    fm["tags"] = tags
    new_fm = yaml.dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return f"---\n{new_fm}---{parts[2]}"


def generate_post(entry, api_key, system_prompt, all_affiliates):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=system_prompt,
    )

    title = entry.get("title", "")
    notes = (entry.get("notes") or "").strip()
    images = entry.get("images", []) or []
    affiliate_keys = entry.get("affiliates", []) or []
    today = datetime.date.today().isoformat()

    parts = [
        f"Write a blog post for KinnikuGlow with this title: {title}",
        f"Today's date: {today}",
    ]
    if notes:
        parts.append(f"Additional context for this post: {notes}")
    image_block = build_image_block(images)
    if image_block:
        parts.append(image_block)
    affiliate_block = build_affiliate_block(affiliate_keys, all_affiliates)
    if affiliate_block:
        parts.append(affiliate_block)

    prompt = "\n\n".join(parts)
    for attempt in range(1, 4):
        try:
            print(f"Calling Gemini for: {title} (attempt {attempt})")
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if attempt == 3:
                print(f"Gemini failed after 3 attempts: {e}")
                raise
            wait = 2 ** attempt
            print(f"Attempt {attempt} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)


def write_post(entry, content):
    title = entry.get("title", "")
    slug = slugify(title)
    post_dir = os.path.join(POSTS_DIR, slug)
    os.makedirs(post_dir, exist_ok=True)

    post_path = os.path.join(post_dir, "index.md")
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(content.rstrip() + POST_CLOSING)

    print(f"Post written to: {post_path}")
    return slug


def main():
    # Mode: record branch name after the fact
    if len(sys.argv) == 3 and sys.argv[1] == "--set-branch":
        set_branch_in_queue(sys.argv[2])
        return

    api_key = load_api_key()
    system_prompt = load_prompt()
    all_affiliates = load_affiliates()
    entries = load_queue()

    index, entry = find_next_entry(entries)
    if entry is None:
        print("Queue is empty. Nothing to generate.")
        sys.exit(0)

    title = entry.get("title", "")
    publish = str(entry.get("publish", "")).strip()

    print(f"Next title: {title}")

    raw_content = generate_post(entry, api_key, system_prompt, all_affiliates)
    content = replace_affiliate_placeholders(raw_content)

    tags = entry.get("tags") or []
    if tags:
        content = inject_tags(content, tags)

    slug = write_post(entry, content)
    mark_as_created(entries, index)

    print(f"slug={slug}")
    print(f"title={title}")
    print(f"publish={publish}")
    print("Done.")


if __name__ == "__main__":
    main()
