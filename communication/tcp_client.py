from __future__ import annotations

import json
from typing import Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtNetwork import QAbstractSocket, QTcpSocket


class GatewayClient(QObject):
	connectedChanged = pyqtSignal(bool)
	logMessage = pyqtSignal(str)
	frameReceived = pyqtSignal(dict)
	stateChanged = pyqtSignal(str)

	def __init__(self, parent: Optional[QObject] = None) -> None:
		super().__init__(parent)
		self._socket = QTcpSocket(self)
		self._buffer = bytearray()
		self._socket.connected.connect(self._on_connected)
		self._socket.disconnected.connect(self._on_disconnected)
		self._socket.readyRead.connect(self._on_ready_read)
		self._socket.errorOccurred.connect(self._on_error)

	@property
	def is_connected(self) -> bool:
		return self._socket.state() == QAbstractSocket.ConnectedState

	def connect_to_host(self, host: str, port: int) -> None:
		if self._socket.state() != QAbstractSocket.UnconnectedState:
			self._socket.abort()
		self.logMessage.emit(f"连接网关 {host}:{port}")
		self._socket.connectToHost(host, port)

	def disconnect(self) -> None:
		if self._socket.state() != QAbstractSocket.UnconnectedState:
			self.logMessage.emit("主动断开网关连接")
			self._socket.disconnectFromHost()

	def send_frame(self, payload: Dict[str, object]) -> None:
		data = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
		if not self.is_connected:
			self.logMessage.emit(f"未连接，丢弃上报: {payload.get('type', 'unknown')}")
			return
		self._socket.write(data)
		self._socket.flush()

	def _on_connected(self) -> None:
		self.connectedChanged.emit(True)
		self.stateChanged.emit("已连接")
		self.logMessage.emit("网关连接成功")

	def _on_disconnected(self) -> None:
		self.connectedChanged.emit(False)
		self.stateChanged.emit("未连接")
		self.logMessage.emit("网关连接已断开")

	def _on_error(self, error: QAbstractSocket.SocketError) -> None:
		self.stateChanged.emit(f"错误: {self._socket.errorString()}")
		self.logMessage.emit(f"Socket错误: {self._socket.errorString()}")

	def _on_ready_read(self) -> None:
		self._buffer.extend(bytes(self._socket.readAll()))
		while True:
			line_end = self._buffer.find(b"\n")
			if line_end < 0:
				break
			raw_line = bytes(self._buffer[:line_end]).strip()
			del self._buffer[: line_end + 1]
			if not raw_line:
				continue
			try:
				frame = json.loads(raw_line.decode("utf-8"))
			except Exception as exc:
				self.logMessage.emit(f"接收无效数据: {exc}")
				continue
			self.frameReceived.emit(frame)


__all__ = ["GatewayClient"]
