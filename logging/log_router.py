# === PFAD-B FULL FILE: QGCR/logging/log_router.py ===

class LogRouter:
    """
    Zentraler Logger mit drei Kanälen:
    - px4(instance_id, text)  : PX4-Instanzen (stdout/stderr, STATUSTEXT)
    - sim(source, text)       : Simulatoren (Gazebo / Matlab / Python)
    - qgcr(text)              : QGCR intern (HFSM, GUI, MicroServices)
    """

    def __init__(self, model, queue_registry):
        self.model = model
        self.q = queue_registry

    def px4(self, instance_id, text: str):
        self.q.px4_log_queue.put(f"[PX4-{instance_id}] {text}")

    def sim(self, source: str, text: str):
        self.q.sim_log_queue.put(f"[SIM-{source}] {text}")

    def qgcr(self, text: str):
        self.q.qgcr_log_queue.put(f"[QGCR] {text}")
