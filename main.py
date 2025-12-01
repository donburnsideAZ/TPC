#!/usr/bin/env python3
"""
PTC - Pack Track Click
The packaging tool for people who just want to ship.

"I just want to hand someone an installer and say 'here, this works.'"
"""

import sys
import subprocess
import platform
from pathlib import Path

# Add the project directory to Python path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import (
    QApplication, QMessageBox, QDialog, QVBoxLayout, 
    QLabel, QPushButton, QHBoxLayout, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.main_window import MainWindow


def is_git_installed() -> bool:
    """Check if git is available on the system."""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False


class GitMissingDialog(QDialog):
    """
    Friendly dialog shown when git isn't installed.
    
    Explains what's needed and how to fix it — no jargon, no panic.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("One Quick Thing...")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Git isn't installed yet")
        header.setStyleSheet("font-size: 20px; font-weight: 600; color: #333;")
        layout.addWidget(header)
        
        # Explanation
        explanation = QLabel(
            "PTC uses Git behind the scenes to track your versions. "
            "Don't worry — you'll never have to touch it directly. "
            "We just need it installed so we can do the heavy lifting for you."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("font-size: 14px; color: #555; line-height: 1.5;")
        layout.addWidget(explanation)
        
        layout.addSpacing(10)
        
        # Platform-specific instructions
        system = platform.system()
        
        if system == "Darwin":  # macOS
            instructions = self.create_mac_instructions()
        elif system == "Windows":
            instructions = self.create_windows_instructions()
        else:  # Linux
            instructions = self.create_linux_instructions()
        
        layout.addWidget(instructions)
        
        layout.addSpacing(10)
        
        # What to do after
        after_label = QLabel(
            "Once you've installed Git, restart PTC and you'll be good to go!"
        )
        after_label.setWordWrap(True)
        after_label.setStyleSheet("font-size: 13px; color: #666; font-style: italic;")
        layout.addWidget(after_label)
        
        layout.addStretch()
        
        # Buttons
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)
        
        btn_layout.addStretch()
        
        btn_quit = QPushButton("Quit PTC")
        btn_quit.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #5aafff;
            }
        """)
        btn_quit.clicked.connect(self.accept)
        btn_layout.addWidget(btn_quit)
        
        layout.addWidget(btn_row)
    
    def create_mac_instructions(self) -> QWidget:
        """Create macOS-specific installation instructions."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        title = QLabel("On Mac, here's what to do:")
        title.setStyleSheet("font-size: 14px; font-weight: 600; color: #333;")
        layout.addWidget(title)
        
        step1 = QLabel("1. Open Terminal (search for it in Spotlight)")
        step1.setStyleSheet("font-size: 13px; color: #555;")
        layout.addWidget(step1)
        
        step2 = QLabel("2. Paste this command and press Enter:")
        step2.setStyleSheet("font-size: 13px; color: #555;")
        layout.addWidget(step2)
        
        command = QLabel("xcode-select --install")
        command.setStyleSheet("""
            font-size: 14px; 
            font-family: Monaco, monospace;
            background-color: #f5f5f5;
            padding: 12px 16px;
            border-radius: 6px;
            color: #333;
        """)
        command.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(command)
        
        step3 = QLabel("3. Click Install when prompted, then wait for it to finish")
        step3.setStyleSheet("font-size: 13px; color: #555;")
        layout.addWidget(step3)
        
        return container
    
    def create_windows_instructions(self) -> QWidget:
        """Create Windows-specific installation instructions."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        title = QLabel("On Windows, here's what to do:")
        title.setStyleSheet("font-size: 14px; font-weight: 600; color: #333;")
        layout.addWidget(title)
        
        step1 = QLabel("1. Go to:")
        step1.setStyleSheet("font-size: 13px; color: #555;")
        layout.addWidget(step1)
        
        url = QLabel("https://git-scm.com/download/windows")
        url.setStyleSheet("""
            font-size: 14px; 
            background-color: #f5f5f5;
            padding: 12px 16px;
            border-radius: 6px;
            color: #4a9eff;
        """)
        url.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(url)
        
        step2 = QLabel("2. Download and run the installer")
        step2.setStyleSheet("font-size: 13px; color: #555;")
        layout.addWidget(step2)
        
        step3 = QLabel("3. Use all the default options — just keep clicking Next")
        step3.setStyleSheet("font-size: 13px; color: #555;")
        layout.addWidget(step3)
        
        return container
    
    def create_linux_instructions(self) -> QWidget:
        """Create Linux-specific installation instructions."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        title = QLabel("On Linux, here's what to do:")
        title.setStyleSheet("font-size: 14px; font-weight: 600; color: #333;")
        layout.addWidget(title)
        
        step1 = QLabel("Open a terminal and run one of these:")
        step1.setStyleSheet("font-size: 13px; color: #555;")
        layout.addWidget(step1)
        
        ubuntu = QLabel("Ubuntu/Debian:  sudo apt install git")
        ubuntu.setStyleSheet("""
            font-size: 13px; 
            font-family: Monaco, monospace;
            background-color: #f5f5f5;
            padding: 10px 16px;
            border-radius: 6px;
            color: #333;
        """)
        ubuntu.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(ubuntu)
        
        fedora = QLabel("Fedora:  sudo dnf install git")
        fedora.setStyleSheet("""
            font-size: 13px; 
            font-family: Monaco, monospace;
            background-color: #f5f5f5;
            padding: 10px 16px;
            border-radius: 6px;
            color: #333;
        """)
        fedora.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(fedora)
        
        return container


def main():
    # Enable high DPI scaling
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("PTC")
    app.setApplicationDisplayName("PTC - Pack Track Click")
    app.setOrganizationName("PTC")
    
    # Set a clean, friendly default font
    font = QFont("SF Pro Display", 13)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    
    # Check for git before showing main window
    if not is_git_installed():
        dialog = GitMissingDialog()
        dialog.exec()
        sys.exit(0)
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
