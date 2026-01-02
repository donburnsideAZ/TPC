#!/usr/bin/env python3
"""
TPC - Track Pack Click v3.0
Simple versioning for people who just want to ship.

"I just want to hand someone an installer and say 'here, this works.'"

TPC 3.0: Simple folder-based snapshots. No Git complexity.
"""

# CRITICAL: These guards must be at the very top, before any other imports
# They prevent infinite window spawning when running as a frozen PyInstaller exe on Windows
import sys
import multiprocessing

def _is_frozen():
    """Check if we're running as a PyInstaller frozen executable."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# For PyInstaller multiprocessing support on Windows
if __name__ == "__main__":
    multiprocessing.freeze_support()

import platform
from pathlib import Path

# Add the project directory to Python path for local imports
sys.path.insert(0, str(Path(__file__).parent))

# Import version from core (single source of truth)
from core import __version__

from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import QLockFile
from PyQt6.QtGui import QFont, QPalette, QColor

from ui.main_window import MainWindow


def main():
    # Enable high DPI scaling
    app = QApplication(sys.argv)
    
    # === SINGLE INSTANCE CHECK ===
    lock_file_path = Path.home() / ".tpc" / "tpc.lock"
    lock_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    lock_file = QLockFile(str(lock_file_path))
    if not lock_file.tryLock(100):
        sys.exit(0)
    
    # Force light mode - TPC is designed for light mode only
    app.setStyle("Fusion")
    
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Link, QColor(74, 158, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(74, 158, 255))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(160, 160, 160))
    
    app.setPalette(palette)
    
    # Set application metadata
    app.setApplicationName("TPC")
    app.setApplicationDisplayName(f"TPC - Track Pack Click v{__version__}")
    app.setOrganizationName("TPC")
    
    # Set system font
    if platform.system() == "Darwin":
        font = QFont(".AppleSystemUIFont", 13)
    elif platform.system() == "Windows":
        font = QFont("Segoe UI", 10)
    else:
        font = QFont("Ubuntu", 11)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    
    # === FIRST RUN CHECK ===
    from core.config import is_first_run, complete_first_run
    
    if is_first_run():
        from ui.wizards.first_run import FirstRunWizard
        
        wizard = FirstRunWizard()
        if wizard.exec() == QDialog.DialogCode.Accepted:
            projects_path = wizard.get_projects_path()
            cloud_service = wizard.get_cloud_service()
            
            if projects_path:
                complete_first_run(projects_path, cloud_service)
        else:
            sys.exit(0)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
