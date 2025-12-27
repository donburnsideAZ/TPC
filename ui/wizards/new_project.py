"""
New Project Wizard for TPC.

A friendly, step-by-step flow for creating a new project:
1. What are you building? (name)
2. Tell me about it (optional description)
3. Where should it live? (location)

No jargon, no scary options. Just the essentials.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QFileDialog,
    QWidget, QStackedWidget, QMessageBox
)
from PyQt6.QtCore import Qt

from core.project import Project, DEFAULT_PROJECTS_ROOT


class NewProjectWizard(QDialog):
    """Wizard for creating a new project."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.created_project: Project | None = None
        self.selected_location = DEFAULT_PROJECTS_ROOT
        
        self.setWindowTitle("New Project")
        self.setModal(True)
        self.setMinimumSize(500, 450)
        self.resize(550, 500)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        # Header
        header = QLabel("Let's start something new")
        header.setObjectName("wizardHeader")
        layout.addWidget(header)
        
        # Project name
        name_section = QWidget()
        name_layout = QVBoxLayout(name_section)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(8)
        
        name_label = QLabel("What are you building?")
        name_label.setObjectName("fieldLabel")
        name_layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setObjectName("fieldInput")
        self.name_input.setPlaceholderText("My Awesome Tool")
        self.name_input.textChanged.connect(self.update_location_preview)
        name_layout.addWidget(self.name_input)
        
        layout.addWidget(name_section)
        
        # Description (optional)
        desc_section = QWidget()
        desc_layout = QVBoxLayout(desc_section)
        desc_layout.setContentsMargins(0, 0, 0, 0)
        desc_layout.setSpacing(8)
        
        desc_label = QLabel("What does it do? (optional)")
        desc_label.setObjectName("fieldLabel")
        desc_layout.addWidget(desc_label)
        
        self.desc_input = QTextEdit()
        self.desc_input.setObjectName("fieldInputMulti")
        self.desc_input.setPlaceholderText(
            "A quick description helps you remember what this is for later.\n"
            "Also useful if you're working with Claude or another AI assistant."
        )
        self.desc_input.setMaximumHeight(80)
        desc_layout.addWidget(self.desc_input)
        
        layout.addWidget(desc_section)
        
        # Location
        loc_section = QWidget()
        loc_layout = QVBoxLayout(loc_section)
        loc_layout.setContentsMargins(0, 0, 0, 0)
        loc_layout.setSpacing(8)
        
        loc_label = QLabel("Where should it live?")
        loc_label.setObjectName("fieldLabel")
        loc_layout.addWidget(loc_label)
        
        loc_row = QWidget()
        loc_row_layout = QHBoxLayout(loc_row)
        loc_row_layout.setContentsMargins(0, 0, 0, 0)
        loc_row_layout.setSpacing(8)
        
        self.location_preview = QLabel(str(DEFAULT_PROJECTS_ROOT / "My Awesome Tool"))
        self.location_preview.setObjectName("locationPreview")
        self.location_preview.setWordWrap(True)
        loc_row_layout.addWidget(self.location_preview, 1)
        
        btn_browse = QPushButton("Change")
        btn_browse.setObjectName("btnBrowse")
        btn_browse.clicked.connect(self.browse_location)
        loc_row_layout.addWidget(btn_browse)
        
        loc_layout.addWidget(loc_row)
        
        layout.addWidget(loc_section)
        
        layout.addStretch()
        
        # Buttons
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)
        
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_create = QPushButton("Create Project")
        btn_create.setObjectName("btnCreate")
        btn_create.clicked.connect(self.create_project)
        btn_layout.addWidget(btn_create)
        
        layout.addWidget(btn_row)
        
        self.apply_styles()
    
    def update_location_preview(self):
        """Update the location preview as name changes."""
        name = self.name_input.text().strip() or "My Awesome Tool"
        self.location_preview.setText(str(self.selected_location / name))
    
    def browse_location(self):
        """Let user choose a different location."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose Project Location",
            str(self.selected_location),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            self.selected_location = Path(folder)
            self.update_location_preview()
    
    def create_project(self):
        """Validate and create the project."""
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(
                self,
                "Name Required",
                "Every great project needs a name.\n\n"
                "Don't worry, you can always change it later."
            )
            self.name_input.setFocus()
            return
        
        # Check if project already exists
        project_path = self.selected_location / name
        if project_path.exists():
            QMessageBox.warning(
                self,
                "Already Exists",
                f"A project named '{name}' already exists at this location.\n\n"
                "Try a different name, or use 'Adopt' to work with the existing project."
            )
            return
        
        try:
            self.created_project = Project.create_new(
                name=name,
                location=self.selected_location,
                description=self.desc_input.toPlainText().strip()
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Something Went Wrong",
                f"Couldn't create the project:\n\n{e}\n\n"
                "Check that you have write access to the location."
            )
    
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            
            #wizardHeader {
                color: #333333;
                font-size: 22px;
                font-weight: 600;
            }
            
            #fieldLabel {
                color: #555555;
                font-size: 14px;
                font-weight: 500;
            }
            
            #fieldInput {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 10px 12px;
                color: #333333;
                font-size: 15px;
                min-height: 20px;
            }
            
            #fieldInput:focus {
                border-color: #4a9eff;
            }
            
            #fieldInputMulti {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 10px 12px;
                color: #333333;
                font-size: 14px;
            }
            
            #fieldInputMulti:focus {
                border-color: #4a9eff;
            }
            
            #locationPreview {
                color: #666666;
                font-size: 13px;
                background-color: #f5f5f5;
                padding: 10px 12px;
                border-radius: 6px;
            }
            
            #btnBrowse {
                background-color: #e8e8e8;
                color: #555555;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            
            #btnBrowse:hover {
                background-color: #d8d8d8;
            }
            
            #btnCancel {
                background-color: transparent;
                color: #666666;
                border: 1px solid #cccccc;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
            }
            
            #btnCancel:hover {
                background-color: #f0f0f0;
                color: #333333;
            }
            
            #btnCreate {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            
            #btnCreate:hover {
                background-color: #5aafff;
            }
            
            #btnCreate:pressed {
                background-color: #3a8eef;
            }
        """)
