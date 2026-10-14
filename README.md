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

PX4 liegt standardmaessig unter `~/PX4-Autopilot`, sonst `export PX4_DIR=/pfad/zu/PX4-Autopilot`.

Tests (aus `~/projects`):

```bash
python3 -m unittest discover -s QGCR/test/unittest -t . -v
```

```bash
python3 -m pytest QGCR/test/pytest
```

PX4-SITL-Tests (`test_px4_*.py`) starten PX4 + Gazebo headless und laufen nur mit `QGCR_SITL=1`:

```bash
QGCR_SITL=1 python3 -m unittest discover -s QGCR/test/unittest -t . -p "test_px4_*.py" -v
```

`test/Obsolete/` enthaelt Tests gegen nicht mehr existierende Module/APIs (werden nicht ausgefuehrt).

# PX4 SITL GUI (alt)

python3 -m unittest discover gui_alt/test -v

---

# 🧭 Architekturübersicht

Dieses Projekt implementiert eine modulare, hierarchische Zustandsmaschinen‑Architektur (HFSM) für die Steuerung eines UAV‑SITL‑Setups.  
Die GUI, die FSMs und die Kommunikationsschicht sind klar voneinander getrennt und folgen einer deterministischen Initialisierungsreihenfolge.

---

# 🏗️ Systemkomponenten

## 1. **Model**
Zentrale Datenhaltung der Anwendung.  
Enthält u. a.:

- Missionsdaten  
- MAVLink‑Kommandos  
- Parser  
- Zustandsvariablen  

Das Model ist **zustandslos gegenüber der FSM‑Architektur** und wird von allen FSMs gemeinsam genutzt.

---

## 2. **HeartbeatMonitor**
Ein einfacher Timer‑basierter Monitor, der Heartbeat‑Timeouts erkennt.

- besitzt **keine** Abhängigkeiten  
- wird von der Connection genutzt  
- erzeugt Events wie „PX4_LOST“ oder „GCS_LOST“

Signatur:

```python
HeartbeatMonitor(timeout_s=2.0)
```

---

## 3. **Connection (EventRouter)**
Die zentrale Kommunikationsschicht zwischen:

- GUI  
- FSMs  
- HeartbeatMonitor  
- MainStateMachine  

Aufgaben:

- Weiterleitung eingehender Events  
- Routing von Heartbeat‑Signalen  
- Bereitstellung einer einheitlichen Connection‑API für alle Sub‑FSMs  

Signatur:

```python
EventRouter(model, heartbeat_monitor)
```

---

## 4. **MainStateMachine**
Globale System‑FSM, die den Gesamtzustand des Systems abbildet.

- nutzt `model`  
- nutzt `connection`  
- wird von allen Sub‑FSMs referenziert  

Signatur:

```python
MainStateMachine(model, connection)
```

---

# 🧩 FSM‑Architektur

Das System besteht aus vier High‑Level‑FSMs (HFSMs):

1. **StartupHFSM**
2. **ReadyHFSM**
3. **TakeoffHFSM**
4. **MissionHFSM**

Jede HFSM ist **komplett unabhängig** und wird vom Dispatcher verwaltet.

---

## 4.1 StartupHFSM

Hierarchische FSM mit drei Sub‑FSMs:

- `StartupInitFSM`
- `StartupWaitFSM`
- `StartupReadyFSM`

Jede Sub‑FSM hat die Signatur:

```python
SubFSM(model, system_sm, connection)
```

StartupHFSM selbst ist eine reine Kompositions‑FSM:

```python
StartupHFSM(init_fsm, wait_fsm, ready_fsm)
```

---

## 4.2 ReadyHFSM

Die Ready‑FSM ist **eigenständig** und besitzt **keine Sub‑FSMs mit Model/Connection**.

Sie besteht aus zwei internen Substates:

- `IDLE`
- `ARMED`

Signatur:

```python
ReadyHFSM()
```

---

## 4.3 TakeoffHFSM

Besteht aus zwei Sub‑FSMs:

- `TakeoffActiveFSM`
- `TakeoffExitFSM`

Beide Sub‑FSMs haben die Signatur:

```python
SubFSM(model, system_sm, connection)
```

HFSM‑Signatur:

```python
TakeoffHFSM(active_fsm, exit_fsm)
```

---

## 4.4 MissionHFSM

Besteht aus einer Sub‑FSM:

- `MissionStateMachine`

Signatur:

```python
MissionStateMachine(model, system_sm, connection)
MissionHFSM(mission_subfsm)
```

---

# 🔀 Dispatcher

Der Dispatcher hält Referenzen auf **alle vier HFSMs** und entscheidet:

- welche FSM aktiv ist  
- welche FSM Heartbeat‑Events erhält  
- welche FSM Default‑Events (z. B. MAVLink‑Messages) erhält  

Signatur:

```python
Dispatcher(startup_sm, ready_sm, takeoff_sm, mission_sm)
```

---

# 🖥️ GUI‑Architektur

Die GUI besteht aus:

- `MainWindow`  
- `GUIController`  
- `MissionTab`  
- weiteren modularen GUI‑Elementen  

Der GUIController verbindet:

- Model  
- aktive FSM (initial: ReadyHFSM)  
- Dispatcher  

Signatur:

```python
GUIController(model, active_fsm, dispatcher)
```

---

# 🚀 Initialisierungsreihenfolge (wichtig!)

Die Reihenfolge ist **zwingend**, da jede Schicht die darunterliegende benötigt:

1. `model = Model()`
2. `heartbeat_monitor = HeartbeatMonitor()`
3. `connection = EventRouter(model, heartbeat_monitor)`
4. `system_sm = MainStateMachine(model, connection)`
5. Sub‑FSMs erzeugen (Startup, Takeoff, Mission)
6. HFSMs zusammensetzen
7. `ready_sm = ReadyHFSM()`
8. `dispatcher = Dispatcher(...)`
9. `controller = GUIController(model, ready_sm, dispatcher)`
10. `MainWindow(controller).mainloop()`

---

# 📌 Zusammenfassung

Diese Architektur trennt:

- **Kommunikation**
- **Systemzustand**
- **High‑Level‑FSMs**
- **Sub‑FSMs**
- **GUI‑Logik**

klar voneinander und ermöglicht:

- deterministische Abläufe  
- saubere Testbarkeit  
- modulare Erweiterbarkeit  
- robuste Fehlerbehandlung  

---


Die neue Architektur ist:

Ebene	Typ	Vererbung	Input	Output
Sub‑FSM	INIT, WAIT, READY, IDLE, ARMED, ACTIVE, EXIT, MISSION_IDLE	BaseFSM	(msg_type, msg)	Events → model.event_queue
HFSM	StartupHFSM, ReadyHFSM, TakeoffHFSM, MissionHFSM	keine Vererbung	Events aus model.event_queue	Sub‑FSM‑Wechsel




GUI                  Model.queue_state          BaseMachineController          StartupHFSM                StartupSubFSMs
 |                           |                           |                           |                           |
 |--- (User opens GUI) ----->|                           |                           |                           |
 |                           |                           |                           |                           |
 |--- GUI_TAKEOFF_BUTTON --->|                           |                           |                           |
 |                           |--- Event(GUI_TAKEOFF) --->|                           |                           |
 |                           |                           |--- process_event() ------>|                           |
 |                           |                           |                           |--- handle_event() ------->|
 |                           |                           |                           |   (ignored in STARTUP)    |
 |                           |                           |                           |<--------------------------|
 |                           |                           |<-- remains STARTUP -------|                           |
 |                           |                           |                           |                           |
 |                           |                           |--- step() --------------->|                           |
 |                           |                           |                           |--- on_update() ---------->|
 |                           |                           |                           |   (calls subcontroller)   |
 |                           |                           |                           |                           |
 |                           |                           |                           |--- sub.step() ----------->|
 |                           |                           |                           |                           |
 |                           |                           |                           |<-- SubState.HEARTBEAT ----|
 |                           |                           |<-- MainState.STARTUP ---|                           |
 |                           |                           |                           |                           |
 |                           |                           |                           |                           |
PX4 Thread                   |                           |                           |                           |
 |--- PX4_HEARTBEAT -------->|                           |                           |                           |
 |                           |--- Event(PX4_HEARTBEAT) ->|                           |                           |
 |                           |                           |--- process_event() ------>|                           |
 |                           |                           |                           |--- handle_event() ------->|
 |                           |                           |                           |   sub.inject_event()      |
 |                           |                           |                           |                           |
 |                           |                           |                           |--- sub.handle_event() --->|
 |                           |                           |                           |   returns STARTUP_PARAMS  |
 |                           |                           |                           |<--------------------------|
 |                           |                           |<-- remains STARTUP -------|                           |
 |                           |                           |                           |                           |
 |                           |                           |--- step() --------------->|                           |
 |                           |                           |                           |--- on_update() ---------->|
 |                           |                           |                           |   sees substate=PARAMS    |
 |                           |                           |                           |                           |
 |                           |                           |<-- MainState.STARTUP ---|                           |
 |                           |                           |                           |                           |
 |                           |                           |                           |                           |
PX4 Thread                   |                           |                           |                           |
 |--- PX4_PARAM_SYNC_DONE -->|                           |                           |                           |
 |                           |--- Event(PARAM_SYNC) ---->|                           |                           |
 |                           |                           |--- process_event() ------>|                           |
 |                           |                           |                           |--- handle_event() ------->|
 |                           |                           |                           |   sub.inject_event()      |
 |                           |                           |                           |                           |
 |                           |                           |                           |--- sub.handle_event() --->|
 |                           |                           |                           |   returns STARTUP_HOME    |
 |                           |                           |                           |<--------------------------|
 |                           |                           |<-- remains STARTUP -------|                           |
 |                           |                           |                           |                           |
 |                           |                           |--- step() --------------->|                           |
 |                           |                           |                           |--- on_update() ---------->|
 |                           |                           |                           |   sees substate=HOME      |
 |                           |                           |                           |                           |
 |                           |                           |<-- MainState.STARTUP ---|                           |
 |                           |                           |                           |                           |
PX4 Thread                   |                           |                           |                           |
 |--- PX4_HOME_SET --------->|                           |                           |                           |
 |                           |--- Event(HOME_SET) ------>|                           |                           |
 |                           |                           |--- process_event() ------>|                           |
 |                           |                           |                           |--- handle_event() ------->|
 |                           |                           |                           |   sub.inject_event()      |
 |                           |                           |                           |                           |
 |                           |                           |                           |--- sub.handle_event() --->|
 |                           |                           |                           |   returns STARTUP_OK      |
 |                           |                           |                           |<--------------------------|
 |                           |                           |<-- remains STARTUP -------|                           |
 |                           |                           |                           |                           |
 |                           |                           |--- step() --------------->|                           |
 |                           |                           |                           |--- on_update() ---------->|
 |                           |                           |                           |   sees substate=OK        |
 |                           |                           |                           |   startup_ok=True         |
 |                           |                           |                           |--- on_exit() ------------>|
 |                           |                           |                           |   returns READY           |
 |                           |                           |<-- MainState.READY -----|                           |
 |                           |                           |                           |                           |
 |                           |                           |--- transition(READY) ---->|                           |
 |                           |                           |                           |                           |
 |                           |                           |                           |                           |
 |                           |                           |                           |                           |
 |                           |                           |--- step() ---------------> ReadyHFSM                  |
 |                           |                           |                           |--- on_update() ---------->|
 |                           |                           |                           |   (Ready logic)           |
 |                           |                           |<-- MainState.READY -----|                           |
 |                           |                           |                           |                           |




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
