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
#3	13030	13280	Gimbal			(irrelevant fuer dieses Projekt)
- Diese Ports wurden mit QGC getsetet und geflogen (Keine Analyse dieser Port mehr!)
- Immer Port #0, keine anderen
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
- Niemals _on_enter(), _on_during() und _on_exit() aufrufen aber immer ueberschreiben
- Niemals on_update() aufrufen. 
- Namens-Schema fuer Unittests "test_<ordner>_<dateiname>.py"
- if/else auf switch/case umstellen, wenn mehr als zwei Verzweigungen
- ## Environment und ## Vereinbarung bei Punkt 1 zeigen



# Setup Ubuntu 24.04

Ubuntu 24.04 verbietet `pip install` ins System-Python (PEP 668), daher venv verwenden.

Nur eine QGCR-Instanz: läuft bereits eine (`python3 -m QGCR.main`), bricht eine zweite mit
„QGCR läuft bereits (PID …)“ ab – ihre Startup-Bereinigung würde sonst die laufende QGCR samt PX4 beenden.

Beenden: Fenster schließen (X) oder Strg+C im Terminal – QGCR beendet dabei das von ihm gestartete
PX4/Gazebo. PX4 erhält eine eigene stdin-Pipe, damit die PX4-Shell das Terminal nicht übernimmt.
`tkinter` ist unter 24.04 nicht vorinstalliert.

```bash
sudo apt install python3-tk python3-venv lsof
cd ~/projects
python3 -m venv .venv
source .venv/bin/activate
pip install -r QGCR/requirements.txt
```

Start (aus `~/projects`, da alle Imports `QGCR.*` sind):

```bash
python3 -m QGCR.main
```

Modell wählen (Standard `gz_rc_cessna`), z. B. die FSL Rocket VTOL:

```bash
python3 -m QGCR.main --model gz_fsl_rocket_vtol
```

Im Betrieb kann das Modell im HomeTab (Auswahlliste „Modell“) gewechselt werden: QGCR löst RESET aus,
beendet PX4 und startet es in STARTUP mit dem neuen Modell neu. Im Flug (AIRBORNE) und während RESET
ist die Auswahl gesperrt. Erlaubte Modelle: `Model.ALLOWED_MODELS`.

PX4 liegt standardmaessig unter `~/PX4-Autopilot`, sonst `export PX4_DIR=/pfad/zu/PX4-Autopilot`.

Tests (aus `~/projects`):

```bash
python3 -m unittest discover -s QGCR/test/unittest -t . -v
```

```bash
python3 -m pytest QGCR/test/pytest
```

PX4-SITL-Tests (`test_px4_*.py`) starten PX4 + Gazebo headless und laufen nur mit `QGCR_SITL=1`.
Läuft bereits eine QGCR-, PX4- oder Gazebo-Sitzung, brechen sie mit einer Meldung ab, statt sie zu beenden:

```bash
QGCR_SITL=1 python3 -m unittest discover -s QGCR/test/unittest -t . -p "test_px4_*.py" -v
```

`test/Obsolete/` enthaelt Tests gegen nicht mehr existierende Module/APIs (werden nicht ausgefuehrt).

# PX4 SITL GUI (alt)

python3 -m unittest discover gui_alt/test -v

---

# 🧭 Architekturübersicht

QGCR ist eine Tkinter-Bodenstation für PX4-SITL (Gazebo Harmonic). Der Systemzustand wird von
High-Level-FSMs (HFSMs) gesteuert, die ein zentraler `MainController` tickt. GUI, Zustandslogik und
MAVLink-Kommunikation laufen in getrennten Threads und tauschen Daten nur über das `Model` aus.

**Single-Writer:** Den Flugzustand im Model ändert nur der Update-Thread. Der RX-Thread liest
MAVLink nur und legt die Nachrichten in eine Queue; der Update-Thread verteilt sie über
`connection.process_pending()` an Model und Dispatcher, bevor er die HFSM tickt. Die GUI liest das
Model und schreibt nur Events (`hfsm_events`), `active_tab` und Eingaben wie Upload-Items/Modellwahl.

```
PX4-SITL ──UDP 18570 → 14550──► Connection (udp:0.0.0.0:14550)
                                 ├─ RX-Thread: recv → Empfangs-Queue (sonst nichts)
                                 └─ GCS-Heartbeat-Thread (1 Hz) → PX4

Update-Thread (20 Hz):  connection.process_pending()
                          HEARTBEAT / GLOBAL_POSITION_INT / HOME_POSITION / COMMAND_ACK → Model
                          STATUSTEXT → PX4-Log,  alle übrigen (+ COMMAND_ACK) → Dispatcher → MicroServices
                        → model.check_timeout() → MicroServiceController.tick() → MainController.on_update()
Tk-Mainloop (GUI):      Buttons → GUIController.handle_button_event() → model.hfsm_events
                        gui_tick (500 ms): Log-Queues → LogTab,  Model → StatusBar
```

---

# 🏗️ Systemkomponenten

| Komponente | Datei | Aufgabe |
|---|---|---|
| `QueueRegistry` | `core/queue_registry.py` | System-Queues `telemetry`, `fsm`, `mission`, `gui` (Ring-Buffer, max. 500 Einträge, von `gui_tick` geleert) + Log-Queues `px4_log_queue`, `sim_log_queue`, `qgcr_log_queue` |
| `Model` | `model/model.py` | Zentrale Datenhaltung (siehe unten) |
| `LogRouter` | `logging/log_router.py` | `model.log.px4(id, text)`, `.sim(src, text)`, `.qgcr(text)` → Log-Queues |
| `Connection` | `communication/connection.py` | MAVLink über Port #0, RX- und GCS-Heartbeat-Thread |
| `Dispatcher` | `communication/dispatcher.py` | Verteilt Nachrichten an `on_message(msg_type, msg)` der MicroServices |
| `MicroServiceController` | `controller/microservice_controller.py` | Erzeugt und tickt die MicroServices |
| `MainController` | `controller/main_controller.py` | Tickt die aktive HFSM, wechselt HFSMs (kein FSM) |
| `GUIController` | `controller/gui_controller.py` | Vermittelt zwischen GUI, Model und MainWindow |
| `GazeboMarkers` | `sim/gazebo_markers.py` | Start- (grün) und Landepunkt (rot) als visuelle Modelle `qgcr_start` / `qgcr_landing` in Gazebo (Scheibe + 4-m-Mast, keine Kollision); eigener Worker-Thread, `gz service /world/default/create|remove` |
| `PX4SwarmStarter` | `sim/px4_swarm_starter.py` | Startet/stoppt PX4-SITL-Instanzen (`make px4_sitl gz_<modell>`); stdout+stderr zusammen → PX4-Log |
| `StartupCleanup` | `core/startup_cleanup.py` | Beendet PX4-/Gazebo-Reste, gibt Ports frei, löscht Gazebo-SHM |

## Model

```python
Model(queue_registry)
```

- **Heartbeat:** `px4_connected`, `px4_heartbeat_count`, `px4_last_heartbeat`;
  `check_timeout()` setzt `px4_connected=False` nach `HEARTBEAT_TIMEOUT` (8 s) und 2 Fehlversuchen
  (es gibt keinen separaten HeartbeatMonitor)
- **Fahrzeug:** `px4_mode` (z. B. `AUTO.LAND`; Haupt-/Untermodus aus `custom_mode` Bits 16-23 / 24-31), `px4_armed`, `ready_to_arm`, `vehicle_lat/lon/alt`, `home_lat/lon/alt`
- **Mission:** `mission` (`MissionData`: `items`, `count`, `ready`), `clear_mission()`, `add_mission_item()`
- **HFSM:** `hfsm_events` (deque, GUI → HFSM), `hfsm_main`, `hfsm_sub`, `push_state_update()`
- **MicroServices:** `services` (Container mit `_NullService`-Platzhaltern) und Aliase
  `takeoff`, `home_ms`, `mission_ms`, `upload_ms`, `reset`
- Telemetrie-, Status- und State-Updates gehen als Tupel in die `gui`-Queue, z. B. `("status", text)`

## Connection + Dispatcher

```python
dispatcher = Dispatcher(model)
connection = Connection(model, dispatcher)
connection.connect()          # bindet udp:0.0.0.0:14550, startet die Threads
```

Der Dispatcher ruft `on_message(msg_type, msg)` auf `model.mission_ms`, `upload_ms`, `home_ms`,
`takeoff` und `param_sync` auf, sofern vorhanden. Fehler eines Services stoppen die anderen nicht.

## MicroServices

Nicht-blockierend mit `start()` / `tick()` / `on_message()` und den Flags `done` / `error`:

| Model-Attribut | Klasse | Datei |
|---|---|---|
| `model.takeoff` | `TakeoffMicroService` | `microservices/takeoff_ms.py` |
| `model.upload_ms` | `UploadMicroService` | `microservices/upload_ms.py` |
| `model.home_ms` | `HomeMicroService` | `microservices/home_ms.py` |
| `model.reset` | `ResetMicroService` | `microservices/reset_microservice.py` |

Zusätzlich erzeugt der Connect-Thread nach dem ersten PX4-Heartbeat einen synchronen
`MissionMicroService` (`communication/microservices/mission_microservice.py`, `upload()` / `download()`)
als `model.mission_ms` (= `model.services.mission`). `model.mission` bleibt immer die `MissionData`.
Der Service liest **nicht** selbst von der Verbindung: Mission-Nachrichten kommen über den Dispatcher
(`on_message`) in eine Queue, `upload()` / `download()` warten darauf (Timeout je Nachricht).
Beide blockieren und dürfen nicht aus dem RX-Thread aufgerufen werden. Abbruch über ein `threading.Event`
(`cancel=`) je Transfer: PX4 erhält `MISSION_ACK` (`MAV_MISSION_OPERATION_CANCELLED`), `last_error` = `"Abgebrochen"`.
Grundregel: Nur der RX-Thread der Connection ruft `recv_match()` auf.

---

# 🧩 FSM-Architektur

## Basisklassen

| Klasse | Datei | Rolle |
|---|---|---|
| `Base` | `states/base.py` | Lifecycle: `on_update()` ruft `_on_enter()` einmal, dann `_on_during()`, dann `_on_exit()` → nächster Zustand |
| `BaseFSM` | `states/base_fsm.py` | Basis der Sub-FSMs |
| `BaseHFSM` | `states/base_hfsm.py` | Basis der HFSMs, setzt `model.hfsm_main` |

Regeln: `on_update()` darf nicht überschrieben werden (wird von `Base` erzwungen).
`_on_during()` sammelt nur Informationen, Zustandswechsel entscheidet ausschließlich `_on_exit()`.

## MainController

```python
MainController(model, MAIN_STATE_MAP)   # states/main_state_map.py
```

- startet in `STARTUP`, tickt pro `on_update()` genau die aktive HFSM
- erzeugt bei jedem Wechsel eine **neue** HFSM-Instanz
- globale Events vor jedem Tick (gesucht wird in der ganzen Queue, nicht nur im ersten Element):
  `TAKEOFF_DONE` → AIRBORNE, `RESET` → RESET (außer in AIRBORNE:
  dort landet die AirborneHFSM zuerst),
  `RESET_DONE` bzw. `model.reset_done` → STARTUP
- beim Wechsel nach READY verwirft er alte `hfsm_events` – bevor `hfsm_main = READY` sichtbar wird,
  damit ein direkt danach geklicktes TAKEOFF nicht verloren geht

## High-Level-FSMs (`MainState`)

| Zustand | Klasse | Verhalten |
|---|---|---|
| `STARTUP` | `StartupHFSM` | Enter: `PX4SwarmStarter(model.vehicle_configs).start_all()` (oder vorhandenen `model.startup_controller` wiederverwenden). → `READY`, sobald `connection_ready()` und `heartbeat_ok()` |
| `READY` | `ReadyHFSM` | Tickt `model.takeoff`. `TAKEOFF` → AIRBORNE, `RESET` → RESET, Mission-Tab aktiv (`model.active_tab`) → MISSION, `ARM` / `DISARM` → `MAV_CMD_COMPONENT_ARM_DISARM` über `model.connection` (bleibt READY). Nach 5 s Schonfrist: Verbindung verloren → RESET |
| `AIRBORNE` | `AirborneHFSM` | Enter: `model.takeoff.start()`, falls IDLE (TAKEOFF: `NAV_TAKEOFF` mit `param7` = Home-Höhe AMSL + 10 m, Position = aktuelle bzw. NaN; ohne bekannte Home-Höhe kein ARM). Tickt `model.takeoff`. `LAND` → `MAV_CMD_NAV_LAND` an der aktuellen Position (`hfsm_sub` LAND, PX4 AUTO.LAND); nach dem Aufsetzen disarmt PX4 → Takeoff-Service `reset()` → READY. `MISSION_START` (HomeTab „MISSION“) → AUTO.MISSION im Flug (`hfsm_sub` MISSION). Läuft eine Mission (auch vom Boden gestartet), startet AIRBORNE keinen eigenen Takeoff; endet sie mit Landung (PX4 disarmt) → READY. `RESET` im Flug: erst landen (NAV_LAND, `hfsm_sub` RESET_LAND), nach Landung + Disarm → RESET; nicht armed / kein PX4-Ziel → sofort; zweiter RESET während der Landung → sofort. Verbindung verloren → RESET |
| `MISSION` | `MissionHFSM` | `MISSION_UPLOAD` / `MISSION_DOWNLOAD` im Worker-Thread (`hfsm_sub` UPLOAD / DOWNLOAD / IDLE), `MISSION_STOP` bricht den laufenden Transfer ab (Mission im Model bleibt). `MISSION_START` (Button „Start“) → `MAV_CMD_MISSION_START` (PX4 armt + AUTO.MISSION, `hfsm_sub` START); sobald armed und AUTO.MISSION → AIRBORNE mit `model.mission_running`, sonst nach 10 s Statusmeldung. Home-Tab aktiv → READY (nach laufendem Transfer), `RESET` → RESET, Verbindung verloren → RESET |
| `RESET` | `ResetHFSM` | Enter: Takeoff zurücksetzen, PX4 stoppen (`startup_controller.stop_all()`), Backup, PX4-rootfs + `/tmp/px4-*`, `/tmp/gz-*` löschen, Heartbeat-Status verwerfen (`model.reset_heartbeat()`), `reset_done=True` → STARTUP |
| `INTERCEPT` | `InterceptHFSM` | Tab „FSL“ (kontrollierte FSL-Drohne, siehe unten). IDLE → `INTERCEPT_TRIGGER` → Wartepunkt planen → UPLOAD → START → FLIGHT → (Timeout / Akku / `INTERCEPT_ABORT` → RTL) → gelandet → IDLE. Neue Trigger außerhalb von IDLE werden verworfen. Tab verlassen → READY (im Flug erst nach der Landung). RESET im Flug: erst RTL + Landung |
| `LOST` | `LostHFSM` | Platzhalter, bleibt in LOST (wird derzeit nicht angesteuert) |

```
                     Mission-Tab
                   ┌────────────► MISSION
                   │   Home-Tab      │
STARTUP ──HB──► READY ◄──────────────┤
   ▲               │ TAKEOFF         │
   │               ▼                 │
   │           AIRBORNE              │
   │               │                 │
   │      RESET / Verbindung verloren (aus READY, AIRBORNE, MISSION)
   └── reset_done ── RESET ◄─────────┘
```

## Sub-FSMs

Die HFSMs arbeiten ohne Sub-FSMs (`hfsm_sub` ist nur eine Anzeige wie `IDLE`, `LAND`, `UPLOAD`).
Die früheren Sub-FSMs samt `*_substate.py` / `*_state_map.py` liegen unter `Obsolete/states/`.

---

# 🎯 Kontrollierte FSL-Drohne (Tab „FSL“)

Modell `gz_fsl_rocket_vtol` (Multicopter-Betrieb). Solange der Tab aktiv ist (HFSM `INTERCEPT`),
sind die HomeTab-Buttons und die Modellauswahl gesperrt; mit anderem Modell bietet der Tab
„Modell auf FSL umstellen“ an.

- **Trigger (simuliert):** ID, Position Ost/Nord/Höhe [m] relativ zum FSL-Startpunkt,
  Geschwindigkeit Ost/Nord/Vertikal [m/s]; Zeitstempel = Absenden. Geschwindigkeit kurzfristig konstant.
- **Wartepunkt** (`model/intercept.py`): frühester Punkt auf der geschätzten Bahn, den die FSL erreicht,
  während der Trigger noch mindestens 10 m davor ist. Keine Entfernungsgrenze (der 200-m-Kreis im
  Plot dient nur der Orientierung). Höhe = Höhe der Trigger-Bahn dort, mindestens 10 m.
  Zeitmodell der FSL (SITL gemessen): 3 s Vorbereitung + 16 s bis Horizontalflug + Strecke /
  (8 m/s × 0,92) + 4 s Abbremsen.
- **Mission:** Takeoff 10 m → `DO_CHANGE_SPEED` → Wartepunkt → ggf. `NAV_LOITER_TIME` → 10 s entlang der
  Trigger-Bahn → `NAV_LAND` am Startpunkt. Start per `MAV_CMD_MISSION_START`.
- **Überwachung:** Timeout (Default 180 s ab Start) oder Akku < Minimum (Default 30 %,
  `SYS_STATUS.battery_remaining`) bzw. „Abbrechen“ → RTL (`MAV_CMD_NAV_RETURN_TO_LAUNCH`).
  SITL: die simulierte Batterie fällt im Flug nur bis `SIM_BAT_MIN_PCT` (PX4-Default 50 %) und wird
  am Boden wieder voll – mit dem Default-Minimum 30 % löst die Überwachung in SITL daher nie aus.
  Der SITL-Test `test_low_battery_triggers_rtl` setzt `SIM_BAT_MIN_PCT` vorübergehend auf 10 %
  (PX4 speichert Parameter dauerhaft; der Test setzt sie wieder auf 50 % zurück).
- **Abstand Trigger–FSL:** laufend in der Statuszeile (3D und horizontal) und im 2D-Plot als
  gestrichelte Linie zwischen Trigger-Symbol und FSL-Position.
- **Anzeige:** 2D-Plot mit 200-m-Kreis, Trigger-Bahn (lila) und Wartepunkt (gelbe Raute);
  Gazebo: Start, Landung, Trigger-Bahn (lila Stab in Flughöhe) und Wartepunkt (gelbe Kugel).
  Beispiel: `docs/fsl_tab_intercept.png`

---

# 🖥️ GUI-Architektur

```python
GUIController(model, state_machine=main_controller, main_window, queue_registry)
MainWindow(parent=root, controller=gui_controller, queue_registry=queue_registry)
```

- `MainWindow` (ttk.Frame): Notebook mit `HomeTab`, `MissionTab`, `FslTab`, `LogTab` + `StatusBar`
- HomeTab-2D-Plot (`view/plot_2d.py`): Draufsicht in Metern (Nord oben, Maßstab automatisch) mit
  Missions-Track (blau, aufgezeichnet solange `model.mission_running`, ab 1 m Abstand, max. 10 000 Punkte),
  geplanten Wegpunkten (grau gestrichelt), Startpunkt (grünes Dreieck = Position beim Missionsstart),
  Landepunkt (rotes ⊗ = `NAV_LAND`/`NAV_VTOL_LAND` der Mission) und aktueller Position (orange).
  Der Track bleibt nach der Landung sichtbar, bis die nächste Mission startet oder „Track löschen“
  (HomeTab) gedrückt wird.
- Höhen-Plot (`view/plot_alt.py`) unter dem 2D-Plot: Höhe über Home [m] über der Zeit seit
  Missionsstart [s] (`model.mission_alt_track`, höchstens alle 0,5 s ein Punkt), aktueller Wert oben rechts.
  Beispiel: `docs/home_tab_plots_vtol_mission.png`
  Beispiel: `docs/plot_2d_vtol_mission.png` (fsl_rocket_vtol, SITL)
- Gazebo: dieselben Start-/Landepunkte (`model.mission_markers()`) setzt `GazeboMarkers` in die Welt
  (lat/lon → ENU um `<spherical_coordinates>` der World-SDF). Nach RESET/Modellwechsel (neue
  Gazebo-Instanz, STARTUP) werden sie neu platziert; fehlgeschlagene Versuche alle 2 s wiederholt.
- Buttons rufen `GUIController.handle_button_event(name)` auf; erlaubte Events
  (`VALID_BUTTON_EVENTS`): `ARM`, `DISARM`, `TAKEOFF`, `LAND`, `MISSION_START`, `MISSION_UPLOAD`,
  `MISSION_DOWNLOAD`, `MISSION_VALIDATE`, `MISSION_STOP`, `RESET`, `STOP` → `model.hfsm_events`
- `gui_tick()` (alle 500 ms): PX4-/Sim-/QGCR-Logs → `LogTab`, Model → `StatusBar`
  (HFSM, Sub-State, Mode, Armed, Heartbeat-Zähler, Spinner)
- `gui`-Queue (`process_gui_queue()` in `gui_tick`): `("status", text)` → letzte Meldung rechts in der
  `StatusBar` + `[STATUS] text` im QGCR-Log, `("log", text)` → QGCR-Log; Telemetrie/State-Updates werden
  verworfen (direkt aus dem Model gelesen)
- Tab-Wechsel (`<<NotebookTabChanged>>`) → `GUIController.on_tab_changed()` → `model.active_tab`.
  READY / MISSION werten `active_tab` zustandsbasiert aus (kein Event, das verloren gehen kann).
- MissionTab: Upload öffnet einen Datei-Dialog (QGC `.plan`, `model/mission_parser.py`) →
  `model.mission_upload_items` → `MISSION_UPLOAD`; Download → `MISSION_DOWNLOAD`; Stop → `MISSION_STOP`;
  Start → `MISSION_START` (nur in MISSION/IDLE mit Mission im Model). Die Mission muss eine Landung
  enthalten (PX4 `MIS_TKO_LAND_REQ = 2` für Fixed-Wing und VTOL).
  Bekannt (PX4-seitig, SITL): `gz_rc_cessna` bricht die Missionslandung mit Landemuster ab
  („Holding at .. m above landing waypoint“) und kreist; dann mit LAND landen. `gz_fsl_rocket_vtol`
  landet die Mission selbst.
  `gui_tick` aktiviert Upload/Download nur in MISSION/IDLE, Stop nur während eines Transfers, und zeigt
  Home, Wegpunkte und `model.mission_status`

---

# 🚀 Initialisierungsreihenfolge (`main.py`, `Application.__init__`)

1. `StartupCleanup.run_full_cleanup()`
2. `root = tk.Tk()`
3. `queue_registry = QueueRegistry()`, `model = Model(queue_registry)`
4. `model.vehicle_configs = [PX4InstanceConfig(px4_dir=$PX4_DIR, model_name=--model, instance_id=1)]`
5. `model.log = LogRouter(model, queue_registry)`
6. `dispatcher = Dispatcher(model)`, `connection = Connection(model, dispatcher)`, `model.connection = connection`
7. MicroServices + `MicroServiceController(model)`
8. `main_controller = MainController(model, MAIN_STATE_MAP)`
9. `gui_controller = GUIController(...)`, `window = MainWindow(...)`, GUI-Tick starten
10. Threads: Update-Loop (20 Hz) und Connect-Loop (`connection.connect()`, auf Heartbeat warten,
    `model.mission_ms = MissionMicroService(...)`)
11. `root.mainloop()`

---

# 📁 Altbestand (`Obsolete/`)

Module, die von `main.py` aus nicht erreichbar waren, liegen mit unveränderter Ordnerstruktur unter
`Obsolete/` (z. B. `Obsolete/states/ready/subfsms/`). Sie werden nicht importiert und nicht getestet;
ihre Imports zeigen noch auf die alten Pfade. Zurückholen: `git mv Obsolete/<pfad> <pfad>`.

- `Obsolete/states/`: Sub-FSMs, Substates, State-Maps, alte State-Machine-Basisklassen
- `Obsolete/communication/`: `heartbeat_monitor.py`, `qgc_*.py`, alte `microservices/*`
- `Obsolete/core/states/`, `Obsolete/sim/startup.py`, `Obsolete/model/qgc_model_router.py`
- `Obsolete/view/`: `gis/` (tkintermapview), `gui_event_loop.py`, `gui_interface.py`, `button_policy.py`,
  `telemetry_view.py`, `tab_router.py`

Zugehörige Tests und Harness-Skripte liegen in `test/Obsolete/`.

---


<!--
QGC‑kompatibler Mission‑Upload – Zusammenfassung

Diese Software implementiert den MAVLink‑Mission‑Upload exakt nach dem Verhalten
von QGroundControl (QGC). Die wichtigsten technischen Erkenntnisse:

1. QGC verwendet immer eine bidirektionale UDP‑Verbindung:
   udp://0.0.0.0:14550
   Dadurch kann der Client sowohl an PX4 senden als auch alle MAVLink‑Nachrichten
   empfangen. Varianten wie "udpout:" sind send‑only und führen zu Timeouts.

2. Der Client muss an Port 14550 gebunden sein:
   udp:0.0.0.0:14550
   Nur so empfängt er PX4‑Heartbeats und MISSION_REQUEST‑Nachrichten.
   udp:127.0.0.1:14550 bindet NICHT an den Port und empfängt daher nichts.

3. QGC sendet kontinuierlich GCS‑Heartbeats (1 Hz).
   Ohne diesen Heartbeat meldet PX4 „No connection to the ground control station“,
   akzeptiert aber dennoch Mission‑Uploads. Der Heartbeat ist für korrekte
   MAVLink‑Kommunikation jedoch essenziell.

4. QGC wartet immer auf den PX4‑Heartbeat, bevor es Missionen hochlädt.
   Erst nach Empfang eines Heartbeats (sysid=1, compid=1) werden die Ziel‑IDs
   korrekt gesetzt. Ohne diesen Schritt sendet der Client an falsche IDs.

5. Der Commander‑Modus ist für den Mission‑Upload irrelevant.
   QGC setzt keinen Flugmodus vor dem Upload. Missionen können in jedem Zustand
   übertragen werden (DISARMED, MANUAL, HOLD, FAILSAFE usw.).

6. QGC‑Mission‑Upload‑Sequenz:
   - GCS → MISSION_COUNT
   - PX4 → MISSION_REQUEST(seq=0)
   - GCS → MISSION_ITEM_INT(seq=0)
   - PX4 → MISSION_REQUEST(seq=1)
   - GCS → MISSION_ITEM_INT(seq=1)
   - …
   - PX4 → MISSION_ACK(ACCEPTED)

   Wichtig: PX4 sendet das ACK nur einmal, am Ende. QGC wartet nicht nach jedem
   Item auf ein ACK.

7. Häufige Fehlerursachen:
   - Verwendung von udpout (keine Antworten)
   - falscher Bind‑Port
   - falsche Ziel‑IDs (0/0 statt 1/1)
   - ACK an falscher Stelle erwartet
   - Heartbeat und Upload getrennt implementiert

Die aktuelle Implementierung löst diese Probleme, indem sie:
- einen GCS‑Heartbeat‑Thread startet,
- auf den PX4‑Heartbeat wartet,
- target_system/target_component korrekt setzt,
- den Mission‑Upload exakt nach QGC‑Sequenz durchführt,
- alle MAVLink‑Nachrichten sichtbar macht.

Damit ist der Mission‑Upload vollständig QGC‑kompatibel und robust.
-->
