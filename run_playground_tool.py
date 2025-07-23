# run_playground_tool.py - Simple Playground Accessibility Tool
import requests, json, math
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import Qt, QRectF
from qgis.PyQt.QtGui import QFont
from qgis.core import *
from qgis.gui import QgsMapToolEmitPoint

class SimplePlaygroundTool(QDialog):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.current_point = None
        self.map_tool = None
        self.last_results = None
        self.setupUI()
        
    def setupUI(self):
        self.setWindowTitle("Playground Accessibility")
        self.setMinimumSize(350, 400)
        layout = QVBoxLayout()
        
        title = QLabel("🏞️ Playground Accessibility Tool")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        buffer_layout = QHBoxLayout()
        buffer_layout.addWidget(QLabel("Search Distance:"))
        self.buffer_spin = QSpinBox()
        self.buffer_spin.setRange(100, 1000)
        self.buffer_spin.setValue(400)
        self.buffer_spin.setSuffix(" meters")
        buffer_layout.addWidget(self.buffer_spin)
        layout.addLayout(buffer_layout)
        
        self.point_button = QPushButton("📍 Click Point on Map")
        self.point_button.clicked.connect(self.select_point)
        layout.addWidget(self.point_button)
        
        self.status_label = QLabel("Click the button above, then click anywhere on the map")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
        layout.addWidget(self.status_label)
        
        self.analyze_button = QPushButton("🔍 Analyze Playground Access")
        self.analyze_button.clicked.connect(self.analyze)
        self.analyze_button.setEnabled(False)
        self.analyze_button.setStyleSheet("font-weight: bold; padding: 8px;")
        layout.addWidget(self.analyze_button)
        
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(150)
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)
        
        self.export_button = QPushButton("📄 Export PDF Report")
        self.export_button.clicked.connect(self.export_pdf)
        self.export_button.setEnabled(False)
        self.export_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        layout.addWidget(self.export_button)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        self.setLayout(layout)
    
    def select_point(self):
        if self.map_tool is None:
            self.map_tool = QgsMapToolEmitPoint(self.iface.mapCanvas())
            self.map_tool.canvasClicked.connect(self.point_selected)
            self.iface.mapCanvas().setMapTool(self.map_tool)
            self.point_button.setText("❌ Cancel Point Selection")
            self.status_label.setText("Now click anywhere on the map to select your analysis point...")
        else:
            self.iface.mapCanvas().unsetMapTool(self.map_tool)
            self.map_tool = None
            self.point_button.setText("📍 Click Point on Map")
            self.status_label.setText("Point selected! Ready to analyze." if self.current_point else "Click the button above, then click anywhere on the map")
    
    def point_selected(self, point, button):
        self.current_point = point
        self.select_point()
        self.status_label.setText(f"✅ Point selected: {point.x():.5f}, {point.y():.5f}")
        self.analyze_button.setEnabled(True)
    
    def analyze(self):
        if not self.current_point:
            QMessageBox.warning(self, "No Point", "Please select a point on the map first!")
            return
        
        try:
            self.analyze_button.setEnabled(False)
            self.status_label.setText("🔄 Fetching playground data...")
            
            buffer_distance = self.buffer_spin.value()
            point_wgs84 = self.transform_to_wgs84(self.current_point)
            playgrounds = self.get_playgrounds(point_wgs84, buffer_distance)
            
            self.status_label.setText("🔄 Calculating distances and routes...")
            results = self.calculate_metrics(point_wgs84, playgrounds, buffer_distance)
            
            self.last_results = results
            self.create_map_layers(self.current_point, results, buffer_distance)
            self.display_results(results)
            self.export_button.setEnabled(True)
            
            if results['walking_route']:
                self.status_label.setText("✅ Analysis complete with walking route!")
            else:
                self.status_label.setText("✅ Analysis complete!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Analysis failed: {str(e)}")
            self.status_label.setText("❌ Analysis failed. Check your internet connection.")
        
        finally:
            self.analyze_button.setEnabled(True)
    
    def transform_to_wgs84(self, point):
        canvas_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        wgs84_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        if canvas_crs != wgs84_crs:
            transform = QgsCoordinateTransform(canvas_crs, wgs84_crs, QgsProject.instance())
            geom = QgsGeometry.fromPointXY(point)
            geom.transform(transform)
            return geom.asPoint()
        return point
    
    def get_playgrounds(self, point_wgs84, buffer_distance):
        lat, lon = point_wgs84.y(), point_wgs84.x()
        margin = buffer_distance / 111000
        bbox = f"{lat - margin},{lon - margin},{lat + margin},{lon + margin}"
        
        query = f'[out:json][timeout:25];(node["leisure"="playground"]({bbox});way["leisure"="playground"]({bbox}););out center;'
        
        response = requests.post("https://overpass-api.de/api/interpreter", data=query, timeout=30)
        response.raise_for_status()
        
        playgrounds = []
        for element in response.json().get('elements', []):
            if element['type'] == 'node':
                pg_lat, pg_lon = element['lat'], element['lon']
            elif 'center' in element:
                pg_lat, pg_lon = element['center']['lat'], element['center']['lon']
            else:
                continue
            playgrounds.append({'lat': pg_lat, 'lon': pg_lon, 'name': element.get('tags', {}).get('name', 'Playground')})
        
        return playgrounds
    
    def calculate_metrics(self, point_wgs84, playgrounds, buffer_distance):
        canvas_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        wgs84_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(wgs84_crs, canvas_crs, QgsProject.instance())
        
        point_geom = QgsGeometry.fromPointXY(point_wgs84)
        point_geom.transform(transform)
        point_canvas = point_geom.asPoint()
        
        straight_distances = []
        playgrounds_in_buffer = []
        
        for playground in playgrounds:
            pg_geom = QgsGeometry.fromPointXY(QgsPointXY(playground['lon'], playground['lat']))
            pg_geom.transform(transform)
            pg_point = pg_geom.asPoint()
            
            distance = math.sqrt((point_canvas.x() - pg_point.x())**2 + (point_canvas.y() - pg_point.y())**2)
            
            if distance <= buffer_distance:
                playgrounds_in_buffer.append(playground)
                straight_distances.append(distance)
        
        count = len(playgrounds_in_buffer)
        if count == 0:
            return {
                'count': 0, 
                'nearest_distance': float('inf'), 
                'walking_distance': None,
                'walking_route': None,
                'score': "🔴 LIMITED", 
                'score_desc': "No playgrounds found.", 
                'playgrounds': []
            }
        
        nearest_straight_distance = min(straight_distances)
        
        # Try to get walking routes to all playgrounds
        best_walking_distance = None
        best_walking_route = None
        
        for i, playground in enumerate(playgrounds_in_buffer):
            walking_dist, walking_route = self.get_walking_route(point_wgs84, playground)
            if walking_dist and (best_walking_distance is None or walking_dist < best_walking_distance):
                best_walking_distance = walking_dist
                best_walking_route = walking_route
        
        # Use walking distance for scoring if available
        score_distance = best_walking_distance if best_walking_distance else nearest_straight_distance
        
        if score_distance <= 200:
            score, score_desc = "🟢 EXCELLENT", "Great access to playgrounds!"
        elif score_distance <= 500:
            score, score_desc = "🟡 MODERATE", "Reasonable access to playgrounds."
        else:
            score, score_desc = "🔴 LIMITED", "Limited access to playgrounds."
        
        return {
            'count': count, 
            'nearest_distance': nearest_straight_distance,
            'walking_distance': best_walking_distance,
            'walking_route': best_walking_route,
            'score': score, 
            'score_desc': score_desc, 
            'playgrounds': playgrounds_in_buffer
        }
    
    def get_walking_route(self, start_point, end_playground):
        try:
            start_lon, start_lat = start_point.x(), start_point.y()
            end_lon, end_lat = end_playground['lon'], end_playground['lat']
            
            url = f"http://router.project-osrm.org/route/v1/foot/{start_lon},{start_lat};{end_lon},{end_lat}"
            params = {'overview': 'full', 'geometries': 'geojson'}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data['code'] == 'Ok' and data['routes']:
                route = data['routes'][0]
                walking_distance = route['distance']
                coordinates = route['geometry']['coordinates']
                
                # Simple check: only accept reasonable routes
                if 10 <= walking_distance <= 10000:  # 10m to 10km
                    points = [QgsPointXY(coord[0], coord[1]) for coord in coordinates]
                    route_geom = QgsGeometry.fromPolylineXY(points)
                    return walking_distance, route_geom
        except:
            pass
        
        return None, None
    
    def create_map_layers(self, point, results, buffer_distance):
        canvas_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        
        # Buffer layer
        buffer_layer = QgsVectorLayer(f"Polygon?crs={canvas_crs.authid()}", "Playground Buffer", "memory")
        point_geom = QgsGeometry.fromPointXY(point)
        buffer_geom = point_geom.buffer(buffer_distance, 32)
        
        buffer_feature = QgsFeature()
        buffer_feature.setGeometry(buffer_geom)
        buffer_layer.dataProvider().addFeature(buffer_feature)
        buffer_layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({'color': '0,0,255,30', 'outline_color': 'blue', 'outline_width': '2'})))
        
        # Point layer
        point_layer = QgsVectorLayer(f"Point?crs={canvas_crs.authid()}", "Analysis Point", "memory")
        point_feature = QgsFeature()
        point_feature.setGeometry(point_geom)
        point_layer.dataProvider().addFeature(point_feature)
        point_layer.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple({'name': 'circle', 'color': 'red', 'size': '6', 'outline_color': 'darkred', 'outline_width': '2'})))
        
        # Playground layer
        if results['playgrounds']:
            playground_layer = QgsVectorLayer(f"Point?crs={canvas_crs.authid()}", "Playgrounds Found", "memory")
            wgs84_crs = QgsCoordinateReferenceSystem("EPSG:4326")
            transform = QgsCoordinateTransform(wgs84_crs, canvas_crs, QgsProject.instance())
            
            for playground in results['playgrounds']:
                pg_feature = QgsFeature()
                pg_geom = QgsGeometry.fromPointXY(QgsPointXY(playground['lon'], playground['lat']))
                pg_geom.transform(transform)
                pg_feature.setGeometry(pg_geom)
                playground_layer.dataProvider().addFeature(pg_feature)
            playground_layer.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple({'name': 'square', 'color': 'green', 'size': '8', 'outline_color': 'darkgreen', 'outline_width': '2'})))
            QgsProject.instance().addMapLayer(playground_layer)
        
        # Walking route layer
        if results['walking_route']:
            route_layer = QgsVectorLayer(f"LineString?crs={canvas_crs.authid()}", "Walking Route", "memory")
            wgs84_crs = QgsCoordinateReferenceSystem("EPSG:4326")
            transform = QgsCoordinateTransform(wgs84_crs, canvas_crs, QgsProject.instance())
            
            route_feature = QgsFeature()
            route_geom = QgsGeometry(results['walking_route'])
            route_geom.transform(transform)
            route_feature.setGeometry(route_geom)
            route_layer.dataProvider().addFeature(route_feature)
            route_layer.setRenderer(QgsSingleSymbolRenderer(QgsLineSymbol.createSimple({'color': 'red', 'width': '3', 'penstyle': 'dash'})))
            QgsProject.instance().addMapLayer(route_layer)
        
        QgsProject.instance().addMapLayer(buffer_layer)
        QgsProject.instance().addMapLayer(point_layer)
        self.iface.mapCanvas().refresh()
    
    def display_results(self, results):
        if results['count'] == 0:
            result_text = f"""🔍 PLAYGROUND ACCESSIBILITY ANALYSIS

📍 Search radius: {self.buffer_spin.value()}m

❌ No playgrounds found in this area
   
💡 Try:
   • Increasing the search distance
   • Selecting a more urban location

{results['score']} - {results['score_desc']}"""
        else:
            walking_info = ""
            if results['walking_distance']:
                ratio = results['walking_distance'] / results['nearest_distance']
                walking_info = f"🚶 Walking distance: {results['walking_distance']:.0f}m ({ratio:.1f}x straight-line)"
            else:
                walking_info = "🚶 Walking distance: Not available"
            
            result_text = f"""🔍 PLAYGROUND ACCESSIBILITY ANALYSIS

📍 Search radius: {self.buffer_spin.value()}m

🏞️ Playgrounds found: {results['count']}
📏 Straight-line distance: {results['nearest_distance']:.0f}m
{walking_info}

{results['score']} - {results['score_desc']}"""
        
        self.results_text.setText(result_text)
    
    def export_pdf(self):
        if not self.last_results:
            QMessageBox.warning(self, "No Results", "Please run an analysis first!")
            return
        
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"playground_analysis_{timestamp}.pdf"
            
            file_path, _ = QFileDialog.getSaveFileName(self, "Export PDF Report", filename, "PDF files (*.pdf)")
            if not file_path:
                return
            
            project = QgsProject.instance()
            layout = QgsPrintLayout(project)
            layout.initializeDefaults()
            
            # Add map
            map_item = QgsLayoutItemMap(layout)
            map_item.attemptSetSceneRect(QRectF(10, 10, 180, 120))
            map_item.setExtent(self.iface.mapCanvas().extent())
            layout.addLayoutItem(map_item)
            
            # Add title
            title_item = QgsLayoutItemLabel(layout)
            title_item.setText("🔍 PLAYGROUND ACCESSIBILITY ANALYSIS")
            title_item.setFont(QFont("Arial", 16, QFont.Bold))
            title_item.attemptSetSceneRect(QRectF(10, 140, 180, 10))
            layout.addLayoutItem(title_item)
            
            # Add results
            if self.last_results['count'] == 0:
                results_text = f"""📍 Search radius: {self.buffer_spin.value()}m

❌ No playgrounds found in this area

{self.last_results['score']} - {self.last_results['score_desc']}

Analysis completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            else:
                walking_info = ""
                if self.last_results['walking_distance']:
                    ratio = self.last_results['walking_distance'] / self.last_results['nearest_distance']
                    walking_info = f"🚶 Walking distance: {self.last_results['walking_distance']:.0f}m ({ratio:.1f}x straight-line)"
                else:
                    walking_info = "🚶 Walking distance: Not available"
                
                results_text = f"""📍 Search radius: {self.buffer_spin.value()}m

🏞️ Playgrounds found: {self.last_results['count']}
📏 Straight-line distance: {self.last_results['nearest_distance']:.0f}m
{walking_info}

{self.last_results['score']} - {self.last_results['score_desc']}

Analysis completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            
            results_item = QgsLayoutItemLabel(layout)
            results_item.setText(results_text)
            results_item.setFont(QFont("Arial", 12))
            results_item.attemptSetSceneRect(QRectF(10, 155, 180, 60))
            layout.addLayoutItem(results_item)
            
            # Export PDF
            exporter = QgsLayoutExporter(layout)
            exporter.exportToPdf(file_path, QgsLayoutExporter.PdfExportSettings())
            
            QMessageBox.information(self, "Export Successful", f"Report exported to:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export PDF:\n{str(e)}")

def run_playground_tool():
    try:
        iface = qgis.utils.iface
        global playground_dialog
        playground_dialog = SimplePlaygroundTool(iface)
        playground_dialog.show()
        print("🏞️ Playground Accessibility Tool started successfully!")
        return playground_dialog
    except Exception as e:
        print(f"❌ Error starting tool: {str(e)}")
        return None

if __name__ == '__main__':
    run_playground_tool()
else:
    print("🏞️ Playground Accessibility Tool loaded!")
    run_playground_tool()