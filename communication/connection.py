# === PFAD-B FULL FILE: QGCR/communication/connection.py ===

import time
import threading
from pymavlink import mavutil


class Connection:
    """
    MAVLink-Verbindung über UDP.
    - Bindet UDP-Port
    - Startet RX-Thread
    - Startet GCS-Heartbeat-Thread
    - KEIN wait_heartbeat() mehr (Heartbeat wird asynchron im Model/HFSM ausgewertet)
    """

    def __init__(self, model, dispatcher):
        self.model = model
        self.dispatcher = dispatcher

        self.master = None
        self._stop = False

        self._rx_thread = None
        self._gcs_hb_thread = None

        self.udp_ip = "0.0.0.0"
        self.udp_port = 14550

    def connect(self):
        """
        Bindet den UDP-Port und startet die Threads.
        Kein blockierendes wait_heartbeat() – der HFSM wartet selbst auf Heartbeat.
        """
        print(f"[Connection] Binding UDP on {self.udp_ip}:{self.udp_port}")

        self.master = mavutil.mavlink_connection(
            f"udp:{self.udp_ip}:{self.udp_port}",
            source_system=255,
            source_component=0,
            autoreconnect=False
        )

        # RX-Thread
        self._rx_thread = threading.Thread(
            target=self._receive_loop,
            daemon=True
        )
        self._rx_thread.start()

        # GCS-Heartbeat-Thread
        self._gcs_hb_thread = threading.Thread(
            target=self._gcs_heartbeat_loop,
            daemon=True
        )
        self._gcs_hb_thread.start()

    def _receive_loop(self):
        """
        Liest MAVLink-Nachrichten und verteilt sie an Model + Dispatcher.
        """
        while not self._stop:
            try:
                msg = self.master.recv_match(blocking=True, timeout=1.0)
                if msg is None:
                    continue

                msg_type = msg.get_type()

                if msg_type == "HEARTBEAT":
                    self.model.update_ready_to_arm(msg)
                    self.model.on_heartbeat(msg)

                elif msg_type == "GLOBAL_POSITION_INT":
                    self.model.update_vehicle_position(
                        msg.lat / 1e7,
                        msg.lon / 1e7,
                        msg.relative_alt / 1000.0
                    )

                elif msg_type == "COMMAND_ACK":
                    self.model.on_command_ack(msg)
                    self.dispatcher.dispatch(msg)

                elif msg_type == "HOME_POSITION":
                    self.model.update_home_position(
                        msg.latitude / 1e7,
                        msg.longitude / 1e7,
                        msg.altitude / 1000.0
                    )
                    
                else:
                    # PX4 STATUSTEXT → PX4-Logfenster
                    if msg_type == "STATUSTEXT":
                        txt = getattr(msg, "text", "")
                        sev = getattr(msg, "severity", 0)
                        if hasattr(self.model, "log"):
                            self.model.log.px4(
                                self.master.target_system,
                                f"[STATUSTEXT:{sev}] {txt}"
                            )

                    # Restliche Nachrichten normal weiterleiten
                    self.dispatcher.dispatch(msg)

            except Exception as e:
                print("[Connection] Fehler im Empfangsloop:", e)
                time.sleep(0.1)

    def _gcs_heartbeat_loop(self):
        """
        Sendet periodisch einen GCS-Heartbeat an PX4.
        """
        MAV_TYPE_GCS = 6
        MAV_AUTOPILOT_INVALID = 8
        MAV_STATE_ACTIVE = 4
        MAV_MODE_FLAG_CUSTOM_MODE_ENABLED = 1

        while not self._stop:
            try:
                self.master.mav.heartbeat_send(
                    MAV_TYPE_GCS,
                    MAV_AUTOPILOT_INVALID,
                    0,
                    MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                    MAV_STATE_ACTIVE,
                )
            except Exception:
                pass

            time.sleep(1.0)

    def send(self, msg):
        """
        Sendet eine MAVLink-Nachricht.
        """
        try:
            self.master.mav.send(msg)
        except Exception as e:
            print("[Connection] Sendefehler:", e)

    def close(self):
        self._stop = True
        try:
            if self.master:
                self.master.close()
        except Exception:
            pass
        print("[Connection] Verbindung geschlossen.")
