from __future__ import annotations

from typing import Dict, List, Optional

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
	QAbstractItemView,
	QApplication,
	QCheckBox,
	QDoubleSpinBox,
	QFormLayout,
	QGroupBox,
	QHBoxLayout,
	QLabel,
	QListWidget,
	QListWidgetItem,
	QLineEdit,
	QMainWindow,
	QMessageBox,
	QPushButton,
	QSpinBox,
	QTextEdit,
	QVBoxLayout,
	QWidget,
)

from communication.tcp_client import GatewayClient
from managers.device_manager import DeviceManager
from models.device import Device
from simulation.engine import advance_heartbeat, advance_simulation
from utils.protocol import make_frame
from utils.runtime import configure_qt_runtime


class MainWindow(QMainWindow):
	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle("多设备模拟器上位机")
		self.resize(1280, 820)

		self.manager = DeviceManager()
		self.manager.seed_default_devices(10)
		self.gateway = GatewayClient(self)
		self.gateway.logMessage.connect(self.append_log)
		self.gateway.connectedChanged.connect(self.on_gateway_connected_changed)
		self.gateway.stateChanged.connect(self.on_gateway_state_changed)
		self.gateway.frameReceived.connect(self.on_gateway_frame_received)

		self._updating_detail = False

		self.device_list = QListWidget()
		self.device_list.setSelectionMode(QAbstractItemView.MultiSelection)
		self.device_list.currentItemChanged.connect(self.on_selection_changed)

		self.total_label = QLabel("0")
		self.online_label = QLabel("0")
		self.alarm_label = QLabel("0")
		self.offline_label = QLabel("0")
		self.gateway_state_label = QLabel("未连接")
		self.gateway_state_label.setStyleSheet("color:#aa0000;font-weight:600;")
		self.gateway_host_edit = QLineEdit("127.0.0.1")
		self.gateway_port_spin = QSpinBox()
		self.gateway_port_spin.setRange(1, 65535)
		self.gateway_port_spin.setValue(9000)
		self.gateway_connect_button = QPushButton("连接网关")
		self.gateway_disconnect_button = QPushButton("断开连接")

		self.device_id_value = QLabel("-")
		self.name_value = QLabel("-")
		self.last_event_value = QLabel("-")

		self.temperature_spin = QDoubleSpinBox()
		self.temperature_spin.setRange(-40.0, 125.0)
		self.temperature_spin.setDecimals(1)
		self.temperature_spin.setSingleStep(0.1)
		self.temperature_batch_spin = QDoubleSpinBox()
		self.temperature_batch_spin.setRange(-40.0, 125.0)
		self.temperature_batch_spin.setDecimals(1)
		self.temperature_batch_spin.setSingleStep(0.1)
		self.temperature_batch_spin.setValue(25.0)

		self.humidity_spin = QDoubleSpinBox()
		self.humidity_spin.setRange(0.0, 100.0)
		self.humidity_spin.setDecimals(1)
		self.humidity_spin.setSingleStep(0.1)
		self.humidity_batch_spin = QDoubleSpinBox()
		self.humidity_batch_spin.setRange(0.0, 100.0)
		self.humidity_batch_spin.setDecimals(1)
		self.humidity_batch_spin.setSingleStep(0.1)
		self.humidity_batch_spin.setValue(50.0)

		self.alarm_check = QCheckBox("报警")
		self.online_check = QCheckBox("在线")

		self.add_button = QPushButton("新增设备")
		self.remove_button = QPushButton("删除设备")
		self.apply_button = QPushButton("应用修改")
		self.random_button = QPushButton("随机变化")
		self.alarm_button = QPushButton("触发报警")
		self.clear_alarm_button = QPushButton("消除报警")
		self.offline_button = QPushButton("模拟失联")
		self.online_button = QPushButton("恢复在线")
		self.batch_temperature_button = QPushButton("批量设置温度")
		self.batch_humidity_button = QPushButton("批量设置湿度")
		self.all_alarm_button = QPushButton("全部报警")
		self.clear_all_alarm_button = QPushButton("全部消警")
		self.all_offline_button = QPushButton("全部失联")
		self.all_online_button = QPushButton("全部恢复")

		self.add_button.clicked.connect(self.add_device)
		self.remove_button.clicked.connect(self.remove_selected_device)
		self.apply_button.clicked.connect(self.apply_device_changes)
		self.random_button.clicked.connect(self.randomize_selected_device)
		self.alarm_button.clicked.connect(self.trigger_alarm_selected)
		self.clear_alarm_button.clicked.connect(self.clear_alarm_selected)
		self.offline_button.clicked.connect(self.offline_selected_device)
		self.online_button.clicked.connect(self.online_selected_device)
		self.batch_temperature_button.clicked.connect(self.apply_batch_temperature)
		self.batch_humidity_button.clicked.connect(self.apply_batch_humidity)
		self.all_alarm_button.clicked.connect(self.trigger_alarm_all)
		self.clear_all_alarm_button.clicked.connect(self.clear_alarm_all)
		self.all_offline_button.clicked.connect(self.offline_all)
		self.all_online_button.clicked.connect(self.online_all)
		self.gateway_connect_button.clicked.connect(self.connect_gateway)
		self.gateway_disconnect_button.clicked.connect(self.disconnect_gateway)

		self.log_view = QTextEdit()
		self.log_view.setReadOnly(True)

		self._build_layout()
		self.refresh_ui()

		self.timer = QTimer(self)
		self.timer.setInterval(1000)
		self.timer.timeout.connect(self.on_tick)
		self.timer.start()

	def _build_layout(self) -> None:
		central = QWidget(self)
		self.setCentralWidget(central)

		root_layout = QVBoxLayout(central)

		header = QHBoxLayout()
		header.addWidget(QLabel("设备总数"))
		header.addWidget(self.total_label)
		header.addSpacing(20)
		header.addWidget(QLabel("在线"))
		header.addWidget(self.online_label)
		header.addSpacing(20)
		header.addWidget(QLabel("报警"))
		header.addWidget(self.alarm_label)
		header.addSpacing(20)
		header.addWidget(QLabel("失联"))
		header.addWidget(self.offline_label)
		header.addStretch(1)
		header.addWidget(self.gateway_state_label)
		header.addWidget(self.gateway_connect_button)
		header.addWidget(self.gateway_disconnect_button)
		header.addWidget(self.add_button)
		header.addWidget(self.remove_button)
		root_layout.addLayout(header)

		connection_box = QGroupBox("TCP 网关")
		connection_form = QFormLayout(connection_box)
		connection_form.addRow("主机", self.gateway_host_edit)
		connection_form.addRow("端口", self.gateway_port_spin)
		root_layout.addWidget(connection_box)

		body = QHBoxLayout()

		left_box = QVBoxLayout()
		left_box.addWidget(QLabel("设备列表"))
		left_box.addWidget(self.device_list)
		body.addLayout(left_box, 2)

		right_box = QVBoxLayout()
		right_box.addWidget(QLabel("当前设备"))

		form = QFormLayout()
		form.addRow("设备ID", self.device_id_value)
		form.addRow("名称", self.name_value)
		form.addRow("温度(℃)", self.temperature_spin)
		form.addRow("湿度(%RH)", self.humidity_spin)
		form.addRow("状态", self.alarm_check)
		form.addRow("在线", self.online_check)
		form.addRow("最近事件", self.last_event_value)
		right_box.addLayout(form)

		button_row_1 = QHBoxLayout()
		button_row_1.addWidget(self.apply_button)
		button_row_1.addWidget(self.random_button)
		right_box.addLayout(button_row_1)

		button_row_2 = QHBoxLayout()
		button_row_2.addWidget(self.alarm_button)
		button_row_2.addWidget(self.clear_alarm_button)
		button_row_2.addWidget(self.offline_button)
		button_row_2.addWidget(self.online_button)
		right_box.addLayout(button_row_2)

		batch_form = QFormLayout()
		batch_form.addRow("批量温度", self.temperature_batch_spin)
		batch_form.addRow("批量湿度", self.humidity_batch_spin)
		right_box.addLayout(batch_form)

		button_row_3 = QHBoxLayout()
		button_row_3.addWidget(self.batch_temperature_button)
		button_row_3.addWidget(self.batch_humidity_button)
		right_box.addLayout(button_row_3)

		button_row_4 = QHBoxLayout()
		button_row_4.addWidget(self.all_alarm_button)
		button_row_4.addWidget(self.clear_all_alarm_button)
		button_row_4.addWidget(self.all_offline_button)
		button_row_4.addWidget(self.all_online_button)
		right_box.addLayout(button_row_4)

		body.addLayout(right_box, 3)
		root_layout.addLayout(body, 2)

		root_layout.addWidget(QLabel("日志"))
		root_layout.addWidget(self.log_view, 1)

	def append_log(self, message: str) -> None:
		self.log_view.append(message)
		self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

	def connect_gateway(self) -> None:
		self.gateway.connect_to_host(self.gateway_host_edit.text().strip(), self.gateway_port_spin.value())

	def disconnect_gateway(self) -> None:
		self.gateway.disconnect()

	def on_gateway_connected_changed(self, connected: bool) -> None:
		self.gateway_state_label.setText("已连接" if connected else "未连接")
		self.gateway_state_label.setStyleSheet("color:#008800;font-weight:600;" if connected else "color:#aa0000;font-weight:600;")

	def on_gateway_state_changed(self, text: str) -> None:
		if text:
			self.gateway_state_label.setText(text)

	def on_gateway_frame_received(self, frame: Dict[str, object]) -> None:
		command = str(frame.get("cmd") or frame.get("type") or "").lower()
		device_id = frame.get("device_id")
		device: Optional[Device] = None
		if device_id is None and isinstance(frame.get("device"), dict):
			device_id = frame["device"].get("device_id")
		if device_id is not None:
			try:
				device = self.manager.get_device(int(device_id))
			except (TypeError, ValueError):
				device = None

		if command in {"set_temperature", "set_temp"} and device is not None:
			value = frame.get("value", frame.get("temperature"))
			if value is not None:
				device.set_temperature(float(value))
				self.append_log(f"网关下发温度: DEV{device.device_id:03d} -> {device.temperature:.1f}℃")
		elif command in {"set_humidity"} and device is not None:
			value = frame.get("value", frame.get("humidity"))
			if value is not None:
				device.set_humidity(float(value))
				self.append_log(f"网关下发湿度: DEV{device.device_id:03d} -> {device.humidity:.1f}%RH")
		elif command in {"trigger_alarm", "alarm"} and device is not None:
			device.trigger_alarm()
			self.append_log(f"网关下发报警: DEV{device.device_id:03d}")
		elif command in {"clear_alarm", "disalarm"} and device is not None:
			device.clear_alarm()
			self.append_log(f"网关下发消警: DEV{device.device_id:03d}")
		elif command in {"offline", "disconnect"} and device is not None:
			device.go_offline("gateway")
			self.append_log(f"网关下发失联: DEV{device.device_id:03d}")
		elif command in {"online", "restore"} and device is not None:
			device.go_online()
			self.append_log(f"网关下发恢复在线: DEV{device.device_id:03d}")
		elif command in {"add_device"}:
			count = int(frame.get("count", 1))
			for _ in range(max(0, count)):
				self.add_device()
		elif command in {"remove_device"} and device is not None:
			self.manager.remove_device(device.device_id)
			self.append_log(f"网关下发删除: DEV{device.device_id:03d}")
			self.refresh_ui()
		elif command:
			self.append_log(f"收到网关帧: {frame}")

	def selected_device(self) -> Optional[Device]:
		devices = self.selected_devices()
		if devices:
			return devices[0]
		item = self.device_list.currentItem()
		if item is None:
			return None
		device_id = item.data(Qt.UserRole)
		return self.manager.get_device(int(device_id)) if device_id is not None else None

	def selected_devices(self) -> List[Device]:
		devices: List[Device] = []
		for item in self.device_list.selectedItems():
			device_id = item.data(Qt.UserRole)
			if device_id is None:
				continue
			device = self.manager.get_device(int(device_id))
			if device is not None:
				devices.append(device)
		return devices

	def device_status_text(self, device: Device) -> str:
		if not device.online:
			icon = "🔴"
			status = "失联"
		elif device.alarm:
			icon = "🟠"
			status = "报警"
		else:
			icon = "🟢"
			status = "在线"
		return f"{icon} DEV{device.device_id:03d}  {status}"

	def refresh_device_list(self, preserve_selection: bool = True) -> None:
		selected_ids: List[int] = []
		if preserve_selection:
			selected_ids = [device.device_id for device in self.selected_devices()]

		self.device_list.blockSignals(True)
		self.device_list.clear()
		for device in self.manager.list_devices():
			item = QListWidgetItem(self.device_status_text(device))
			item.setData(Qt.UserRole, device.device_id)
			self.device_list.addItem(item)
			if device.device_id in selected_ids:
				item.setSelected(True)
		if self.device_list.currentItem() is None and self.device_list.count() > 0:
			self.device_list.setCurrentRow(0)
		self.device_list.blockSignals(False)

	def refresh_summary(self) -> None:
		devices = self.manager.list_devices()
		total = len(devices)
		online = sum(1 for device in devices if device.online)
		alarm = sum(1 for device in devices if device.alarm)
		offline = total - online
		self.total_label.setText(str(total))
		self.online_label.setText(str(online))
		self.alarm_label.setText(str(alarm))
		self.offline_label.setText(str(offline))

	def refresh_detail(self, device: Optional[Device]) -> None:
		self._updating_detail = True
		try:
			if device is None:
				self.device_id_value.setText("-")
				self.name_value.setText("-")
				self.temperature_spin.setValue(0.0)
				self.humidity_spin.setValue(0.0)
				self.alarm_check.setChecked(False)
				self.online_check.setChecked(False)
				self.last_event_value.setText("-")
				return

			self.device_id_value.setText(f"DEV{device.device_id:03d}")
			self.name_value.setText(device.name)
			self.temperature_spin.setValue(device.temperature)
			self.humidity_spin.setValue(device.humidity)
			self.alarm_check.setChecked(device.alarm)
			self.online_check.setChecked(device.online)
			self.last_event_value.setText(device.last_event)
		finally:
			self._updating_detail = False

	def refresh_ui(self) -> None:
		self.refresh_summary()
		self.refresh_device_list()
		self.refresh_detail(self.selected_device())

	def on_selection_changed(self, current: object = None, previous: object = None) -> None:
		self.refresh_detail(self.selected_device())

	def add_device(self) -> None:
		device = self.manager.add_device()
		self.append_log(f"新增设备 DEV{device.device_id:03d}")
		self.gateway.send_frame(make_frame("register", device))
		self.refresh_ui()
		self.select_device(device.device_id)

	def select_device(self, device_id: int) -> None:
		for index in range(self.device_list.count()):
			item = self.device_list.item(index)
			if item.data(Qt.UserRole) == device_id:
				self.device_list.setCurrentItem(item)
				break

	def remove_selected_device(self) -> None:
		device = self.selected_device()
		if device is None:
			QMessageBox.information(self, "提示", "请先选择一个设备")
			return
		removed = self.manager.remove_device(device.device_id)
		if removed:
			self.append_log(f"删除设备 DEV{device.device_id:03d}")
			self.gateway.send_frame(make_frame("remove", device, reason="manual"))
		self.refresh_ui()

	def apply_device_changes(self) -> None:
		device = self.selected_device()
		if device is None:
			return
		device.set_temperature(self.temperature_spin.value())
		device.set_humidity(self.humidity_spin.value())
		device.alarm = self.alarm_check.isChecked()
		device.online = self.online_check.isChecked()
		device.last_event = "manual_update"
		self.gateway.send_frame(make_frame("config", device))
		self.append_log(f"DEV{device.device_id:03d} 更新为 温度={device.temperature:.1f}℃ 湿度={device.humidity:.1f}%RH")
		self.refresh_ui()
		self.select_device(device.device_id)

	def randomize_selected_device(self) -> None:
		device = self.selected_device()
		if device is None:
			return
		device.randomize()
		self.append_log(f"DEV{device.device_id:03d} 随机刷新状态")
		self.gateway.send_frame(make_frame("telemetry", device, reason="randomize"))
		self.refresh_ui()
		self.select_device(device.device_id)

	def trigger_alarm_selected(self) -> None:
		device = self.selected_device()
		if device is None:
			return
		device.trigger_alarm()
		self.append_log(f"DEV{device.device_id:03d} 触发报警")
		self.gateway.send_frame(make_frame("alarm", device, reason="manual"))
		self.refresh_ui()
		self.select_device(device.device_id)

	def clear_alarm_selected(self) -> None:
		device = self.selected_device()
		if device is None:
			return
		device.clear_alarm()
		self.append_log(f"DEV{device.device_id:03d} 消除报警")
		self.gateway.send_frame(make_frame("clear_alarm", device, reason="manual"))
		self.refresh_ui()
		self.select_device(device.device_id)

	def offline_selected_device(self) -> None:
		device = self.selected_device()
		if device is None:
			return
		device.go_offline("manual")
		self.append_log(f"DEV{device.device_id:03d} 模拟失联")
		self.gateway.send_frame(make_frame("offline", device, reason="manual"))
		self.refresh_ui()
		self.select_device(device.device_id)

	def online_selected_device(self) -> None:
		device = self.selected_device()
		if device is None:
			return
		device.go_online()
		self.append_log(f"DEV{device.device_id:03d} 恢复在线")
		self.gateway.send_frame(make_frame("online", device, reason="manual"))
		self.refresh_ui()
		self.select_device(device.device_id)

	def apply_batch_temperature(self) -> None:
		devices = self.selected_devices()
		if not devices:
			QMessageBox.information(self, "提示", "请先选择一个或多个设备")
			return
		value = self.temperature_batch_spin.value()
		for device in devices:
			device.set_temperature(value)
			self.append_log(f"DEV{device.device_id:03d} 批量温度设置为 {value:.1f}℃")
			self.gateway.send_frame(make_frame("config", device, batch="temperature"))
		self.refresh_ui()

	def apply_batch_humidity(self) -> None:
		devices = self.selected_devices()
		if not devices:
			QMessageBox.information(self, "提示", "请先选择一个或多个设备")
			return
		value = self.humidity_batch_spin.value()
		for device in devices:
			device.set_humidity(value)
			self.append_log(f"DEV{device.device_id:03d} 批量湿度设置为 {value:.1f}%RH")
			self.gateway.send_frame(make_frame("config", device, batch="humidity"))
		self.refresh_ui()

	def trigger_alarm_all(self) -> None:
		for device in self.manager.all_devices():
			device.trigger_alarm()
			self.gateway.send_frame(make_frame("alarm", device, scope="all"))
		self.append_log("全部设备触发报警")
		self.refresh_ui()

	def clear_alarm_all(self) -> None:
		for device in self.manager.all_devices():
			device.clear_alarm()
			self.gateway.send_frame(make_frame("clear_alarm", device, scope="all"))
		self.append_log("全部设备消除报警")
		self.refresh_ui()

	def offline_all(self) -> None:
		for device in self.manager.all_devices():
			device.go_offline("batch")
			self.gateway.send_frame(make_frame("offline", device, scope="all"))
		self.append_log("全部设备模拟失联")
		self.refresh_ui()

	def online_all(self) -> None:
		for device in self.manager.all_devices():
			device.go_online()
			self.gateway.send_frame(make_frame("online", device, scope="all"))
		self.append_log("全部设备恢复在线")
		self.refresh_ui()

	def on_tick(self) -> None:
		advance_simulation(self.manager)
		for device in advance_heartbeat(self.manager):
			self.append_log(f"DEV{device.device_id:03d} 心跳")
			self.gateway.send_frame(make_frame("heartbeat", device))
		selected_id = self.selected_device().device_id if self.selected_device() else None
		self.refresh_ui()
		if selected_id is not None:
			self.select_device(selected_id)


def run_gui() -> int:
	configure_qt_runtime()
	app = QApplication([])
	window = MainWindow()
	window.show()
	return app.exec_()


__all__ = ["MainWindow", "run_gui"]
