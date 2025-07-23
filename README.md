# 🏞️ QGIS Playground Accessibility Tool

A simple QGIS plugin that analyzes playground accessibility from any location using real-world walking routes and OpenStreetMap data.


### Tool Interface

<img width="1274" height="788" alt="image" src="https://github.com/user-attachments/assets/de5cc497-e10e-4e0d-b30a-e5e3f09ea414" />




## ✨ Features

- **Point-and-click analysis**: Click anywhere on the map to analyze playground access
- **Real walking routes**: Uses OSRM routing API for actual walking distances
- **OpenStreetMap integration**: Fetches live playground data via Overpass API
- **Smart scoring system**: Color-coded accessibility ratings (🟢 Excellent / 🟡 Moderate / 🔴 Limited)
- **PDF export**: Generate professional reports with maps and statistics
- **Perfect circular buffers**: Works correctly with any coordinate system (EPSG:3857, etc.)

## 🚀 Quick Start

### Installation

1. **Download** the `run_playground_tool.py` file
2. **Open QGIS** (version 3.0 or higher)
3. **Open Python Console**: Go to `Plugins` → `Python Console`
4. **Load the script**: Click the folder icon and select `run_playground_tool.py`
5. **Run**: Click the play button - the tool will open automatically!

### Usage

1. **Set search distance** (100-1000 meters, default: 400m)
2. **Click "📍 Click Point on Map"**
3. **Click anywhere on your map** to select analysis location
4. **Click "🔍 Analyze Playground Access"**
5. **View results** and optionally **export PDF report**

## 🎯 How It Works

### Analysis Process
1. **Creates buffer zone** around your selected point
2. **Fetches playground data** from OpenStreetMap within the buffer
3. **Calculates walking routes** to all playgrounds using OSRM API
4. **Finds optimal route** with shortest walking distance
5. **Assigns accessibility score** based on walking distance

### Scoring System
- 🟢 **Excellent** (≤200m): Great access to playgrounds
- 🟡 **Moderate** (200-500m): Reasonable access to playgrounds  
- 🔴 **Limited** (>500m): Poor access to playgrounds

### Map Visualization
- 🔴 **Red circle**: Your analysis point
- 🔵 **Blue area**: Search buffer zone
- 🟢 **Green squares**: Playgrounds found
- 🔴 **Red dashed line**: Optimal walking route

## 📋 Requirements

- **QGIS 3.0+** (tested on QGIS 3.16+)
- **Internet connection** (for OpenStreetMap and routing data)
- **Python libraries**: `requests`, `json`, `math` (included with QGIS)

## 📊 Example Results

```
🔍 PLAYGROUND ACCESSIBILITY ANALYSIS
📍 Search radius: 400m
🏞️ Playgrounds found: 3
📏 Straight-line distance: 180m
🚶 Walking distance: 240m (1.3x straight-line)
🟢 EXCELLENT - Great access to playgrounds!
```

## 🔧 Technical Details

### APIs Used
- **OpenStreetMap Overpass API**: Real-time playground data
- **OSRM Routing API**: Walking route calculations
- **QGIS Python API**: Map visualization and PDF export

### Data Sources
- Playground locations from OpenStreetMap contributors
- Walking routes optimized for pedestrian access
- Cached results for improved performance




**Made with ❤️ **
