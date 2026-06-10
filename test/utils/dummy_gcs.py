# === PFAD-B FULL FILE: QGCR/test/utils/dummy_gcs.py ===

import threading
import time
import socket
from pymavlink import mavutil


def start_dummy_gcs_with_sync(
    gcs_port=14540,
    px4_port=14580,
    rate_hz=1.0,
    timeout=10.0
):
    """
    Dummy-GCS für PX4 Mission-Link (#1):

    - Bindet lokal auf gcs_port (14540)
    - Sendet Heartbeats an PX4 (px4_port = 14580)
    - Wartet blockierend auf ersten PX4-Heartbeat (PX4 sendet 14580 -> 14540)

    Rückgabe:
        hb_thread, gcs_sock, px4_heartbeat_msg
    """

    # GCS-Socket: lokal 14540, empfängt PX4-HBs und sendet GCS-HBs
    gcs_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    gcs_sock.bind(("127.0.0.1", gcs_port))
    gcs_sock.settimeout(0.2)

    mav = mavutil.mavlink.MAVLink(None)
    mav.srcSystem = 255
    mav.srcComponent = 190

    period = 1.0 / rate_hz
    px4_heartbeat = None

    def _hb_loop():
        while True:
            try:
                hb = mav.heartbeat_encode(
                    mavutil.mavlink.MAV_TYPE_GCS,
                    mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                    0, 0, 0
                )
                # GCS -> PX4: 14540 -> 14580
                gcs_sock.sendto(hb.get_msgbuf(), ("127.0.0.1", px4_port))
            except Exception:
                pass
            time.sleep(period)

    hb_thread = threading.Thread(target=_hb_loop, daemon=True)
    hb_thread.start()

    # PX4-Heartbeat abwarten (PX4: 14580 -> 14540)
    start = time.time()
    while time.time() - start < timeout:
        try:
            data, _ = gcs_sock.recvfrom(2048)
            msg = mavutil.mavlink.MAVLink_message.decode(data)
            if msg.get_type() == "HEARTBEAT":
                px4_heartbeat = msg
                break
        except Exception:
            pass

    return hb_thread, gcs_sock, px4_heartbeat
