#!/usr/bin/env python3
"""
Minimal web server for image upload and EXIF extraction.
Wikimedia Commons image description hackathon project.
"""

import http.server
import socketserver
import json
import os
from io import BytesIO
from datetime import datetime
import urllib.request
import urllib.error
import base64

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow")
    exit(1)

try:
    from SPARQLWrapper import SPARQLWrapper, JSON as SPARQL_JSON
    SPARQL_AVAILABLE = True
except ImportError:
    print("Warning: SPARQLWrapper not installed. Wikidata POI search will be unavailable.")
    print("Install with: pip install sparqlwrapper")
    SPARQL_AVAILABLE = False

PORT = 8000
UPLOAD_DIR = "uploads"
OLLAMA_API_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3-vl:8b"
OLLAMA_TRANSLATION_MODEL = "gemma3:12b-it-qat"

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)


def extract_exif_data(image_path):
    """Extract EXIF data from an image file."""
    try:
        image = Image.open(image_path)
        exif_data = {}
        
        # Get basic EXIF data
        exifdata = image.getexif()
        
        if exifdata is not None:
            for tag_id, value in exifdata.items():
                tag = TAGS.get(tag_id, tag_id)
                
                # Convert bytes to string
                if isinstance(value, bytes):
                    try:
                        value = value.decode()
                    except:
                        value = str(value)
                
                exif_data[tag] = value
            
            # Extract GPS data if available
            gps_info = exifdata.get_ifd(0x8825)
            if gps_info:
                gps_data = {}
                for tag_id, value in gps_info.items():
                    tag = GPSTAGS.get(tag_id, tag_id)
                    gps_data[tag] = value
                
                # Parse GPS coordinates
                if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                    lat = convert_to_degrees(gps_data['GPSLatitude'])
                    lon = convert_to_degrees(gps_data['GPSLongitude'])
                    
                    # Apply reference (N/S, E/W)
                    if gps_data.get('GPSLatitudeRef') == 'S':
                        lat = -lat
                    if gps_data.get('GPSLongitudeRef') == 'W':
                        lon = -lon
                    
                    exif_data['GPSLatitude'] = lat
                    exif_data['GPSLongitude'] = lon
                
                exif_data['GPSData'] = gps_data
        
        return exif_data
    
    except Exception as e:
        return {"error": str(e)}


def convert_to_degrees(value):
    """Convert GPS coordinates to degrees in float format."""
    d, m, s = value
    return float(d) + (float(m) / 60.0) + (float(s) / 3600.0)


def reverse_geocode(lat, lon):
    """Query OpenStreetMap Nominatim API for reverse geocoding."""
    # Use more detailed parameters for better address breakdown
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1&extratags=1&namedetails=1&zoom=18"
    
    print(f"=== REVERSE GEOCODING REQUEST ===")
    print(f"URL: {url}")
    print(f"Coordinates: lat={lat}, lon={lon}")
    
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'WikimediaCommonsImageAnalyzer/1.0 (Hackathon Project)'
        })
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            print(f"=== REVERSE GEOCODING RESPONSE ===")
            print(json.dumps(data, indent=2))
            
            result = {
                'api_url': url,
                'api_response': data,
                'data': data  # Return the full response as data
            }
            
            return result
        
    except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
        error_msg = str(e)
        print(f"=== REVERSE GEOCODING ERROR ===")
        print(f"Error: {error_msg}")
        return {
            'api_url': url,
            'api_response': {'error': error_msg},
            'data': None
        }


def search_nearby_poi(lat, lon, direction=None):
    """Search for nearby points of interest using Nominatim."""
    # Search for nearby POIs using a simple query with coordinates
    # Create a radius search (approx 100m)
    url = (f"https://nominatim.openstreetmap.org/search?"
           f"format=json&"
           f"q=&"
           f"lat={lat}&"
           f"lon={lon}&"
           f"addressdetails=1&"
           f"extratags=1&"
           f"limit=20")
    
    print(f"=== POI SEARCH REQUEST ===")
    print(f"URL: {url}")
    print(f"Center: lat={lat}, lon={lon}")
    if direction is not None:
        print(f"Camera direction: {direction}°")
    
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'WikimediaCommonsImageAnalyzer/1.0 (Hackathon Project)'
        })
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            print(f"=== POI SEARCH RESPONSE ===")
            print(f"Found {len(data) if isinstance(data, list) else 0} results")
            if isinstance(data, list) and len(data) > 0:
                print(json.dumps(data[:3], indent=2))  # Print first 3 for brevity
            
            pois = []
            if isinstance(data, list):
                for item in data[:15]:  # Limit to 15 POIs
                    display_name = item.get('display_name', '')
                    name = item.get('name', '')
                    
                    # Skip if it's the exact same location (within 10m)
                    item_lat = float(item.get('lat', 0))
                    item_lon = float(item.get('lon', 0))
                    distance = ((lat - item_lat)**2 + (lon - item_lon)**2)**0.5 * 111000  # Rough meters
                    
                    if distance > 10 and name:  # Only include if >10m away and has a name
                        pois.append({
                            'name': name,
                            'type': item.get('type'),
                            'category': item.get('category'),
                            'class': item.get('class'),
                            'display_name': display_name,
                            'distance': round(distance, 1),
                            'lat': item_lat,
                            'lon': item_lon
                        })
            
            return {
                'pois': pois,
                'api_url': url,
                'api_response': data if isinstance(data, list) else {'error': 'Invalid response format'}
            }
        
    except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
        error_msg = str(e)
        print(f"=== POI SEARCH ERROR ===")
        print(f"Error: {error_msg}")
        return {
            'pois': [],
            'api_url': url,
            'api_response': {'error': error_msg}
        }


def query_wikidata_pois(lat, lon, radius_km=1):
    """Query Wikidata for nearby points of interest using SPARQL."""
    if not SPARQL_AVAILABLE:
        return {
            'places': [],
            'error': 'SPARQLWrapper not installed',
            'query': None,
            'raw_response': None
        }
    
    endpoint_url = "https://query.wikidata.org/sparql"
    
    # Build SPARQL query with coordinates
    # Note: Wikidata uses Point(Longitude Latitude) format
    query = f"""SELECT ?place ?location ?distance ?placeLabel ?placeDescription ?instanceOfLabel WHERE {{
    SERVICE wikibase:around {{
      ?place wdt:P625 ?location .
      bd:serviceParam wikibase:center "Point({lon} {lat})"^^geo:wktLiteral .
      bd:serviceParam wikibase:radius "{radius_km}" .
      bd:serviceParam wikibase:distance ?distance .
    }}
    OPTIONAL {{ ?place wdt:P31 ?instanceOf . }}
    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],mul,en". }}
}} ORDER BY ?distance LIMIT 100"""
    
    print(f"=== WIKIDATA SPARQL QUERY ===")
    print(f"Endpoint: {endpoint_url}")
    print(f"Coordinates: lat={lat}, lon={lon}, radius={radius_km}km")
    print(f"Query:\n{query}")
    
    try:
        import sys
        user_agent = f"WikimediaCommonsImageAnalyzer/1.0 Python/{sys.version_info[0]}.{sys.version_info[1]}"
        sparql = SPARQLWrapper(endpoint_url, agent=user_agent)
        sparql.setQuery(query)
        sparql.setReturnFormat(SPARQL_JSON)
        
        results = sparql.query().convert()
        
        print(f"=== WIKIDATA RESPONSE ===")
        print(f"Found {len(results.get('results', {}).get('bindings', []))} results")
        
        places = []
        for result in results.get("results", {}).get("bindings", []):
            place_uri = result.get("place", {}).get("value", "")
            place_label = result.get("placeLabel", {}).get("value", "Unknown")
            place_desc = result.get("placeDescription", {}).get("value", "")
            instance_of = result.get("instanceOfLabel", {}).get("value", "")
            distance = float(result.get("distance", {}).get("value", 0))
            
            # Extract Wikidata ID from URI (e.g., http://www.wikidata.org/entity/Q123 -> Q123)
            wikidata_id = place_uri.split('/')[-1] if place_uri else ""
            
            places.append({
                'label': place_label,
                'description': place_desc,
                'instance_of': instance_of,
                'distance_km': round(distance, 3),
                'distance_m': round(distance * 1000, 1),
                'wikidata_id': wikidata_id,
                'wikidata_url': f"https://www.wikidata.org/wiki/{wikidata_id}" if wikidata_id else ""
            })
        
        print(f"Parsed {len(places)} places")
        if places:
            print(f"First 3 places: {json.dumps(places[:3], indent=2)}")
        
        return {
            'places': places,
            'query': query,
            'raw_response': results,
            'error': None
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"=== WIKIDATA QUERY ERROR ===")
        print(f"Error: {error_msg}")
        return {
            'places': [],
            'query': query,
            'raw_response': None,
            'error': error_msg
        }


def analyze_image_with_ollama(image_path, exif_data, location_data, wikidata_places=None):
    """Analyze image using Ollama vision model."""
    print(f"=== OLLAMA VISION ANALYSIS ===")
    
    try:
        # Read and encode image to base64
        with open(image_path, 'rb') as img_file:
            image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        
        # Build context from EXIF and location data
        location_context = ""
        
        # Add location context
        if location_data and location_data.get('data'):
            loc = location_data['data']
            addr = loc.get('address', {})
            
            location_parts = []
            if addr.get('city') or addr.get('town') or addr.get('village'):
                location_parts.append(addr.get('city') or addr.get('town') or addr.get('village'))
            if addr.get('country'):
                location_parts.append(addr.get('country'))
            
            if location_parts:
                location_context = ', '.join(location_parts)
        
        # Build prompt - new approach for integrated description
        prompt = (
            f"Describe what you see in this image in one clear sentence (maximum 25 words). "
            f"Your description should naturally include the main subject AND the location. "
        )
        
        # Add location context if available
        if location_context:
            prompt += f"This photo was taken in {location_context}. "
        
        # Add Wikidata places context if available
        if wikidata_places and len(wikidata_places) > 0:
            print(f"\n=== Adding Wikidata context to prompt ===")
            print(f"Number of places: {len(wikidata_places)}")
            prompt += "\n\nBased on GPS coordinates, these specific places/structures are nearby (ordered by distance):\n"
            for i, place in enumerate(wikidata_places[:10], 1):  # Top 10 results
                place_info = f"{i}. {place.get('label', 'Unknown')}"
                if place.get('instance_of'):
                    place_info += f" ({place.get('instance_of')})"
                if place.get('description'):
                    place_info += f" - {place.get('description')}"
                place_info += f" [{place.get('distance_m', 0)}m away]"
                prompt += place_info + "\n"
                if i <= 3:  # Print first 3 to console
                    print(f"  {place_info}")
            prompt += (
                "\nIMPORTANT: If you recognize any of these specific places in the image, "
                "include its exact name in your description. For example: 'A Ryanair airplane at Terminal 2 of Berlin Brandenburg Airport' "
                "rather than just 'A Ryanair airplane at an airport terminal'.\n"
            )
            print(f"=== Wikidata context added ===\n")
        else:
            print(f"\n=== No Wikidata context available ===")
            print(f"wikidata_places: {wikidata_places}")
            print(f"===\n")
        
        prompt += (
            "\n\nProvide a single integrated sentence that describes the subject and location together. "
            "Do not split this into separate parts - make it one flowing sentence."
        )
        
        print(f"Prompt: {prompt}")
        
        # Prepare request to Ollama
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [{
                "role": "user",
                "content": prompt,
                "images": [image_base64]
            }],
            "stream": False
        }
        
        # Send request to Ollama
        req = urllib.request.Request(
            OLLAMA_API_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Sending request to Ollama at {OLLAMA_API_URL}...")
        
        with urllib.request.urlopen(req, timeout=120) as response:  # 2 minute timeout for vision
            result = json.loads(response.read().decode())
            print(f"=== OLLAMA RESPONSE ===")
            print(json.dumps(result, indent=2))
            
            # Extract description from response
            description = None
            if 'message' in result and 'content' in result['message']:
                description = result['message']['content'].strip()
            
            return {
                'description': description,
                'model': OLLAMA_MODEL,
                'prompt': prompt,
                'raw_response': result
            }
    
    except urllib.error.URLError as e:
        error_msg = f"Failed to connect to Ollama. Is it running? Error: {str(e)}"
        print(f"=== OLLAMA ERROR ===")
        print(error_msg)
        return {
            'description': None,
            'error': error_msg,
            'model': OLLAMA_MODEL
        }
    except Exception as e:
        error_msg = str(e)
        print(f"=== OLLAMA ERROR ===")
        print(error_msg)
        return {
            'description': None,
            'error': error_msg,
            'model': OLLAMA_MODEL
        }


def translate_text(text, target_language):
    """Translate text to target language using Ollama."""
    print(f"=== TRANSLATING TO {target_language.upper()} ===")
    
    try:
        prompt = f"Translate the following text from English to {target_language}. Only output the translation, nothing else. No interpretation, no explanation. Your only output should be a faithful translation of the text I gave, no other acknowledgement or talk.\n\n{text}"
        
        payload = {
            "model": OLLAMA_TRANSLATION_MODEL,
            "messages": [{
                "role": "user",
                "content": prompt
            }],
            "stream": False
        }
        
        req = urllib.request.Request(
            OLLAMA_API_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Translating: {text[:100]}...")
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode())
            
            translation = None
            if 'message' in result and 'content' in result['message']:
                translation = result['message']['content'].strip()
                print(f"Translation: {translation}")
            
            return translation
    
    except Exception as e:
        error_msg = str(e)
        print(f"=== TRANSLATION ERROR ({target_language}) ===")
        print(error_msg)
        return None


def suggest_filename(description, date_str, location_data):
    """Generate a suggested filename based on image description and metadata."""
    print(f"=== GENERATING FILENAME SUGGESTION ===")
    
    try:
        # Extract location info
        location_hint = ""
        if location_data and location_data.get('data'):
            loc = location_data['data']
            addr = loc.get('address', {})
            
            city = addr.get('city') or addr.get('town') or addr.get('village')
            country = addr.get('country')
            
            if city:
                location_hint = f" in {city}"
            elif country:
                location_hint = f" in {country}"
        
        # Extract date in YYYY-MM-DD format
        date_part = ""
        if date_str:
            # date_str is like "2025-10-30 08-01-42"
            date_part = date_str.split()[0] if ' ' in date_str else date_str
        
        prompt = (
            f"Based on this image description: \"{description}\", "
            f"suggest a short, descriptive filename (3-6 words maximum) for Wikimedia Commons. "
            f"The filename should describe the main subject clearly and concisely. "
            f"Use only lowercase letters, spaces (not hyphens), and keep it simple. "
            f"Do not include the file extension or date. "
            f"Only output the filename words, nothing else."
        )
        
        if location_hint:
            prompt += f" The photo was taken{location_hint}."
        
        payload = {
            "model": OLLAMA_TRANSLATION_MODEL,
            "messages": [{
                "role": "user",
                "content": prompt
            }],
            "stream": False
        }
        
        req = urllib.request.Request(
            OLLAMA_API_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Generating filename for: {description[:80]}...")
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            
            filename_base = None
            if 'message' in result and 'content' in result['message']:
                filename_base = result['message']['content'].strip()
                # Clean up the filename
                filename_base = filename_base.lower()
                filename_base = filename_base.replace('-', ' ')
                # Remove any quotes or extra punctuation
                filename_base = filename_base.strip('"\'.,!?')
                # Remove special tokens that sometimes appear in LLM output
                filename_base = filename_base.replace('end_of_turn>', '')
                filename_base = filename_base.replace('<end_of_turn>', '')
                filename_base = filename_base.replace('</s>', '')
                filename_base = filename_base.replace('<s>', '')
                # Clean up any extra whitespace
                filename_base = ' '.join(filename_base.split())
                print(f"Suggested filename base: {filename_base}")
            
            # Construct final filename with date
            if filename_base and date_part:
                suggested_filename = f"{filename_base} {date_part}.jpg"
            elif filename_base:
                suggested_filename = f"{filename_base}.jpg"
            elif date_part:
                suggested_filename = f"image {date_part}.jpg"
            else:
                suggested_filename = "image.jpg"
            
            return suggested_filename
    
    except Exception as e:
        error_msg = str(e)
        print(f"=== FILENAME GENERATION ERROR ===")
        print(error_msg)
        return None


class ImageUploadHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler for image uploads."""
    
    def do_GET(self):
        """Handle GET requests - serve static files."""
        if self.path == '/':
            self.path = '/index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)
    
    def do_POST(self):
        """Handle POST requests - process image upload."""
        if self.path == '/translate':
            # Handle translation request
            try:
                content_length = int(self.headers['Content-Length'])
                body = self.rfile.read(content_length)
                request_data = json.loads(body.decode())
                
                text = request_data.get('text')
                target_language = request_data.get('language')
                
                if not text or not target_language:
                    self.send_error(400, "Missing text or language")
                    return
                
                print(f"\n=== Translation Request: {target_language} ===")
                
                translation = translate_text(text, target_language)
                
                response = {
                    "success": True,
                    "translation": translation,
                    "language": target_language,
                    "model": OLLAMA_TRANSLATION_MODEL
                }
                
                # Send response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {
                    "success": False,
                    "error": str(e)
                }
                self.wfile.write(json.dumps(error_response).encode())
        
        elif self.path == '/suggest-filename':
            # Handle filename suggestion request
            try:
                content_length = int(self.headers['Content-Length'])
                body = self.rfile.read(content_length)
                request_data = json.loads(body.decode())
                
                description = request_data.get('description')
                date_str = request_data.get('date')
                location_data = request_data.get('location')
                
                if not description:
                    self.send_error(400, "Missing description")
                    return
                
                print(f"\n=== Filename Suggestion Request ===")
                
                suggested_filename = suggest_filename(description, date_str, location_data)
                
                response = {
                    "success": True,
                    "filename": suggested_filename,
                    "model": OLLAMA_TRANSLATION_MODEL
                }
                
                # Send response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {
                    "success": False,
                    "error": str(e)
                }
                self.wfile.write(json.dumps(error_response).encode())
        
        elif self.path == '/upload/vision':
            # Handle vision analysis request
            try:
                content_length = int(self.headers['Content-Length'])
                body = self.rfile.read(content_length)
                request_data = json.loads(body.decode())
                
                filename = request_data.get('filename')
                exif_data = request_data.get('exif')
                location_data = request_data.get('location')
                wikidata_places = request_data.get('wikidata_places')  # New parameter
                
                print(f"\n=== Vision Request Debug ===")
                print(f"Filename: {filename}")
                print(f"Has EXIF: {exif_data is not None}")
                print(f"Has Location: {location_data is not None}")
                print(f"Has Wikidata Places: {wikidata_places is not None}")
                if wikidata_places:
                    print(f"Number of Wikidata places: {len(wikidata_places)}")
                    print(f"First place: {wikidata_places[0] if wikidata_places else None}")
                
                if not filename:
                    self.send_error(400, "No filename provided")
                    return
                
                file_path = os.path.join(UPLOAD_DIR, filename)
                
                if not os.path.exists(file_path):
                    self.send_error(404, "File not found")
                    return
                
                # Analyze image with Ollama vision model
                print("\n" + "="*50)
                print("Starting Ollama vision analysis...")
                if wikidata_places:
                    print(f"Including {len(wikidata_places)} Wikidata places in context")
                print("="*50 + "\n")
                
                vision_data = analyze_image_with_ollama(
                    file_path,
                    exif_data,
                    location_data,
                    wikidata_places
                )
                
                # Send response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(vision_data, default=str).encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {
                    "success": False,
                    "error": str(e)
                }
                self.wfile.write(json.dumps(error_response).encode())
        
        elif self.path == '/wikidata-pois':
            # Handle Wikidata POI query request
            try:
                content_length = int(self.headers['Content-Length'])
                body = self.rfile.read(content_length)
                request_data = json.loads(body.decode())
                
                lat = request_data.get('lat')
                lon = request_data.get('lon')
                radius = request_data.get('radius', 1)  # Default 1km
                
                if lat is None or lon is None:
                    self.send_error(400, "Missing lat or lon coordinates")
                    return
                
                print(f"\n=== Wikidata POI Query Request ===")
                print(f"Coordinates: {lat}, {lon}")
                print(f"Radius: {radius}km")
                
                wikidata_result = query_wikidata_pois(lat, lon, radius)
                
                response = {
                    "success": True,
                    "wikidata": wikidata_result
                }
                
                # Send response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response, default=str).encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {
                    "success": False,
                    "error": str(e)
                }
                self.wfile.write(json.dumps(error_response).encode())
        
        elif self.path == '/upload':
            try:
                # Parse the multipart form data
                content_type = self.headers['Content-Type']
                if 'multipart/form-data' not in content_type:
                    self.send_error(400, "Bad Request: Expected multipart/form-data")
                    return
                
                # Get boundary
                boundary = content_type.split("boundary=")[1].encode()
                
                # Read the request body
                content_length = int(self.headers['Content-Length'])
                body = self.rfile.read(content_length)
                
                # Parse multipart data manually
                parts = body.split(b'--' + boundary)
                
                image_data = None
                filename = None
                
                for part in parts:
                    if b'Content-Disposition' in part:
                        # Extract filename
                        if b'filename=' in part:
                            headers, content = part.split(b'\r\n\r\n', 1)
                            headers_str = headers.decode('utf-8', errors='ignore')
                            
                            # Extract filename from headers
                            for line in headers_str.split('\n'):
                                if 'filename=' in line:
                                    # Extract filename and remove quotes properly
                                    filename_part = line.split('filename=')[1]
                                    # Remove leading/trailing whitespace and quotes
                                    filename = filename_part.strip().strip('"').strip("'").strip()
                                    break
                            
                            # Remove trailing boundary markers
                            image_data = content.rsplit(b'\r\n', 1)[0]
                
                if not image_data or not filename:
                    self.send_error(400, "No image file provided")
                    return
                
                # Clean the filename - remove any quotes or special characters that might cause issues
                filename = filename.replace('"', '').replace("'", '').replace('\n', '').replace('\r', '')
                
                # Save the uploaded image
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_filename = f"{timestamp}_{filename}"
                file_path = os.path.join(UPLOAD_DIR, safe_filename)
                
                with open(file_path, 'wb') as f:
                    f.write(image_data)
                
                # Extract EXIF data
                exif_data = extract_exif_data(file_path)
                
                # Perform reverse geocoding and POI search if GPS data available
                location_data = None
                poi_data = None
                camera_direction = None
                
                if 'GPSLatitude' in exif_data and 'GPSLongitude' in exif_data:
                    # Extract camera direction if available
                    if 'GPSData' in exif_data:
                        gps_data = exif_data['GPSData']
                        if 'GPSImgDirection' in gps_data:
                            camera_direction = float(gps_data['GPSImgDirection'])
                    
                    location_data = reverse_geocode(
                        exif_data['GPSLatitude'],
                        exif_data['GPSLongitude']
                    )
                    poi_data = search_nearby_poi(
                        exif_data['GPSLatitude'],
                        exif_data['GPSLongitude'],
                        camera_direction
                    )
                
                # Prepare initial response without vision data
                response = {
                    "success": True,
                    "filename": safe_filename,
                    "exif": exif_data,
                    "location": location_data,
                    "pois": poi_data,
                    "camera_direction": camera_direction,
                    "vision": None
                }
                
                # Send response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response, default=str).encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {
                    "success": False,
                    "error": str(e)
                }
                self.wfile.write(json.dumps(error_response).encode())
        else:
            self.send_error(404, "Not Found")
    
    def log_message(self, format, *args):
        """Custom log message format."""
        print(f"[{self.log_date_time_string()}] {format % args}")


def main():
    """Start the server."""
    Handler = ImageUploadHandler
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"🚀 Server running at http://localhost:{PORT}/")
        print(f"📁 Uploads will be saved to: {os.path.abspath(UPLOAD_DIR)}/")
        print(f"Press Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Server stopped")


if __name__ == "__main__":
    main()
