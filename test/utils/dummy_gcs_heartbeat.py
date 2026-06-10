#!/usr/bin/env python3
from pymavlink import mavutil
import time

def main():
    print("[GCS] Sending heartbeats to PX4 (1 Hz)...")

    master = mavutil.mavlink_connection("udpout:127.0.0.1:18570")

    while True:
        master.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_GCS,
            mavutil.mavlink.MAV_AUTOPILOT_INVALID,
            0, 0, 0
        )
        time.sleep(1)

if __name__ == "__main__":
    main()
