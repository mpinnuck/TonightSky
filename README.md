# TonightSky

**TonightSky** is a macOS application designed to assist amateur astronomers and astrophotographers in planning their night sky observations. With a user-friendly interface, it allows you to filter and explore deep sky objects from various catalogs, including Messier, NGC, and IC, while providing information about their transit times based on your location.

Inspired by the Seti-Astro "WhatsInTonightSky" app, **TonightSky** uses a custom `celestial_catalog.csv` file to deliver detailed information on celestial objects.

## Key Features

- **Deep Sky Object Catalogs**: Includes Messier, NGC, and IC catalogs, allowing users to explore a wide range of celestial objects.
- **Transit Time Calculation**: Automatically calculates the transit times for celestial objects relative to the meridian at your location and a nominated local time.
- **Customizable Filters**: Offers SQL-like condition filters to search and list objects based on specific criteria such as magnitude, object type, or size.
- **Location-Based Data**: Customize your location to calculate accurate transit times for astronomical events.
- **Responsive UI**: Features a simple, intuitive interface with timezone management and object listing.
- **macOS Support**: Optimized for macOS, this application is built specifically for users running macOS environments.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/mpinnuck/TonightSky.git
   cd TonightSky

2.	Set up the environment:
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt

3. Run the application:
   python TonightSky.py or 
   build app with 
      pyinstaller -D --windowed --clean --icon=TonightSky.icns --add-data "celestial_catalog.csv:." TonightSky.py
   or pyinstaller -F --windowed --clean --icon=TonightSky.icns --add-data "celestial_catalog.csv:." TonightSky.py
   -D creates a folder with all required items, loads instantly
   -F creates a single zipped file, when executed unzips to a temporary folder then executs this takes about 10 secs on an M2
   
## File Structure
.  \
├── .gitignore                 # Ignore files like virtual envs, build artifacts, etc.  \
├── TonightSky.py              # Main Python script for the application  \
├── TonightSky.spec            # PyInstaller spec file for packaging the application  \
├── TonightSky.icns            # macOS app icon  \
├── celestial_catalog.csv      # Deep sky object catalogs for the app  \
├── requirements.txt           # Python dependencies  \
├── build/                     # Build artifacts created during packaging  \
│   └── TonightSky/            # Contains build metadata and executable  \
├── tonightsky.json            # Stores user settings and configurations  

## Usage
1.	Custom Location: Set your location manually by inputting your latitude and longitude.
2. Enter a time of night as a base for relative transit times before or after that time
3.	Filter Objects: Use the SQL-like filter option to narrow down objects based on criteria such as altitude, magnitude, size, or transit time.
4.	Calculate Transit Times: The app calculates transit times relative to the meridian at your location and the current local time you provide.
5. Double click on a row to display the astrobin page for the object
6. Right click to copy a row to the clip board
7. The app saves settings in TonightSky.json on windows in APPDATA, on OSX in /Users/user/Library/Application Support/TonightSky/tonightsky.json

