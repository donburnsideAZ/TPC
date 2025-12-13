"""
Settings dialog for TPC.

Currently contains:
- GitHub authentication (Personal Access Token)

Future:
- Projects location
- Theme
- etc.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QWidget, QTabWidget,
    QMessageBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt

from core.github import (
    get_github_token,
    get_github_username,
    save_github_credentials,
    clear_github_credentials,
    has_github_credentials,
    validate_token
)


class SettingsDialog(QDialog):
    """TPC Settings dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("TPC Settings")
        self.setModal(True)
        self.setMinimumSize(550, 650)
        self.resize(600, 750)
        
        self.setup_ui()
        self.load_current_settings()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Tab widget for different settings sections
        tabs = QTabWidget()
        
        # GitHub tab
        github_tab = self.create_github_tab()
        tabs.addTab(github_tab, "GitHub")
        
        # About tab
        about_tab = self.create_about_tab()
        tabs.addTab(about_tab, "About")
        
        layout.addWidget(tabs)
        
        # Buttons
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #5aafff;
            }
        """)
        btn_layout.addWidget(btn_close)
        
        layout.addWidget(btn_row)
        
        self.apply_styles()
    
    def create_github_tab(self) -> QWidget:
        """Create the GitHub settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Status section
        self.status_group = QGroupBox("Connection Status")
        status_layout = QVBoxLayout(self.status_group)
        
        self.connection_status = QLabel("Checking...")
        self.connection_status.setStyleSheet("font-size: 14px; padding: 8px;")
        status_layout.addWidget(self.connection_status)
        
        layout.addWidget(self.status_group)
        
        # Credentials section
        creds_group = QGroupBox("Sign In with Personal Access Token")
        creds_layout = QVBoxLayout(creds_group)
        creds_layout.setSpacing(12)
        
        # Instructions
        instructions = QLabel(
            "To connect TPC to GitHub, you need a Personal Access Token:\n\n"
            "• Go to GitHub → Settings → Developer Settings → Personal Access Tokens → Tokens (classic)\n"
            "• Click 'Generate new token (classic)'\n"
            "• Name it something like 'TPC'\n"
            "• Set expiration to 90 days or 'No expiration' (you'll get a warning, it's fine)\n"
            "• Check the 'repo' scope\n"
            "• Generate and copy the token"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666666; font-size: 13px;")
        creds_layout.addWidget(instructions)
        
        # Direct link button
        link_btn = QPushButton("Open GitHub Token Settings")
        link_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #4a9eff;
                border: 1px solid #4a9eff;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #f0f7ff;
            }
        """)
        link_btn.clicked.connect(self.open_github_tokens)
        creds_layout.addWidget(link_btn)
        
        # Form
        form = QWidget()
        form_layout = QFormLayout(form)
        form_layout.setSpacing(12)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("your-github-username")
        self.username_input.setStyleSheet(self.input_style())
        form_layout.addRow("Username:", self.username_input)
        
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("ghp_xxxxxxxxxxxxxxxxxxxx")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setStyleSheet(self.input_style())
        form_layout.addRow("Token:", self.token_input)
        
        creds_layout.addWidget(form)
        
        # Action buttons
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)
        
        self.btn_test = QPushButton("Test Connection")
        self.btn_test.setStyleSheet("""
            QPushButton {
                background-color: #e8e8e8;
                color: #333333;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #d8d8d8;
            }
        """)
        self.btn_test.clicked.connect(self.test_connection)
        btn_layout.addWidget(self.btn_test)
        
        self.btn_save = QPushButton("Save Credentials")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3ddc81;
            }
        """)
        self.btn_save.clicked.connect(self.save_credentials)
        btn_layout.addWidget(self.btn_save)
        
        btn_layout.addStretch()
        
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #e74c3c;
                border: 1px solid #e74c3c;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #fef0ef;
            }
        """)
        self.btn_disconnect.clicked.connect(self.disconnect_github)
        btn_layout.addWidget(self.btn_disconnect)
        
        creds_layout.addWidget(btn_row)
        
        layout.addWidget(creds_group)
        layout.addStretch()
        
        return tab
    
    def create_about_tab(self) -> QWidget:
        """Create the About tab."""
        from core import __version__
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Logo/Title
        title = QLabel("TPC - Track Pack Click")
        title.setStyleSheet("font-size: 22px; font-weight: 600; color: #333;")
        layout.addWidget(title)
        
        version = QLabel(f"Version {__version__}")
        version.setStyleSheet("font-size: 14px; color: #666;")
        layout.addWidget(version)
        
        layout.addSpacing(16)
        
        tagline = QLabel("The packaging tool for people who just want to ship.")
        tagline.setStyleSheet("font-size: 14px; color: #444; font-style: italic;")
        tagline.setWordWrap(True)
        layout.addWidget(tagline)
        
        layout.addStretch()
        
        return tab
    
    def input_style(self) -> str:
        return """
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 10px 12px;
                color: #333333;
                font-size: 14px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #4a9eff;
            }
        """
    
    def load_current_settings(self):
        """Load and display current settings."""
        if has_github_credentials():
            username = get_github_username()
            self.username_input.setText(username or "")
            self.token_input.setText("••••••••••••••••")  # Don't show actual token
            self.connection_status.setText(f"✓ Connected as {username}")
            self.connection_status.setStyleSheet("font-size: 14px; padding: 8px; color: #27ae60;")
            self.btn_disconnect.setVisible(True)
        else:
            self.connection_status.setText("Not connected to GitHub")
            self.connection_status.setStyleSheet("font-size: 14px; padding: 8px; color: #888888;")
            self.btn_disconnect.setVisible(False)
    
    def open_github_tokens(self):
        """Open GitHub token settings in browser."""
        import webbrowser
        webbrowser.open("https://github.com/settings/tokens")
    
    def test_connection(self):
        """Test the entered credentials."""
        username = self.username_input.text().strip()
        token = self.token_input.text().strip()
        
        if not username:
            QMessageBox.warning(self, "Missing Username", "Please enter your GitHub username.")
            return
        
        if not token or token == "••••••••••••••••":
            # If they haven't changed the masked token, use stored one
            stored_token = get_github_token()
            if stored_token:
                token = stored_token
            else:
                QMessageBox.warning(self, "Missing Token", "Please enter your Personal Access Token.")
                return
        
        self.btn_test.setEnabled(False)
        self.btn_test.setText("Testing...")
        
        # Run validation
        success, message = validate_token(username, token)
        
        self.btn_test.setEnabled(True)
        self.btn_test.setText("Test Connection")
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.connection_status.setText(f"✓ {message}")
            self.connection_status.setStyleSheet("font-size: 14px; padding: 8px; color: #27ae60;")
        else:
            QMessageBox.warning(self, "Connection Failed", message)
    
    def save_credentials(self):
        """Save the entered credentials."""
        username = self.username_input.text().strip()
        token = self.token_input.text().strip()
        
        if not username:
            QMessageBox.warning(self, "Missing Username", "Please enter your GitHub username.")
            return
        
        if not token or token == "••••••••••••••••":
            # Check if we have stored token
            stored_token = get_github_token()
            if stored_token and has_github_credentials():
                # Just updating username
                token = stored_token
            else:
                QMessageBox.warning(self, "Missing Token", "Please enter your Personal Access Token.")
                return
        
        # Validate before saving
        self.btn_save.setEnabled(False)
        self.btn_save.setText("Validating...")
        
        success, message = validate_token(username, token)
        
        if success:
            save_github_credentials(username, token)
            
            self.btn_save.setText("Saved!")
            self.connection_status.setText(f"✓ {message}")
            self.connection_status.setStyleSheet("font-size: 14px; padding: 8px; color: #27ae60;")
            self.token_input.setText("••••••••••••••••")
            self.btn_disconnect.setVisible(True)
            
            QMessageBox.information(
                self, 
                "Connected!", 
                f"{message}\n\nYou can now push and pull from GitHub."
            )
        else:
            QMessageBox.warning(self, "Invalid Credentials", message)
        
        self.btn_save.setEnabled(True)
        self.btn_save.setText("Save Credentials")
    
    def disconnect_github(self):
        """Remove stored GitHub credentials."""
        reply = QMessageBox.question(
            self,
            "Disconnect GitHub?",
            "This will remove your stored GitHub credentials.\n\n"
            "You'll need to enter them again to push or pull.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            clear_github_credentials()
            self.username_input.clear()
            self.token_input.clear()
            self.connection_status.setText("Not connected to GitHub")
            self.connection_status.setStyleSheet("font-size: 14px; padding: 8px; color: #888888;")
            self.btn_disconnect.setVisible(False)
    
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #ffffff;
            }
            
            QTabBar::tab {
                background-color: #f1f1f1;
                color: #666666;
                padding: 10px 20px;
                border: 1px solid #e0e0e0;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }
            
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #333333;
            }
            
            QGroupBox {
                font-weight: 600;
                color: #333333;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
