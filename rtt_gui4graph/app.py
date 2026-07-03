from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RTT GUI4GRAPH")
    parser.add_argument("--mock", action="store_true", help="connect to mock source on start")
    args = parser.parse_args(argv)

    try:
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError:
        print("PySide6 is not installed. Run: python -m pip install -r requirements.txt", file=sys.stderr)
        return 2

    from rtt_gui4graph.ui.main_window import MainWindow

    app = QApplication(sys.argv[:1])
    window = MainWindow(auto_mock=args.mock)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
