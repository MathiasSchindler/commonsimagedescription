# Wikimedia Commons Image Analyzer

A minimal web application for extracting EXIF metadata from images and generating MediaWiki templates to assist with Wikimedia Commons uploads. Built during **[GLAM Wiki 2025 Hackathon](https://meta.wikimedia.org/wiki/GLAM_Wiki_2025/Hackathon)** in Lisbon, Portugal (October 30 - November 1, 2025).

## The Problem

Currently, uploading images to Wikimedia Commons requires manual entry of metadata, descriptions, and formatting:

![Current Wikimedia Commons upload interface](wikimedia%20commons%20upload%20now.png)

## Our Solution

This tool automatically extracts EXIF data, analyzes images with AI, and generates ready-to-use MediaWiki templates with multi-language descriptions:

![Demo interface with automated suggestions](demo%20image%20annotation.png)

## Features

- 📤 **Drag & drop image upload** - Instant file handling with visual feedback
- 📋 **EXIF metadata extraction** - Complete camera and technical data
- 📍 **GPS location analysis** - Reverse geocoding via OpenStreetMap Nominatim API
- 🧭 **Camera direction** - Extracts and displays compass heading from EXIF
- 🏛️ **Nearby POI detection** - Identifies points of interest around photo location via OSM
- 🌐 **Wikidata integration** - Queries nearby notable places via SPARQL to improve AI recognition
- 🤖 **AI vision analysis** - Context-aware image description using Qwen3-VL vision model
- 🌍 **Multi-language support** - Automatic translation to German, Portuguese, and Hebrew
- ✏️ **Editable descriptions** - Click-to-edit interface with automatic re-translation
- 📝 **Smart filename suggestions** - AI-generated filenames based on image content
- 📝 **MediaWiki template generation** - Ready-to-use Commons upload syntax
- ⚡ **Progressive loading** - Shows metadata instantly while AI processes in background
- 🎨 **Clean, responsive UI** - Split-screen layout with live preview

## Requirements

- Python 3.11+ (Python 3.13 recommended)
- Pillow (PIL)
- SPARQLWrapper (for Wikidata queries)
- Ollama running locally with models:
  - `qwen3-vl:8b` (vision analysis)
  - `gemma3:12b-it-qat` (translation and filename generation)

## Installation

1. Install Python dependencies:

```bash
pip install Pillow SPARQLWrapper
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
   - **Suggested Filename** - AI-generated filename based on image content
   - **AI Vision Analysis** - Context-aware image description with location integration
   - **Date & Time** - From EXIF data
   - **Camera Location** - Where the photo was taken (GPS coordinates, address)
   - **Camera Direction** - Compass heading the camera was facing
   - **Nearby Points of Interest** - Places around the camera location (OSM)
   - **Camera Information** - Make, model, lens details
   - **Technical Details** - ISO, exposure, focal length, dimensions
   - **Wikidata Places (Debug)** - Nearby notable places from Wikidata SPARQL query
   - **MediaWiki Template** - Ready-to-paste Commons syntax with multi-language descriptions

5. Edit descriptions by clicking on highlighted text in the MediaWiki template

6. Copy the generated MediaWiki template for Commons upload

## How It Works

### Progressive Loading Architecture

1. **Initial Upload** (1-2 seconds)
   - Extracts EXIF metadata
   - Performs reverse geocoding (OpenStreetMap Nominatim)
   - Searches for nearby POIs (OpenStreetMap)
   - Displays all metadata immediately

2. **Wikidata Query** (1-2 seconds)
   - Queries Wikidata SPARQL endpoint for nearby notable places
   - Gets structured data about landmarks, buildings, monuments within 1km
   - Passes top 10 results to vision model for context

3. **Background AI Analysis** (10-30 seconds)
   - Sends image to Qwen3-VL with Wikidata context for accurate identification
   - Generates integrated description including location and identified structures
   - Translates description to German, Portuguese, and Hebrew using Gemma3
   - Generates smart filename suggestion
   - Updates MediaWiki template progressively

### API Integrations

- **OpenStreetMap Nominatim** - Reverse geocoding and POI search
- **Wikidata SPARQL** - Structured queries for nearby notable places
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
|description={{en|1=A Ryanair airplane parked at Terminal 2 of Berlin Brandenburg Airport in Schönefeld, Germany}}
{{de|1=Ein Ryanair-Flugzeug steht am Terminal 2 des Flughafens Berlin Brandenburg in Schönefeld, Deutschland}}
{{pt|1=Um avião da Ryanair estacionado no Terminal 2 do Aeroporto de Berlim Brandemburgo em Schönefeld, Alemanha}}
{{he|1=מטוס ריינאייר חונה בטרמינל 2 של נמל התעופה ברלין ברנדנבורג בשנפלד, גרמניה}}
|date=2025-10-29 12:54:31
|source={{own}}
|author=
|permission=
|other versions=
}}{{Location|52.36522222|13.50316667|heading:315.0}}

=={{int:license-header}}==
{{CC0}}

[[Category:Uploaded via Commons Image Analyzer]]
[[Category:Germany]]
[[Category:Schönefeld]]
```

## Technical Notes

- **No external dependencies** - Only stdlib + Pillow + SPARQLWrapper for Python
- **Local AI processing** - All models run via Ollama locally, no cloud APIs
- **Minimal web server** - Uses Python's built-in `http.server`
- **No database** - Stateless request/response architecture
- **Privacy-first** - Images and processing stay on your machine
- **Context-aware AI** - Wikidata integration helps identify specific landmarks and structures

## API Endpoints

- `GET /` - Serves the web interface
- `POST /upload` - Processes image upload, returns EXIF and location data
- `POST /upload/vision` - Analyzes image with vision model and Wikidata context (async)
- `POST /translate` - Translates text to target language (async)
- `POST /wikidata-pois` - Queries Wikidata SPARQL for nearby places
- `POST /suggest-filename` - Generates smart filename suggestion based on image content

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
- Category suggestions based on image content and Wikidata classifications
- Direct Wikidata entity linking for locations and landmarks in template
- Batch processing for multiple images
- Custom prompt templates
- Export formats (JSON, XML)
- Integration with Wikimedia Commons upload API

## Known Limitations

- This is a demonstration project for the hackathon, not production-ready
- OpenStreetMap Nominatim has usage limits (respect their policies)
- Wikidata SPARQL endpoint has rate limits and query timeouts
- Vision model accuracy depends on image quality and Wikidata coverage of the area
- Translations are literal and may need human review
- LLM-generated filenames occasionally include special tokens (filtered out)
- Click-to-edit feature requires JavaScript enabled

## Credits

Created for **[GLAM Wiki 2025 Hackathon](https://meta.wikimedia.org/wiki/GLAM_Wiki_2025/Hackathon)** in Lisbon, Portugal (October 30 - November 1, 2025)

- **AI Assistance**: The vast majority of this code was generated by **Claude Sonnet 4.5** via GitHub Copilot in VS Code
- OpenStreetMap contributors for location data
- Wikidata and its contributors for structured place data
- Ollama for local LLM infrastructure
- Qwen team for vision model
- Google for Gemma translation model

## License

**CC0 (Public Domain)** - The source code is released under CC0. You can copy, modify, distribute and perform the work, even for commercial purposes, all without asking permission.

Created for [GLAM Wiki 2025 Hackathon](https://meta.wikimedia.org/wiki/GLAM_Wiki_2025/Hackathon) in Lisbon, Portugal
