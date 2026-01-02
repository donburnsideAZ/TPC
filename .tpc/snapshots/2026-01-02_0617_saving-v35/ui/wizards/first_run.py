"""
First Run Wizard for TPC 2.0.

Shown on first launch (or when no config exists) to help users
pick where their projects should live.

The goal: get them into a cloud folder so sync "just works" across machines.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QRadioButton, QButtonGroup, QWidget,
    QFileDialog, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt

from core.cloud import (
    CloudFolder, 
    detect_cloud_folders, 
    get_local_folder,
    ensure_projects_folder
)


class CloudFolderOption(QFrame):
    """A single cloud folder option in the picker."""
    
    def __init__(self, folder: CloudFolder, parent=None):
        super().__init__(parent)
        self.folder = folder
        
        self.setObjectName("cloudOption")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Radio button
        self.radio = QRadioButton()
        self.radio.setEnabled(folder.available)
        layout.addWidget(self.radio)
        
        # Service info
        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        # Service name
        name_label = QLabel(folder.service)
        name_label.setObjectName("serviceName")
        if not folder.available:
            name_label.setStyleSheet("color: #999999;")
        info_layout.addWidget(name_label)
        
        # Path hint
        if folder.service == "Local":
            path_text = "Won't sync between computers"
        else:
            path_text = "Syncs automatically"
        path_label = QLabel(path_text)
        path_label.setObjectName("servicePath")
        if not folder.available:
            path_label.setStyleSheet("color: #bbbbbb;")
        info_layout.addWidget(path_label)
        
        layout.addWidget(info, 1)
        
        # Status
        if folder.available:
            if folder.service == "Local":
                status = QLabel("")  # No status for local
            else:
                status = QLabel("✓ Found")
                status.setStyleSheet("color: #27ae60; font-size: 12px;")
        else:
            status = QLabel("Not installed")
            status.setStyleSheet("color: #999999; font-size: 12px;")
        layout.addWidget(status)
        
        # Click anywhere to select
        if folder.available:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def mousePressEvent(self, event):
        if self.folder.available:
            self.radio.setChecked(True)
        super().mousePressEvent(event)


class FirstRunWizard(QDialog):
    """
    First-run wizard for choosing project location.
    
    Shows available cloud folders and lets user pick one,
    or choose a custom location.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.selected_path: Path | None = None
        self.selected_service: str | None = None
        
        self.setWindowTitle("Welcome to TPC")
        self.setModal(True)
        self.setMinimumSize(500, 450)
        self.resize(550, 500)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("Where should TPC keep your projects?")
        header.setObjectName("wizardHeader")
        layout.addWidget(header)
        
        # Subheader
        subheader = QLabel(
            "Pick a cloud folder and your projects will automatically "
            "sync across all your computers."
        )
        subheader.setObjectName("wizardSubheader")
        subheader.setWordWrap(True)
        layout.addWidget(subheader)
        
        layout.addSpacing(8)
        
        # Cloud folder options
        self.button_group = QButtonGroup(self)
        self.options: list[CloudFolderOption] = []
        
        # Get cloud folders
        cloud_folders = detect_cloud_folders()
        
        # Add available cloud folders first
        available_folders = [f for f in cloud_folders if f.available]
        unavailable_folders = [f for f in cloud_folders if not f.available]
        
        first_available_set = False
        
        if available_folders:
            for folder in available_folders:
                option = CloudFolderOption(folder)
                self.button_group.addButton(option.radio)
                self.options.append(option)
                layout.addWidget(option)
                
                # Select first available by default
                if not first_available_set:
                    option.radio.setChecked(True)
                    first_available_set = True
        
        # Show unavailable as disabled (collapsed)
        if unavailable_folders:
            unavailable_label = QLabel("Not installed on this computer:")
            unavailable_label.setObjectName("sectionLabelDim")
            layout.addWidget(unavailable_label)
            
            for folder in unavailable_folders:
                option = CloudFolderOption(folder)
                self.options.append(option)
                layout.addWidget(option)
        
        # Separator
        layout.addSpacing(8)
        
        # Local option
        local_folder = get_local_folder()
        local_option = CloudFolderOption(local_folder)
        self.button_group.addButton(local_option.radio)
        self.options.append(local_option)
        layout.addWidget(local_option)
        
        # If no cloud folders available, select local by default
        if not first_available_set:
            local_option.radio.setChecked(True)
        
        layout.addStretch()
        
        # Tip
        tip = QLabel(
            "💡 You can change this later in Settings"
        )
        tip.setObjectName("tipLabel")
        layout.addWidget(tip)
        
        layout.addSpacing(8)
        
        # Buttons row
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)
        
        # Custom location link
        btn_custom = QPushButton("Choose different folder...")
        btn_custom.setObjectName("btnCustom")
        btn_custom.clicked.connect(self.choose_custom_location)
        btn_layout.addWidget(btn_custom)
        
        btn_layout.addStretch()
        
        # Continue button
        btn_continue = QPushButton("Let's Go")
        btn_continue.setObjectName("btnContinue")
        btn_continue.clicked.connect(self.on_continue)
        btn_layout.addWidget(btn_continue)
        
        layout.addWidget(btn_row)
        
        self.apply_styles()
    
    def choose_custom_location(self):
        """Let user pick a custom folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose Projects Location",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            custom_path = Path(folder)
            
            # Create TPC Projects subfolder
            success, message = ensure_projects_folder(custom_path)
            
            if success:
                self.selected_path = custom_path / "TPC Projects"
                self.selected_service = None  # Custom location
                self.accept()
            else:
                QMessageBox.warning(
                    self,
                    "Couldn't Create Folder",
                    f"{message}\n\nTry choosing a different location."
                )
    
    def on_continue(self):
        """Handle the continue button."""
        # Find selected option
        for option in self.options:
            if option.radio.isChecked():
                self.selected_path = option.folder.path
                self.selected_service = option.folder.service if option.folder.service != "Local" else None
                break
        
        if not self.selected_path:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select where you'd like to keep your projects."
            )
            return
        
        # Ensure the TPC Projects folder can be created
        success, message = ensure_projects_folder(self.selected_path)
        
        if success:
            # Update selected_path to include TPC Projects
            self.selected_path = self.selected_path / "TPC Projects"
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Couldn't Create Folder",
                f"{message}\n\nTry choosing a different location."
            )
    
    def get_projects_path(self) -> Path | None:
        """Get the full path to the TPC Projects folder."""
        return self.selected_path
    
    def get_cloud_service(self) -> str | None:
        """Get the name of the selected cloud service, or None if local/custom."""
        return self.selected_service
    
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            
            #wizardHeader {
                color: #222222;
                font-size: 22px;
                font-weight: 600;
            }
            
            #wizardSubheader {
                color: #666666;
                font-size: 14px;
                line-height: 1.4;
            }
            
            #sectionLabelDim {
                color: #999999;
                font-size: 12px;
                margin-top: 8px;
                margin-bottom: 4px;
            }
            
            #cloudOption {
                background-color: #f8f8f8;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
            }
            
            #cloudOption:hover {
                background-color: #f0f0f0;
                border-color: #d0d0d0;
            }
            
            #serviceName {
                color: #333333;
                font-size: 15px;
                font-weight: 500;
            }
            
            #servicePath {
                color: #888888;
                font-size: 12px;
            }
            
            #tipLabel {
                color: #888888;
                font-size: 13px;
            }
            
            #btnCustom {
                background-color: transparent;
                color: #666666;
                border: none;
                padding: 8px 0;
                font-size: 13px;
                text-align: left;
            }
            
            #btnCustom:hover {
                color: #4a9eff;
            }
            
            #btnContinue {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 12px 28px;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 500;
            }
            
            #btnContinue:hover {
                background-color: #5aafff;
            }
            
            #btnContinue:pressed {
                background-color: #3a8eef;
            }
            
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
            
            QRadioButton::indicator:checked {
                background-color: #4a9eff;
                border: 2px solid #4a9eff;
                border-radius: 9px;
            }
            
            QRadioButton::indicator:unchecked {
                background-color: #ffffff;
                border: 2px solid #cccccc;
                border-radius: 9px;
            }
        """)
