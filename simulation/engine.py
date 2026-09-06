from __future__ import annotations

from managers.device_manager import DeviceManager


def advance_simulation(manager: DeviceManager) -> None:
	manager.simulate_tick()


def advance_heartbeat(manager: DeviceManager):
	return manager.simulate_heartbeat()


__all__ = ["advance_simulation", "advance_heartbeat"]
