#!/usr/bin/env python3

import argparse
import base64
import os
import sys

from google import genai

IMAGE_MODEL = "gemini-3.1-flash-image"
IMAGE_PROMPT_FILE = "scripts/image-prompt.txt"


def load_api_key():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print("Error: GEMINI_API_KEY is not set.")
        sys.exit(1)
    return key


def load_image_prompt():
    if not os.path.exists(IMAGE_PROMPT_FILE):
        print(f"Error: Image prompt file not found: {IMAGE_PROMPT_FILE}")
        sys.exit(1)

    with open(IMAGE_PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def generate_image(
    title,
    slug,
    article_content,
    article_context="",
    filename="ai-image.jpeg",
):
    api_key = load_api_key()
    base_prompt = load_image_prompt()

    prompt = f"""{base_prompt}

ARTICLE TITLE:
{title}

ARTICLE CONTENT:
{article_content}
"""

    if article_context:
        prompt += f"""

ADDITIONAL ARTICLE CONTEXT:
{article_context}
"""

    prompt += """

Create exactly one realistic image that best represents the article.
Do not create an image collage.
Do not include text, logos, brand names, watermarks, fake labels,
or identifiable real people.
"""

    client = genai.Client(api_key=api_key)

    image_dir = os.path.join(
        "content",
        "posts",
        slug,
        "images",
    )
    os.makedirs(image_dir, exist_ok=True)

    image_path = os.path.join(image_dir, filename)

    print(f"Generating AI image: {filename}")

    interaction = client.interactions.create(
        model=IMAGE_MODEL,
        input=prompt,
        response_format={
            "type": "image",
            "mime_type": "image/jpeg",
            "aspect_ratio": "16:9",
            "image_size": "1K",
        },
    )

    if not interaction.output_image:
        raise RuntimeError("Gemini did not return an image.")

    image_data = base64.b64decode(
        interaction.output_image.data
    )

    with open(image_path, "wb") as f:
        f.write(image_data)

    print(f"Image written to: {image_path}")

    alt_prompt = f"""
Write a short, accurate alt text for the generated image.

Article title:
{title}

Article context:
{article_content[:3000]}

Return ONLY the alt text.
Do not use quotation marks.
Do not mention that the image is AI generated.
Do not invent specific brands, locations, people, or products.
"""

    alt_response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=alt_prompt,
    )

    alt_text = (alt_response.text or "").strip()

    if not alt_text:
        alt_text = title

    return alt_text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--article-content", required=True)
    parser.add_argument("--article-context", default="")
    parser.add_argument("--filename", default="ai-image.jpeg")

    args = parser.parse_args()

    generate_image(
        title=args.title,
        slug=args.slug,
        article_content=args.article_content,
        article_context=args.article_context,
        filename=args.filename,
    )


if __name__ == "__main__":
    main()