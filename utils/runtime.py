from __future__ import annotations

import os
from pathlib import Path


def configure_qt_runtime() -> None:
	if os.name != "nt":
		return
	if os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH"):
		return
	try:
		import PyQt5

		plugin_dir = Path(PyQt5.__file__).resolve().parent / "Qt5" / "plugins" / "platforms"
		if plugin_dir.exists():
			os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugin_dir)
	except Exception:
		pass


__all__ = ["configure_qt_runtime"]
