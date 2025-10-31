# Wikimedia Commons Image Analyzer

A minimal web application for extracting EXIF metadata from images and generating MediaWiki templates to assist with Wikimedia Commons uploads. Built during Wikimedia Hackathon Portugal 2025.

## Features

- 📤 **Drag & drop image upload** - Instant file handling with visual feedback
- 📋 **EXIF metadata extraction** - Complete camera and technical data
- 📍 **GPS location analysis** - Reverse geocoding via OpenStreetMap Nominatim API
- 🧭 **Camera direction** - Extracts and displays compass heading from EXIF
- 🏛️ **Nearby POI detection** - Identifies points of interest around photo location
- 🤖 **AI vision analysis** - Image description using Qwen3-VL vision model
- 🌍 **Multi-language support** - Automatic translation to German and Portuguese
- 📝 **MediaWiki template generation** - Ready-to-use Commons upload syntax
- ⚡ **Progressive loading** - Shows metadata instantly while AI processes in background
- 🎨 **Clean, responsive UI** - Split-screen layout with live preview

## Requirements

- Python 3.11+ (Python 3.13 recommended)
- Pillow (PIL)
- Ollama running locally with models:
  - `qwen3-vl:8b` (vision analysis)
  - `gemma3:12b-it-qat` (translation)

## Installation

1. Install Python dependencies:

```bash
pip install Pillow
```

2. Install and start Ollama:

```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama service
ollama serve
```

3. Download required models:

```bash
# Vision model for image analysis
ollama pull qwen3-vl:8b

# Translation model for multi-language support
ollama pull gemma3:12b-it-qat
```

## Usage

1. Start the server:

```bash
python3 server.py
```

2. Open your browser to: http://localhost:8000/

3. Drag and drop an image or click to upload

4. View comprehensive analysis:
   - **AI Vision Analysis** - Automated image description
   - **Date & Time** - From EXIF data
   - **Camera Location** - Where the photo was taken (GPS coordinates, address)
   - **Camera Direction** - Compass heading the camera was facing
   - **Nearby Points of Interest** - Places around the camera location
   - **Camera Information** - Make, model, lens details
   - **Technical Details** - ISO, exposure, focal length, dimensions
   - **MediaWiki Template** - Ready-to-paste Commons syntax with multi-language descriptions

5. Copy the generated MediaWiki template for Commons upload

## How It Works

### Progressive Loading Architecture

1. **Initial Upload** (1-2 seconds)
   - Extracts EXIF metadata
   - Performs reverse geocoding (OpenStreetMap Nominatim)
   - Searches for nearby POIs
   - Displays all metadata immediately

2. **Background AI Analysis** (10-30 seconds)
   - Sends image to Qwen3-VL for visual description
   - Translates description to German using Gemma3
   - Translates description to Portuguese using Gemma3
   - Updates MediaWiki template progressively

### API Integrations

- **OpenStreetMap Nominatim** - Reverse geocoding and POI search
- **Ollama Local API** - Vision analysis and translations (no cloud services)

## Project Structure

```
.
├── server.py          # Python HTTP server with EXIF, vision, and translation
├── index.html         # Main HTML page with split-screen layout
├── style.css          # Responsive styles
├── script.js          # Client-side JavaScript with progressive loading
├── uploads/           # Uploaded images (auto-created)
└── README.md          # This file
```

## Generated MediaWiki Template Example

```wiki
=={{int:filedesc}}==
{{Information
|description={{en|1=A red squirrel eating a nut in a park (taken in Lisboa, Portugal, facing Southwest)}}
{{de|1=Ein rotes Eichhörnchen, das eine Nuss in einem Park isst (taken in Lisboa, Portugal, facing Southwest)}}
{{pt|1=Um esquilo vermelho comendo uma noz em um parque (taken in Lisboa, Portugal, facing Southwest)}}
|date=2024-11-17 09:03:00
|source={{own}}
|author=
|permission=
|other versions=
}}{{Location|38.74808889|-9.14888333|heading:225.0}}

=={{int:license-header}}==
{{CC0}}

[[Category:Uploaded via Commons Image Analyzer]]
[[Category:Portugal]]
[[Category:Lisboa]]
```

## Technical Notes

- **No external dependencies** - Only stdlib + Pillow for Python
- **Local AI processing** - All models run via Ollama locally, no cloud APIs
- **Minimal web server** - Uses Python's built-in `http.server`
- **No database** - Stateless request/response architecture
- **Privacy-first** - Images and processing stay on your machine

## API Endpoints

- `GET /` - Serves the web interface
- `POST /upload` - Processes image upload, returns EXIF and location data
- `POST /upload/vision` - Analyzes image with vision model (async)
- `POST /translate` - Translates text to target language (async)

## Configuration

Edit `server.py` to customize:

```python
PORT = 8000  # Server port
OLLAMA_API_URL = "http://localhost:11434/api/chat"  # Ollama API endpoint
OLLAMA_MODEL = "qwen3-vl:8b"  # Vision model
OLLAMA_TRANSLATION_MODEL = "gemma3:12b-it-qat"  # Translation model
```

## Future Enhancements

- Additional language support (Spanish, French, Italian)
- Category suggestions based on image content
- Wikidata entity linking for locations and landmarks
- Batch processing for multiple images
- Custom prompt templates
- Export formats (JSON, XML)

## Known Limitations

- This is a demonstration project for the hackathon, not production-ready
- OpenStreetMap Nominatim has usage limits (respect their policies)
- Vision model accuracy depends on image quality and subject matter
- Translations are literal and may need human review
- Camera location ≠ subject location (distinction made in output)

## Credits

Created for **Wikimedia Hackathon Portugal 2025**

- OpenStreetMap contributors for location data
- Ollama for local LLM infrastructure
- Qwen team for vision model
- Google for Gemma translation model

## License

Created for Wikimedia Hackathon Portugal 2025 - Demonstration purposes
