from __future__ import annotations

import time
from typing import Dict, Optional

from models.device import Device


def make_frame(frame_type: str, device: Optional[Device] = None, **extra: object) -> Dict[str, object]:
	frame: Dict[str, object] = {
		"type": frame_type,
		"timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
	}
	if device is not None:
		frame["device"] = device.snapshot()
	if extra:
		frame.update(extra)
	return frame


__all__ = ["make_frame"]
