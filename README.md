# Ubuntu Image Fetcher
A Python tool to download images from URLs, inspired by Ubuntu's philosophy: "I am because we are." It fetches images respectfully, handles errors gracefully, and organizes them for sharing.

## Features
- Fetches single or multiple image URLs
- Saves to `Fetched_Images` directory
- Checks for duplicates, non-images, and large files
- Handles HTTP errors gracefully

## Requirements
- Python 3.10+
- `requests` library (`pip install requests`)

## Setup
1. Clone this repo: `git clone https://github.com/yourusername/Ubuntu_Requests.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python ubuntu_image_fetcher.py`

## Usage
Enter comma-separated image URLs when prompted, e.g., `https://picsum.photos/200, https://picsum.photos/300`.

## License
MIT License
