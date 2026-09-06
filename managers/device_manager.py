from __future__ import annotations

import random
import time
from typing import Dict, Iterable, List, Optional

from models.device import Device


class DeviceManager:
	def __init__(self) -> None:
		self._devices: Dict[int, Device] = {}
		self._next_device_id = 1

	def add_device(self, device: Optional[Device] = None) -> Device:
		if device is None:
			device_id = self._next_device_id
			self._next_device_id += 1
			device = Device(device_id=device_id, name=f"device-{device_id:03d}")
		else:
			self._next_device_id = max(self._next_device_id, device.device_id + 1)

		self._devices[device.device_id] = device
		return device

	def add_devices(self, count: int) -> List[Device]:
		created: List[Device] = []
		for _ in range(max(0, count)):
			created.append(self.add_device())
		return created

	def remove_device(self, device_id: int) -> bool:
		return self._devices.pop(device_id, None) is not None

	def get_device(self, device_id: int) -> Optional[Device]:
		return self._devices.get(device_id)

	def all_devices(self) -> Iterable[Device]:
		return self._devices.values()

	def list_devices(self) -> List[Device]:
		return [self._devices[key] for key in sorted(self._devices)]

	def count(self) -> int:
		return len(self._devices)

	def seed_default_devices(self, count: int = 10) -> None:
		if self._devices:
			return
		self.add_devices(count)

	def simulate_tick(self) -> None:
		now = time.monotonic()
		for device in self._devices.values():
			if not device.online:
				device.check_heartbeat_timeout(now)
				continue

			device.temperature = round(max(0.0, min(50.0, device.temperature + random.uniform(-0.4, 0.4))), 1)
			device.humidity = round(max(0.0, min(100.0, device.humidity + random.uniform(-1.0, 1.0))), 1)

			if random.random() < 0.05:
				device.trigger_alarm()
			elif device.alarm and random.random() < 0.3:
				device.clear_alarm()

			device.check_heartbeat_timeout(now)

	def simulate_heartbeat(self) -> List[Device]:
		now = time.monotonic()
		heartbeating_devices: List[Device] = []
		for device in self._devices.values():
			if device.heartbeat_due(now):
				device.heartbeat()
				heartbeating_devices.append(device)
			elif device.online:
				device.check_heartbeat_timeout(now)
		return heartbeating_devices


__all__ = ["DeviceManager"]
