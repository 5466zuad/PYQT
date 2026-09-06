from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Device:
	device_id: int
	name: str
	temperature: float = 23.5
	humidity: float = 45.0
	alarm: bool = False
	online: bool = True
	last_heartbeat_at: float = field(default_factory=time.monotonic)
	heartbeat_interval: float = 5.0
	heartbeat_timeout: float = 15.0
	last_event: str = "initialized"

	def set_temperature(self, value: float) -> None:
		self.temperature = round(float(value), 1)
		self.last_event = "temperature_updated"

	def set_humidity(self, value: float) -> None:
		self.humidity = round(float(value), 1)
		self.last_event = "humidity_updated"

	def trigger_alarm(self) -> None:
		self.alarm = True
		self.last_event = "alarm_triggered"

	def clear_alarm(self) -> None:
		self.alarm = False
		self.last_event = "alarm_cleared"

	def go_online(self) -> None:
		self.online = True
		self.last_heartbeat_at = time.monotonic()
		self.last_event = "online"

	def go_offline(self, reason: str = "manual") -> None:
		self.online = False
		self.last_event = f"offline:{reason}"

	def heartbeat(self) -> None:
		self.last_heartbeat_at = time.monotonic()
		self.online = True
		self.last_event = "heartbeat"

	def heartbeat_due(self, now: Optional[float] = None) -> bool:
		current_time = time.monotonic() if now is None else now
		return self.online and current_time - self.last_heartbeat_at >= self.heartbeat_interval

	def check_heartbeat_timeout(self, now: Optional[float] = None) -> bool:
		current_time = time.monotonic() if now is None else now
		if current_time - self.last_heartbeat_at >= self.heartbeat_timeout:
			self.online = False
			self.last_event = "heartbeat_timeout"
			return True
		return False

	def randomize(self) -> None:
		self.temperature = round(random.uniform(18.0, 35.0), 1)
		self.humidity = round(random.uniform(20.0, 80.0), 1)
		self.alarm = random.random() < 0.1
		self.last_event = "randomized"

	def snapshot(self) -> Dict[str, object]:
		return {
			"device_id": self.device_id,
			"name": self.name,
			"temperature": self.temperature,
			"humidity": self.humidity,
			"alarm": self.alarm,
			"online": self.online,
			"heartbeat_interval": self.heartbeat_interval,
			"heartbeat_timeout": self.heartbeat_timeout,
			"last_event": self.last_event,
		}


__all__ = ["Device"]
