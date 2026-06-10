#!/usr/bin/env python3

from harness.harness_px4_alive import require_px4_alive
from QGCR.communication.microservices.param_microservice import ParamMicroService


def main():
    master, tsys, tcomp = require_px4_alive()

    ps = ParamMicroService(master, tsys, tcomp)

    print("[HARNESS] Sync Parameters…")
    params = ps.sync()

    print(f"[HARNESS] Parameter geladen: {len(params)}")
    print("[HARNESS] ParamMicroService Harness COMPLETE")


if __name__ == "__main__":
    main()
