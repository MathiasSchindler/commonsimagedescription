// Main application logic
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const loading = document.getElementById('loading');
const results = document.getElementById('results');
const errorDiv = document.getElementById('error');
const resetBtn = document.getElementById('resetBtn');
const copyBtn = document.getElementById('copyBtn');

// Store current data for MediaWiki generation
let currentData = {};
let translations = {};
let suggestedFilename = null;

// Dropzone click handler
dropzone.addEventListener('click', () => {
    fileInput.click();
});

// File input change handler
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

// Drag and drop handlers
dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
});

dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
});

dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    
    if (e.dataTransfer.files.length > 0) {
        handleFile(e.dataTransfer.files[0]);
    }
});

// Reset button handler
resetBtn.addEventListener('click', () => {
    resetUI();
});

// Copy button handler
copyBtn.addEventListener('click', async () => {
    const mediawikiText = document.getElementById('mediawikiOutput').textContent;
    
    try {
        await navigator.clipboard.writeText(mediawikiText);
        copyBtn.textContent = '✓ Copied!';
        copyBtn.classList.add('copied');
        
        setTimeout(() => {
            copyBtn.textContent = '📋 Copy to Clipboard';
            copyBtn.classList.remove('copied');
        }, 2000);
    } catch (err) {
        console.error('Failed to copy:', err);
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = mediawikiText;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            copyBtn.textContent = '✓ Copied!';
        } catch (err) {
            copyBtn.textContent = '❌ Failed to copy';
        }
        document.body.removeChild(textArea);
    }
});

// Main file handler
async function handleFile(file) {
    // Validate file type
    if (!file.type.startsWith('image/')) {
        showError('Please upload a valid image file');
        return;
    }

    // Show loading state
    hideAll();
    loading.classList.remove('hidden');
    updateLoadingText('Uploading image...');

    try {
        // Upload file to server
        const formData = new FormData();
        formData.append('image', file);

        updateLoadingText('Extracting EXIF data and location...');
        
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            currentData = {
                file: file,
                exif: data.exif,
                location: data.location,
                pois: data.pois,
                camera_direction: data.camera_direction,
                vision: null
            };
            
            // Display results immediately with EXIF and location data
            displayResults(file, data.exif, data.location, data.pois, data.camera_direction, null);
            
            // Start vision analysis in background
            updateVisionAnalysis(data.filename, data.exif, data.location);
        } else {
            showError(data.error || 'Failed to process image');
        }
    } catch (error) {
        showError('Error uploading file: ' + error.message);
    }
}

// Request vision analysis separately
async function updateVisionAnalysis(filename, exif, location) {
    const visionInfo = document.getElementById('visionInfo');
    
    // Show loading state in vision section
    visionInfo.innerHTML = '<div class="info-empty">🤖 Analyzing image with AI vision model...</div>';
    
    try {
        const response = await fetch('/upload/vision', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: filename,
                exif: exif,
                location: location
            })
        });

        const visionData = await response.json();
        
        // Update current data
        currentData.vision = visionData;
        
        // Update vision section
        const visionDisplayData = {};
        if (visionData && visionData.description) {
            visionDisplayData['Description'] = visionData.description;
            visionDisplayData['Model'] = visionData.model || 'Unknown';
        } else if (visionData && visionData.error) {
            visionDisplayData['Status'] = 'Analysis failed';
            visionDisplayData['Error'] = visionData.error;
        } else {
            visionDisplayData['Status'] = 'No vision analysis available';
        }
        
        displaySection(visionInfo, visionDisplayData);
        
        // Build context string for translation
        let contextForTranslation = '';
        if (currentData.location && currentData.location.data) {
            const loc = currentData.location.data;
            const addr = loc.address || {};
            
            const locationParts = [];
            if (addr.road) locationParts.push(addr.road);
            if (addr.suburb || addr.neighbourhood) locationParts.push(addr.suburb || addr.neighbourhood);
            if (addr.city || addr.town || addr.village) locationParts.push(addr.city || addr.town || addr.village);
            if (addr.country) locationParts.push(addr.country);
            
            if (locationParts.length > 0) {
                contextForTranslation = `taken in ${locationParts.join(', ')}`;
                
                // Add direction if available
                if (currentData.camera_direction !== null && currentData.camera_direction !== undefined) {
                    const cardinalDir = getCardinalDirection(currentData.camera_direction).split(' (')[0];
                    contextForTranslation += `, facing ${cardinalDir}`;
                }
            }
        }
        
        // Start translations with context
        if (visionData && visionData.description) {
            requestTranslations(visionData.description, contextForTranslation);
            
            // Also request filename suggestion (last step)
            requestFilenameSuggestion(visionData.description);
        }
        
        // Regenerate MediaWiki template with vision data
        generateMediaWikiTemplate(
            currentData.file,
            currentData.exif,
            currentData.location,
            currentData.pois,
            currentData.camera_direction,
            visionData
        );
        
        // Update API debug info
        updateApiDebugInfo();
        
    } catch (error) {
        visionInfo.innerHTML = '<div class="info-empty">❌ Failed to analyze image: ' + error.message + '</div>';
    }
}

// Update API debug info
function updateApiDebugInfo() {
    const apiDebug = document.getElementById('apiDebug');
    const debugInfo = {
        location_api: currentData.location ? {
            url: currentData.location.api_url,
            response: currentData.location.api_response
        } : 'No location data',
        poi_api: currentData.pois ? {
            url: currentData.pois.api_url,
            response: currentData.pois.api_response
        } : 'No POI data',
        vision_api: currentData.vision ? {
            model: currentData.vision.model,
            prompt: currentData.vision.prompt,
            response: currentData.vision.raw_response
        } : 'No vision data'
    };
    apiDebug.textContent = JSON.stringify(debugInfo, null, 2);
}

// Request translations for multiple languages
async function requestTranslations(text, contextStr) {
    const languages = ['German', 'Portuguese', 'Hebrew'];
    
    console.log('Starting translations...');
    
    // First translate the main description
    for (const lang of languages) {
        try {
            const response = await fetch('/translate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: text,
                    language: lang
                })
            });
            
            const data = await response.json();
            
            if (data.success && data.translation) {
                translations[lang.toLowerCase()] = {
                    description: data.translation,
                    context: null
                };
                console.log(`${lang} description received:`, data.translation);
            }
        } catch (error) {
            console.error(`Failed to translate description to ${lang}:`, error);
        }
    }
    
    // Then translate the context string if available
    if (contextStr) {
        for (const lang of languages) {
            try {
                const response = await fetch('/translate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        text: contextStr,
                        language: lang
                    })
                });
                
                const data = await response.json();
                
                if (data.success && data.translation) {
                    if (translations[lang.toLowerCase()]) {
                        translations[lang.toLowerCase()].context = data.translation;
                    }
                    console.log(`${lang} context received:`, data.translation);
                }
            } catch (error) {
                console.error(`Failed to translate context to ${lang}:`, error);
            }
        }
    }
    
    // Regenerate template after all translations
    generateMediaWikiTemplate(
        currentData.file,
        currentData.exif,
        currentData.location,
        currentData.pois,
        currentData.camera_direction,
        currentData.vision
    );
}

// Request filename suggestion
async function requestFilenameSuggestion(description) {
    const filenameEl = document.getElementById('suggestedFilename');
    
    // Show generating state
    filenameEl.innerHTML = '<div class="filename-loading">Generating filename suggestion...</div>';
    
    try {
        // Extract date from EXIF
        let dateStr = '';
        if (currentData.exif) {
            dateStr = currentData.exif.DateTime || currentData.exif.DateTimeOriginal || '';
            if (dateStr) {
                // Convert "2024:11:17 09:03:00" to "2024-11-17"
                dateStr = dateStr.split(' ')[0].replace(/:/g, '-');
            }
        }
        
        const response = await fetch('/suggest-filename', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                description: description,
                date: dateStr,
                location: currentData.location
            })
        });
        
        const data = await response.json();
        
        if (data.success && data.filename) {
            suggestedFilename = data.filename;
            filenameEl.innerHTML = `<span class="filename">${data.filename}</span>`;
            console.log('Filename suggestion:', data.filename);
        } else {
            filenameEl.innerHTML = '<div class="filename-loading">Could not generate filename</div>';
        }
    } catch (error) {
        console.error('Failed to get filename suggestion:', error);
        filenameEl.innerHTML = '<div class="filename-loading">Failed to generate filename</div>';
    }
}

// Update loading text
function updateLoadingText(mainText, subText = '') {
    const loadingTextEl = document.getElementById('loadingText');
    const loadingSubtextEl = document.getElementById('loadingSubtext');
    
    if (loadingTextEl) loadingTextEl.textContent = mainText;
    if (loadingSubtextEl) loadingSubtextEl.textContent = subText;
}

// Display results
function displayResults(file, exif, location, pois, cameraDirection, vision) {
    hideAll();
    results.classList.remove('hidden');

    // Display image preview
    const imagePreview = document.getElementById('imagePreview');
    const img = document.createElement('img');
    img.src = URL.createObjectURL(file);
    img.alt = 'Uploaded image';
    imagePreview.innerHTML = '';
    imagePreview.appendChild(img);

    // AI Vision Analysis
    const visionInfo = document.getElementById('visionInfo');
    const visionData = {};
    
    if (vision && vision.description) {
        visionData['Description'] = vision.description;
        visionData['Model'] = vision.model || 'Unknown';
    } else if (vision && vision.error) {
        visionData['Status'] = 'Analysis failed';
        visionData['Error'] = vision.error;
    } else if (vision === null) {
        visionData['Status'] = '🤖 Analyzing with AI vision model...';
    } else {
        visionData['Status'] = 'No vision analysis available';
    }
    
    displaySection(visionInfo, visionData);

    // Date & Time information
    const dateInfo = document.getElementById('dateInfo');
    displaySection(dateInfo, {
        'Date Taken': exif.DateTime || exif.DateTimeOriginal || 'Not available',
        'Date Digitized': exif.DateTimeDigitized || 'Not available',
        'Modification Date': exif.ModifyDate || 'Not available'
    });

    // Location information
    const locationInfo = document.getElementById('locationInfo');
    const locationData = {};
    
    if (exif.GPSLatitude && exif.GPSLongitude) {
        locationData['Coordinates'] = `${exif.GPSLatitude.toFixed(6)}, ${exif.GPSLongitude.toFixed(6)}`;
        
        if (location && location.data) {
            // Handle JSON format response (not geojson)
            const addr = location.data.address;
            if (addr) {
                if (addr.country) locationData['Country'] = addr.country;
                if (addr.country_code) locationData['Country Code'] = addr.country_code.toUpperCase();
                if (addr.state || addr.region) locationData['State/Region'] = addr.state || addr.region;
                if (addr.province) locationData['Province'] = addr.province;
                if (addr.county) locationData['County'] = addr.county;
                if (addr.city) locationData['City'] = addr.city;
                if (addr.town) locationData['Town'] = addr.town;
                if (addr.village) locationData['Village'] = addr.village;
                if (addr.municipality) locationData['Municipality'] = addr.municipality;
                if (addr.suburb) locationData['Suburb'] = addr.suburb;
                if (addr.neighbourhood) locationData['Neighbourhood'] = addr.neighbourhood;
                if (addr.road) locationData['Road'] = addr.road;
                if (addr.house_number) locationData['House Number'] = addr.house_number;
                if (addr.postcode) locationData['Postcode'] = addr.postcode;
            }
            if (location.data.display_name) {
                locationData['Full Address'] = location.data.display_name;
            }
        }
    } else {
        locationData['GPS Data'] = 'Not available';
    }
    
    if (exif.GPSData && exif.GPSData.GPSAltitude) {
        locationData['Altitude'] = `${exif.GPSData.GPSAltitude} meters`;
    }

    displaySection(locationInfo, locationData);

    // Camera Direction
    const directionInfo = document.getElementById('directionInfo');
    const directionData = {};
    
    if (cameraDirection !== null && cameraDirection !== undefined) {
        directionData['Compass Direction'] = `${cameraDirection.toFixed(1)}°`;
        directionData['Cardinal Direction'] = getCardinalDirection(cameraDirection);
        directionData['Note'] = 'Camera was pointing in this direction when photo was taken';
    } else {
        directionData['Status'] = 'Camera direction not recorded';
    }
    
    displaySection(directionInfo, directionData);

    // Points of Interest
    const poiInfo = document.getElementById('poiInfo');
    const poiData = {};
    
    if (pois && pois.pois && pois.pois.length > 0) {
        pois.pois.forEach((poi, index) => {
            const label = `${index + 1}. ${poi.name || 'Unnamed'}`;
            let details = [];
            if (poi.class) details.push(`${poi.class}`);
            if (poi.type) details.push(`${poi.type}`);
            if (poi.distance) details.push(`~${poi.distance}m away`);
            poiData[label] = details.length > 0 ? details.join(' • ') : 'No details';
        });
        poiData['_note'] = 'Note: POIs are nearby but may not be what is shown in the photo';
    } else {
        poiData['Status'] = 'No nearby points of interest found';
    }
    
    displaySection(poiInfo, poiData);

    // Camera information
    const cameraInfo = document.getElementById('cameraInfo');
    displaySection(cameraInfo, {
        'Make': exif.Make || 'Unknown',
        'Model': exif.Model || 'Unknown',
        'Lens': exif.LensModel || 'Not available',
        'Software': exif.Software || 'Not available'
    });

    // Technical details
    const technicalInfo = document.getElementById('technicalInfo');
    displaySection(technicalInfo, {
        'ISO': exif.ISOSpeedRatings || exif.ISO || 'Not available',
        'Exposure Time': exif.ExposureTime || 'Not available',
        'F-Number': exif.FNumber || 'Not available',
        'Focal Length': exif.FocalLength ? `${exif.FocalLength} mm` : 'Not available',
        'Image Width': exif.ImageWidth || exif.ExifImageWidth || 'Not available',
        'Image Height': exif.ImageHeight || exif.ExifImageHeight || 'Not available',
        'Orientation': getOrientation(exif.Orientation) || 'Normal',
        'Color Space': exif.ColorSpace === 1 ? 'sRGB' : exif.ColorSpace || 'Not available'
    });

    // Raw EXIF data
    const rawExif = document.getElementById('rawExif');
    rawExif.textContent = JSON.stringify(exif, null, 2);

    // API Debug Info
    const apiDebug = document.getElementById('apiDebug');
    const debugInfo = {
        location_api: location ? {
            url: location.api_url,
            response: location.api_response
        } : 'No location data',
        poi_api: pois ? {
            url: pois.api_url,
            response: pois.api_response
        } : 'No POI data',
        vision_api: vision ? {
            model: vision.model,
            prompt: vision.prompt,
            response: vision.raw_response
        } : 'No vision data'
    };
    apiDebug.textContent = JSON.stringify(debugInfo, null, 2);

    // Generate MediaWiki template
    generateMediaWikiTemplate(file, exif, location, pois, cameraDirection, vision);
}

// Helper function to display a section
function displaySection(container, data) {
    container.innerHTML = '';
    
    let hasData = false;
    for (const [label, value] of Object.entries(data)) {
        if (value && value !== 'Not available' && value !== 'Unknown') {
            hasData = true;
            const labelDiv = document.createElement('div');
            labelDiv.className = 'info-label';
            labelDiv.textContent = label + ':';
            
            const valueDiv = document.createElement('div');
            valueDiv.className = 'info-value';
            
            if (typeof value === 'string' && value.startsWith('<a')) {
                valueDiv.innerHTML = value;
            } else {
                valueDiv.textContent = value;
            }
            
            container.appendChild(labelDiv);
            container.appendChild(valueDiv);
        }
    }
    
    if (!hasData) {
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'info-empty';
        emptyDiv.textContent = 'No data available';
        container.appendChild(emptyDiv);
    }
}

// Create OpenStreetMap link
function createOSMLink(lat, lon) {
    const url = `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}&zoom=15`;
    return `<a href="${url}" target="_blank" style="color: var(--primary-color);">View on OpenStreetMap</a>`;
}

// Get cardinal direction from degrees
function getCardinalDirection(degrees) {
    const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 
                       'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
    const index = Math.round(degrees / 22.5) % 16;
    const fullNames = {
        'N': 'North', 'NNE': 'North-Northeast', 'NE': 'Northeast', 'ENE': 'East-Northeast',
        'E': 'East', 'ESE': 'East-Southeast', 'SE': 'Southeast', 'SSE': 'South-Southeast',
        'S': 'South', 'SSW': 'South-Southwest', 'SW': 'Southwest', 'WSW': 'West-Southwest',
        'W': 'West', 'WNW': 'West-Northwest', 'NW': 'Northwest', 'NNW': 'North-Northwest'
    };
    const abbr = directions[index];
    return `${fullNames[abbr]} (${abbr})`;
}

// Generate MediaWiki template
function generateMediaWikiTemplate(file, exif, location, pois, cameraDirection, vision) {
    const output = document.getElementById('mediawikiOutput');
    
    // Extract date
    let dateStr = exif.DateTime || exif.DateTimeOriginal || '';
    if (dateStr) {
        // Convert "2024:11:17 09:03:00" to "2024-11-17 09:03:00"
        dateStr = dateStr.replace(/:/g, '-').replace(/-(\d{2}:\d{2}:\d{2})/, ' $1');
    }
    
    // Extract location details
    let locationStr = '';
    let country = '';
    let city = '';
    let state = '';
    let countryCode = '';
    
    if (location && location.data) {
        const data = location.data;
        const addr = data.address || {};
        
        country = addr.country || '';
        countryCode = addr.country_code || '';
        state = addr.state || addr.region || addr.province || '';
        city = addr.city || addr.town || addr.village || addr.municipality || '';
        
        const parts = [];
        if (addr.road) parts.push(addr.road);
        if (addr.suburb || addr.neighbourhood) parts.push(addr.suburb || addr.neighbourhood);
        if (city) parts.push(city);
        if (state && state !== city) parts.push(state);
        if (country) parts.push(country);
        locationStr = parts.join(', ');
    }
    
    // Build description based on available data
    let descriptionEn = '';
    
    // Use AI vision description as primary content
    if (vision && vision.description) {
        descriptionEn = vision.description;
    } else {
        descriptionEn = 'Photograph';
    }
    
    // Add location context (where photo was taken)
    let contextStr = '';
    if (locationStr) {
        contextStr = ` (taken in ${locationStr}`;
        
        // Add camera direction context
        if (cameraDirection !== null && cameraDirection !== undefined) {
            const cardinalDir = getCardinalDirection(cameraDirection).split(' (')[0];
            contextStr += `, facing ${cardinalDir}`;
        }
        
        contextStr += ')';
    }
    
    // Camera info
    const camera = exif.Make && exif.Model ? `${exif.Make} ${exif.Model}` : '';
    
    // Build template with multi-language descriptions
    let template = `=={{int:filedesc}}==
{{Information
|description={{en|1=${descriptionEn}${contextStr}}}`;

    // Add German translation if available
    if (translations.german && translations.german.description) {
        const deContext = translations.german.context || contextStr;
        template += `
{{de|1=${translations.german.description}${deContext ? ' (' + deContext + ')' : ''}}}`;
    }
    
    // Add Portuguese translation if available
    if (translations.portuguese && translations.portuguese.description) {
        const ptContext = translations.portuguese.context || contextStr;
        template += `
{{pt|1=${translations.portuguese.description}${ptContext ? ' (' + ptContext + ')' : ''}}}`;
    }
    
    // Add Hebrew translation if available
    if (translations.hebrew && translations.hebrew.description) {
        const heContext = translations.hebrew.context || contextStr;
        template += `
{{he|1=${translations.hebrew.description}${heContext ? ' (' + heContext + ')' : ''}}}`;
    }
    
    template += `
|date=${dateStr || '{{According to Exif data}}'}
|source={{own}}
|author=
|permission=
|other versions=
}}`;

    // Add location template if GPS data available
    if (exif.GPSLatitude && exif.GPSLongitude) {
        template += `{{Location|${exif.GPSLatitude.toFixed(8)}|${exif.GPSLongitude.toFixed(8)}`;
        
        // Add heading/direction if available
        if (cameraDirection !== null && cameraDirection !== undefined) {
            template += `|heading:${cameraDirection.toFixed(1)}`;
        }
        
        template += '}}';
    }

    template += '\n\n=={{int:license-header}}==\n{{CC0}}\n\n';
    
    // Add categories section
    template += '[[Category:Uploaded via Commons Image Analyzer]]\n';
    if (country) {
        template += `[[Category:${country}]]\n`;
    }
    if (city) {
        template += `[[Category:${city}]]\n`;
    }
    
    output.textContent = template;
}

// Get orientation description
function getOrientation(value) {
    const orientations = {
        1: 'Normal',
        2: 'Mirrored',
        3: 'Rotated 180°',
        4: 'Mirrored and rotated 180°',
        5: 'Mirrored and rotated 270° CW',
        6: 'Rotated 90° CW',
        7: 'Mirrored and rotated 90° CW',
        8: 'Rotated 270° CW'
    };
    return orientations[value] || value;
}

// Toggle collapsible section
function toggleSection(sectionId) {
    const section = document.getElementById(sectionId);
    const header = section.previousElementSibling;
    const icon = header.querySelector('.toggle-icon');
    
    section.classList.toggle('collapsed');
    icon.classList.toggle('expanded');
}

// Show error message
function showError(message) {
    hideAll();
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
    dropzone.classList.remove('hidden');
}

// Hide all sections
function hideAll() {
    loading.classList.add('hidden');
    results.classList.add('hidden');
    errorDiv.classList.add('hidden');
    dropzone.classList.add('hidden');
}

// Reset UI
function resetUI() {
    fileInput.value = '';
    translations = {}; // Clear translations
    suggestedFilename = null; // Clear filename
    hideAll();
    dropzone.classList.remove('hidden');
}
