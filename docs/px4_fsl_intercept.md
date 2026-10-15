# Offener Punkt: FSL-Abfang als PX4-FlightTask (Weg A, Prototyp)

Status: **offen** – nur Konzept, noch nichts umgesetzt (Architekturänderung, Freigabe nötig).
Basis: PX4 v1.17.0 (`~/PX4-Autopilot`), Modell `gz_fsl_rocket_vtol` im Multicopter-Betrieb.

## Ziel

Die Berechnung aus `model/intercept.py` (Lot-Fußpunkt, entgegen/nachfliegen, Treffzeit,
Zeitbudget) läuft im PX4 als eigene FlightTask mit Regeltakt. QGCR liefert nur noch den Trigger
und zeigt an. Vorteil: weiterfliegen bei Funkverlust, keine Funklatenz, kein `DO_REPOSITION`
alle 2 s. Rechenaufwand: ≈ 50 Gleitkomma-Operationen pro Takt (≈ 1 µs auf STM32H7) – vernachlässigbar.

## Offboard oder eigener Zustand?

| Variante | Bewertung |
|---|---|
| **Offboard** (`NAVIGATION_STATE_OFFBOARD`) | **Ungeeignet.** Sollwerte müssen von außen kommen (MAVLink/ROS 2, ≥ 2 Hz, sonst Failsafe). Die Berechnung bliebe außerhalb von PX4 – das ist Weg „Companion/QGCR“, nicht Weg A. |
| **External Modes** (`NAVIGATION_STATE_EXTERNAL1…8`) | Für Modi, die sich zur Laufzeit über die ROS-2-`px4-ros2-interface-lib` anmelden – laufen auf einem Companion Computer, nicht in der Firmware. Nicht Weg A. |
| **Vorhandenen Zustand `AUTO_FOLLOW_TARGET` wiederverwenden** | **Empfehlung für den Prototyp.** Der Zustand existiert inkl. Commander-Logik, MAVLink-Modusnummer, Mode-Requirements und Trigger-Eingang (`FOLLOW_TARGET` → uORB `follow_target`). Per Parameter wird statt `AutoFollowTarget` die neue Task gestartet. Wenig Eingriff, QGC/QGCR kennen den Modus. Nachteil: echtes Follow-Me ist dann nicht gleichzeitig nutzbar. |
| **Eigener Zustand `AUTO_FSL_INTERCEPT`** | **Für das Produkt.** Sauber getrennt, eigener Modusname, eigene Anforderungen/Failsafes. Mehr Änderungen (siehe unten), eigene Modusnummer muss in QGCR (und ggf. QGC) bekannt sein. |

## Änderungen in PX4

### Prototyp (Zustand `AUTO_FOLLOW_TARGET` wiederverwenden)

1. **Neue FlightTask** `src/modules/flight_mode_manager/tasks/FslIntercept/`
   (`FlightTaskFslIntercept.{hpp,cpp}`, `CMakeLists.txt`, `fsl_intercept_params.c`),
   abgeleitet von `FlightTaskAuto` (Vorbild `AutoFollowTarget`):
   - `activate()`: Startpunkt merken, Trigger aus uORB `follow_target` lesen, Planung
     (Lot-Fußpunkt, erwartete Entscheidung, Budget) – entspricht `plan_intercept()`.
   - `update()` (jeder Takt): Phase APPROACH → Sollposition Wartepunkt; PURSUE → `pursuit()`
     → Sollposition/Geschwindigkeit Treffpunkt; Abstand ≤ `FSL_MEET_RAD` bzw. Zeit reicht nicht
     bzw. Nachfliegen unmöglich → Rückkehr anfordern.
   - Minimalen Abstand mitführen und veröffentlichen.
2. **Task registrieren:** `flight_mode_manager/CMakeLists.txt` (`list(APPEND flight_tasks_all FslIntercept)`).
3. **Task auswählen:** `FlightModeManager.cpp`, Block `NAVIGATION_STATE_AUTO_FOLLOW_TARGET`:
   bei Parameter `FSL_ICPT_EN = 1` → `switchTask(FlightTaskIndex::FslIntercept)`.
4. **Rückkehr auslösen:** Eine FlightTask kann den Modus nicht selbst wechseln. Sie veröffentlicht
   intern `vehicle_command` `VEHICLE_CMD_NAV_RETURN_TO_LAUNCH` (wie ein MAVLink-Kommando, der
   Commander schaltet auf RTL).
5. **Parameter** (`fsl_intercept_params.c`): Geschwindigkeit, Wirkungsgrad 0,92, Anlaufzeit,
   Abbremszeit, Sinkrate, Reserve, Mindesthöhe, `FSL_MEET_RAD` (5 m), Timeout; RTL-Höhe aus
   `RTL_RETURN_ALT`. Akku-Minimum über die vorhandenen Failsafes (`BAT_LOW_THR`, `COM_LOW_BAT_ACT`).
6. **Status an QGCR:** neue uORB-Nachricht `msg/FslInterceptStatus.msg` (Phase, Modus
   entgegen/nachfliegen, Treffzeit, Treffpunkt, minimaler Abstand) + MAVLink-Stream
   (Prototyp: `DEBUG_VECT`/`NAMED_VALUE_FLOAT`, Produkt: eigene Dialekt-Nachricht).

### Produkt (eigener Zustand `AUTO_FSL_INTERCEPT`) zusätzlich

7. `msg/versioned/VehicleStatus.msg`: neuer `NAVIGATION_STATE_…` (freier Platz, z. B. `FREE1 = 16`;
   versionierte Nachricht → Kompatibilität mit ROS 2 beachten).
8. `commander/px4_custom_mode.h`: neuer `PX4_CUSTOM_SUB_MODE_AUTO_FSL_INTERCEPT` + Abbildung
   nav_state ↔ custom_mode.
9. `commander/ModeUtil/conversions.hpp`, `mode_requirements.cpp` (lokale Position, Höhe,
   Lage, Arming-Sperre), `control_mode.cpp` (Positions-/Geschwindigkeitsregelung aktiv),
   `Commander.cpp` (Moduswechsel per `DO_SET_MODE`, Anzeige-Namen).
10. `FlightModeManager.cpp`: eigener Block für den neuen Zustand (statt Parameter-Weiche).
11. Trigger-Eingang: eigene uORB-Nachricht `FslTrigger.msg` mit Zeitstempel der Messung
    (das vorhandene `follow_target` setzt den Empfangszeitpunkt) + MAVLink-Empfang in
    `mavlink_receiver.cpp`.

## Änderungen in QGCR

- InterceptHFSM: statt Mission-Upload + `DO_REPOSITION` → Takeoff, dann Trigger als
  `FOLLOW_TARGET` senden (laufend, wenn echte Messungen kommen) und Modus wechseln
  (`DO_SET_MODE` auf AUTO.FOLLOW_TARGET bzw. den neuen Modus). Überwachung bleibt als Rückfallebene.
- `decode_px4_mode`: neuen Modus kennen; Status-Nachricht der Task auswerten (Phase, Treffzeit,
  minimaler Abstand) statt selbst zu rechnen. `model/intercept.py` bleibt für Vorschau/Plot.

## Grenzen / Risiken

- FlightTasks gelten nur für **Multicopter**. Abfangen im Starrflügel-Betrieb bräuchte eine
  Lösung im Navigator/FW-Positionsregler.
- Eigener PX4-Fork: bauen, pflegen, bei PX4-Updates nachziehen; sicherheitsrelevanter Code →
  SITL-Tests (wie `test_px4_application_intercept.py`) auf PX4-Seite nötig.
- Prototyp-Variante blockiert das echte Follow-Me.
