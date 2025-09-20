# Ubuntu Image Fetcher
A Python tool to download images from URLs, inspired by Ubuntu's philosophy: "I am because we are." It fetches images respectfully, handles errors gracefully, and organizes them for sharing.

## Features

- Accepts one or many image URLs (CLI, file, or interactive input)
- Validates HTTP headers and prevents dangerous downloads
- Streams images and saves them to `Fetched_Images/`
- Prevents duplicates by hashing content (SHA-256) and storing an index
- Handles errors gracefully — no crashes, clear messages

---

## Requirements
- Python 3.10+
- `requests` library (`pip install requests`)

## Setup
1. Clone this repo: `git clone https://github.com/MelissaMatindi/Ubuntu_Requests.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python ubuntu_image_fetcher.py`

## Usage
Enter comma-separated image URLs when prompted, e.g. `https://picsum.photos/200, https://picsum.photos/300`.

## License
MIT License




