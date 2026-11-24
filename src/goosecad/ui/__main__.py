"""Launch with python -m goosecad.ui [document.gcad]."""
import argparse
import sys
from PySide6.QtWidgets import QApplication
from goosecad.document.session import DocumentSession
from .main_window import MainWindow

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("document", nargs="?")
    args = parser.parse_args()
    app = QApplication([sys.argv[0]])
    session = DocumentSession.open(args.document) if args.document else None
    window = MainWindow(session)
    window.show()
    window.initialize_view()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
