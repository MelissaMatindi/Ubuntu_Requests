#!/usr/bin/env python3
"""
ubuntu_image_fetcher.py

Ubuntu-Inspired Image Fetcher
- Accepts multiple URLs (CLI or from a file or interactive input)
- Creates "Fetched_Images" directory (if missing)
- Streams images, checks HTTP headers (Content-Type & Content-Length)
- Prevents duplicate images using SHA256 content hash and index (index.json)
- Saves files safely with sanitized filenames and avoids overwrites
- Handles errors gracefully

Usage examples:
  python ubuntu_image_fetcher.py --urls https://example.com/a.jpg https://site.com/img.png
  python ubuntu_image_fetcher.py --file urls.txt
  python ubuntu_image_fetcher.py        # interactive mode
"""

import argparse
import hashlib
import json
import os
import re
import time
from urllib.parse import urlparse, unquote

import requests

# --------------- Config ---------------
OUTPUT_DIR = "Fetched_Images"
INDEX_FILENAME = "index.json"
MAX_BYTES = 10 * 1024 * 1024   # 10 MB safety limit (adjust as needed)
CHUNK_SIZE = 8192
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "image/bmp",
    "image/tiff",
}
USER_AGENT = "UbuntuImageFetcher/1.0 (+https://yourproject.example)"

# --------------- Helpers ---------------
def ensure_output_dir(path=OUTPUT_DIR):
    os.makedirs(path, exist_ok=True)
    return path

def sanitize_filename(name: str) -> str:
    """Return a safe filename by removing dangerous characters."""
    if not name:
        name = "downloaded_image"
    name = unquote(name)
    name = os.path.basename(name)
    # allow letters, numbers, dot, dash, underscore
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    # collapse multiple underscores
    name = re.sub(r"_+", "_", name)
    return name[:200]  # limit length

def load_index(index_path):
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}
    return {}

def save_index(index, index_path):
    with open(index_path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2)

def make_unique_path(directory, filename):
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    i = 1
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base}_{i}{ext}")
        i += 1
    return candidate

def ext_from_content_type(content_type):
    """Try to guess extension from Content-Type header."""
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
        "image/bmp": ".bmp",
        "image/tiff": ".tiff",
    }
    if not content_type:
        return ""
    ct = content_type.split(";")[0].strip().lower()
    return mapping.get(ct, "")

# --------------- Core download function ---------------
def download_image(url, out_dir, session, index, max_bytes=MAX_BYTES):
    """Downloads a single image, validates headers, prevents duplicates."""
    try:
        resp = session.get(url, stream=True, timeout=15, allow_redirects=True)
    except requests.RequestException as e:
        return False, f"Request error: {e}"

    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        return False, f"HTTP error: {e} (status {resp.status_code})"

    # 1) Check Content-Type
    content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if not content_type.startswith("image/") or content_type not in ALLOWED_IMAGE_TYPES:
        return False, f"Rejected: Content-Type '{content_type}' is not an allowed image type."

    # 2) Check Content-Length if present
    content_length = resp.headers.get("Content-Length")
    if content_length:
        try:
            if int(content_length) > max_bytes:
                return False, f"Rejected: Content-Length ({content_length} bytes) exceeds max allowed ({max_bytes})."
        except ValueError:
            pass  # ignore if header malformed

    # 3) Determine filename (Content-Disposition -> URL path -> generated)
    filename = None
    cd = resp.headers.get("Content-Disposition")
    if cd:
        # try to find filename in header
        m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd)
        if m:
            filename = sanitize_filename(m.group(1))

    if not filename:
        parsed = urlparse(url)
        filename = sanitize_filename(os.path.basename(parsed.path))

    # If no extension, infer from content-type
    if not os.path.splitext(filename)[1]:
        ext = ext_from_content_type(content_type)
        filename = filename + ext if ext else filename + ".img"

    # prepare temporary file path
    tmp_path = os.path.join(out_dir, filename + ".tmp")

    sha = hashlib.sha256()
    total = 0
    try:
        with open(tmp_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                if not chunk:
                    continue
                fh.write(chunk)
                sha.update(chunk)
                total += len(chunk)
                if total > max_bytes:
                    fh.close()
                    os.remove(tmp_path)
                    return False, f"Aborted: downloaded size exceeded {max_bytes} bytes."

    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False, f"Write error: {e}"

    digest = sha.hexdigest()

    # 4) Check duplicates using index (hash -> {filename, url})
    if digest in index:
        # remove temp file and report duplicate
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        existing = index[digest]
        return False, f"Duplicate: already downloaded as '{existing['filename']}' from {existing.get('url')}"

    # 5) Move temp file to final safe path (unique)
    final_path = make_unique_path(out_dir, filename)
    try:
        os.replace(tmp_path, final_path)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False, f"Failed to finalize file: {e}"

    # 6) Update index
    index[digest] = {
        "filename": os.path.basename(final_path),
        "url": url,
        "content_type": content_type,
        "size": total,
        "timestamp": int(time.time()),
    }

    return True, final_path

# --------------- CLI / Interactive Flow ---------------
def parse_args():
    p = argparse.ArgumentParser(description="Ubuntu Image Fetcher — fetch images safely")
    p.add_argument("--urls", nargs="+", help="One or more image URLs")
    p.add_argument("--file", help="Path to a text file containing image URLs (one per line)")
    p.add_argument("--out", default=OUTPUT_DIR, help=f"Output directory (default: {OUTPUT_DIR})")
    p.add_argument("--max", type=int, default=MAX_BYTES, help=f"Maximum bytes per file (default {MAX_BYTES})")
    p.add_argument("--delay", type=float, default=0.6, help="Seconds to wait between downloads (politeness)")
    p.add_argument("--no-index", action="store_true", help="Do not save or check the local index (not recommended)")
    return p.parse_args()

def gather_urls(args):
    urls = []
    if args.urls:
        urls.extend(args.urls)
    if args.file:
        if not os.path.exists(args.file):
            print(f"URL file not found: {args.file}")
        else:
            with open(args.file, "r", encoding="utf-8") as fh:
                for ln in fh:
                    ln = ln.strip()
                    if ln and not ln.startswith("#"):
                        urls.append(ln)
    if not urls:
        # interactive prompt
        print("Welcome to the Ubuntu Image Fetcher")
        print("Enter one or multiple image URLs (separated by commas), or provide a file with --file.\n")
        raw = input("Please enter image URL(s), or press Enter to quit: ").strip()
        if not raw:
            return []
        # split by comma or whitespace
        parts = re.split(r"[,\s]+", raw)
        urls.extend([p for p in parts if p])
    # de-duplicate and keep order
    seen = set()
    final = []
    for u in urls:
        if u not in seen:
            final.append(u)
            seen.add(u)
    return final

def main():
    args = parse_args()
    out_dir = ensure_output_dir(args.out)
    index_path = os.path.join(out_dir, INDEX_FILENAME)

    index = {} if args.no_index else load_index(index_path)

    urls = gather_urls(args)
    if not urls:
        print("No URLs provided — exiting.")
        return

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    print(f"\nFetching {len(urls)} URL(s) — saving into '{out_dir}'\n")
    success_count = 0
    skip_count = 0

    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{len(urls)}] {url}")
        ok, msg = download_image(url, out_dir, session, index, max_bytes=args.max)
        if ok:
            success_count += 1
            print(f"  ✓ Saved: {msg}")
        else:
            skip_count += 1
            print(f"  ✗ {msg}")
        # polite delay
        if i < len(urls):
            time.sleep(args.delay)

    if not args.no_index:
        save_index(index, index_path)

    print("\nSummary:")
    print(f"  Successfully saved: {success_count}")
    print(f"  Skipped/failed:      {skip_count}")
    print(f"\nImages are in the folder: {os.path.abspath(out_dir)}")
    print("Connection strengthened. Community enriched. 🌍\n")

if __name__ == "__main__":
    main()

