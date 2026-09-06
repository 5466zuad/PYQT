from __future__ import annotations

import json
import socket
import threading
import time
from typing import Dict, List

from PyQt5.QtWidgets import QApplication

from managers.device_manager import DeviceManager
from ui.main_window import MainWindow
from utils.protocol import make_frame
from utils.runtime import configure_qt_runtime


def demo() -> None:
	manager = DeviceManager()
	manager.seed_default_devices(10)

	print(f"created {manager.count()} devices")
	for _ in range(3):
		manager.simulate_tick()
		for device in manager.list_devices()[:3]:
			print(device.snapshot())
		print("-")


def smoke_test() -> None:
	configure_qt_runtime()
	manager = DeviceManager()
	manager.seed_default_devices(10)
	assert manager.count() == 10
	device = manager.get_device(1)
	assert device is not None
	device.set_temperature(33.3)
	device.set_humidity(66.6)
	device.trigger_alarm()
	assert device.temperature == 33.3
	assert device.humidity == 66.6
	assert device.alarm is True
	device.clear_alarm()
	device.go_offline("smoke")
	assert device.online is False
	device.go_online()
	assert device.online is True
	device.last_heartbeat_at = time.monotonic() - 1
	device.heartbeat_interval = 0.1
	assert manager.simulate_heartbeat()

	app = QApplication.instance() or QApplication([])
	window = MainWindow()
	window.select_device(1)
	window.temperature_batch_spin.setValue(44.4)
	window.humidity_batch_spin.setValue(55.5)
	window.device_list.item(0).setSelected(True)
	window.device_list.item(1).setSelected(True)
	window.apply_batch_temperature()
	window.apply_batch_humidity()
	assert window.manager.get_device(1).temperature == 44.4
	assert window.manager.get_device(2).humidity == 55.5
	window.trigger_alarm_all()
	assert all(item.alarm for item in window.manager.all_devices())
	window.clear_alarm_all()
	assert all(not item.alarm for item in window.manager.all_devices())
	print("smoke test passed")


def tcp_smoke_test() -> None:
	configure_qt_runtime()
	received: List[Dict[str, object]] = []
	server_ready = threading.Event()
	server_port: Dict[str, int] = {}

	def server_worker() -> None:
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
			server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			server.bind(("127.0.0.1", 0))
			server.listen(1)
			server_port["value"] = server.getsockname()[1]
			server_ready.set()
			conn, _ = server.accept()
			with conn:
				conn.settimeout(2.0)
				buffer = b""
				while len(received) < 2:
					chunk = conn.recv(4096)
					if not chunk:
						break
					buffer += chunk
					while b"\n" in buffer:
						line, buffer = buffer.split(b"\n", 1)
						if line.strip():
							received.append(json.loads(line.decode("utf-8")))
							if len(received) >= 2:
								break

	thread = threading.Thread(target=server_worker, daemon=True)
	thread.start()
	if not server_ready.wait(timeout=3.0):
		raise RuntimeError("tcp smoke test server did not start")

	app = QApplication.instance() or QApplication([])
	window = MainWindow()
	window.gateway.connect_to_host("127.0.0.1", server_port["value"])
	deadline = time.monotonic() + 3.0
	while not window.gateway.is_connected and time.monotonic() < deadline:
		app.processEvents()
		time.sleep(0.01)

	window.gateway.send_frame(make_frame("heartbeat", window.manager.get_device(1)))
	window.gateway.send_frame(make_frame("alarm", window.manager.get_device(1), reason="tcp-smoke"))
	deadline = time.monotonic() + 3.0
	while len(received) < 2 and time.monotonic() < deadline:
		app.processEvents()
		time.sleep(0.01)

	assert len(received) >= 2
	assert received[0]["type"] == "heartbeat"
	assert received[1]["type"] == "alarm"
	print("tcp smoke test passed")


__all__ = ["demo", "smoke_test", "tcp_smoke_test"]
