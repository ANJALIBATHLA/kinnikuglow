# KinnikuGlow

Fitness, meal prep and glow. Tokyo life for working women.

Live at [kinnikuglow.com](https://kinnikuglow.com)

---

## What this is

A lifestyle blog covering fitness, meal prep, skincare and daily life in Tokyo, written for working women living in or visiting the city. Built with Hugo and the PaperMod theme, hosted on GitHub Pages.

## How the blog works

Posts are written and reviewed as pull requests. A GitHub Action generates a draft post daily using Gemini, opens a PR, and auto-merges it either on a scheduled date or when manually marked ready.

**To queue a new post**, add an entry to `queue/posts.yaml`:

```yaml
- title: "Your Post Title"
  publish: "2026-09-01"
  tags: [fitness, tokyo]
  notes: "Any context or direction for the AI."
  images:
    - file: "/images/shared/your-image.jpg"
      alt: "Image description"
      placement: "after intro"
```

Tags control which nav sections the post appears in. Options: `tokyo`, `fitness`, `skincare`, `meal-prep`, `beginners`.

**To add shared images**, drop files into `static/images/shared/` and reference them in the queue entry above.

**To publish a generated post**, either add the `ready` label on the PR or set a `publish` date in the queue. The auto-merge workflow checks daily at 9am UTC.

## Local development

```bash
git submodule update --init --recursive
hugo server
```

Requires Hugo installed locally. Visit `http://localhost:1313` to preview.

## Deployment

Pushing to `main` triggers the deploy workflow which builds the site and pushes to the `gh-pages` branch. GitHub Pages serves the result at kinnikuglow.com.
