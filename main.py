from __future__ import annotations

import argparse

from utils.testing import demo, smoke_test, tcp_smoke_test
from ui.main_window import run_gui


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="多设备模拟器上位机")
	parser.add_argument("--demo", action="store_true", help="运行控制台模拟演示")
	parser.add_argument("--smoke-test", action="store_true", help="运行自动化冒烟测试")
	parser.add_argument("--tcp-smoke-test", action="store_true", help="运行 TCP 通信冒烟测试")
	args = parser.parse_args()

	if args.demo:
		demo()
	elif args.smoke_test:
		smoke_test()
	elif args.tcp_smoke_test:
		tcp_smoke_test()
	else:
		raise SystemExit(run_gui())
