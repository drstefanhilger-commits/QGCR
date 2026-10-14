## Environment
- Windows 11  
- WSL2 + WSLg  
- Ubuntu 24.04 (noble)  
- Python 3.12  
- Intel UHD 770  
- Mesa 25.x (OpenGL ueber WSLg, ggf. `GALLIUM_DRIVER=d3d12`)  
- Gazebo Harmonic (gz-sim 8.x)
- PX4 v1.17.0 (`~/PX4-Autopilot`, ueberschreibbar mit `PX4_DIR`)  
- pymavlink 2.4.50 (bitte diese Signaturen in pymavlink verwenden)
- MAVSDK 3.15.3  
	
## Vereinbarungen fuer QGC-Replacement
- Nur Gazebo Harmonic benutzen 
- px4 <=> gazebo
#0	18570	14550	QGroundControl
#1	14580	14540	Onboard link	(irrelevant fuer dieses Projekt)
#2	14280	14030	Onboard link	(irrelevant fuer dieses Projekt)
#3	13030	13280	Gimbal			  (irrelevant fuer dieses Projekt)
- Diese Ports wurden mit QGC getsetet und geflogen (Keine Analyse des Ports #0 mehr!)
- Verbindung QGCReplacement immer mit udp://0.0.0.0:14550
- starte px4_silt mit "make px4_sitl gz_rc_cessna"
- VS Code statt nano  
- Pfad B (ganze Dateien)  
- `cat << 'EOF' > datei`  
- `mkdir -p` falls Ordner fehlt  
- `chmod +x` bei Skripten  
- Punkte einzeln, auf ok warten  
- Aenderungen an der Architektur muessen immer erlaubt werden
- Immer um aktuelle Dateien fragen, wenn diese nicht bekannt sind
- Base
-- Niemals _on_enter(), _on_during() und _on_exit() aufrufen aber immer ueberschreiben
-- Immer on_update() aufrufen aber nie ueberschreiben 
- Namens-Schema fuer Unittests "test_<ordner>_<dateiname>.py"
- if/else auf switch/case umstellen, wenn mehr als zwei Verzweigungen
- ## Environment und ## Vereinbarung bei Punkt 1 zeigen