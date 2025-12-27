"""
Adopt Project Wizard for TPC.

The rescue mission - taking that Downloads folder script and giving
it a proper home. Zero judgment, maximum helpfulness.

Flow:
1. Where's your script? (file picker, defaults to Downloads)
2. What should we call this project? (auto-suggest from filename)
3. Where do you want to keep it? (default to TPC Projects)
4. Any other files to bring along? (optional)
5. Done! First version saved.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QWidget,
    QCheckBox, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt

from core.project import Project, DEFAULT_PROJECTS_ROOT


def suggest_name_from_file(filepath: Path) -> str:
    """
    Generate a friendly project name from a filename.
    
    'invoice_thing_v3_FINAL.py' -> 'Invoice Thing'
    'my_cool_script.py' -> 'My Cool Script'
    """
    name = filepath.stem
    
    # Remove common suffixes
    for suffix in ['_final', '_FINAL', '_v1', '_v2', '_v3', '_old', '_new', '_backup']:
        name = name.replace(suffix, '')
    
    # Remove version numbers at the end
    import re
    name = re.sub(r'[_-]?\d+$', '', name)
    
    # Convert to title case with spaces
    name = name.replace('_', ' ').replace('-', ' ')
    name = ' '.join(word.capitalize() for word in name.split())
    
    return name.strip() or "My Project"


class AdoptProjectWizard(QDialog):
    """Wizard for adopting an existing script into a TPC project."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.adopted_project: Project | None = None
        self.source_file: Path | None = None
        self.selected_location = DEFAULT_PROJECTS_ROOT
        self.additional_files: list[Path] = []
        
        self.setWindowTitle("Adopt Script")
        self.setModal(True)
        self.setMinimumSize(550, 550)
        self.resize(600, 600)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Let's give your script a proper home")
        header.setObjectName("wizardHeader")
        layout.addWidget(header)
        
        subheader = QLabel(
            "No judgment about the Downloads folder. We've all been there."
        )
        subheader.setObjectName("wizardSubheader")
        layout.addWidget(subheader)
        
        # Step 1: Select file
        file_section = QWidget()
        file_layout = QVBoxLayout(file_section)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(8)
        
        file_label = QLabel("Where's your script?")
        file_label.setObjectName("fieldLabel")
        file_layout.addWidget(file_label)
        
        file_row = QWidget()
        file_row_layout = QHBoxLayout(file_row)
        file_row_layout.setContentsMargins(0, 0, 0, 0)
        file_row_layout.setSpacing(8)
        
        self.file_display = QLabel("No file selected")
        self.file_display.setObjectName("fileDisplay")
        self.file_display.setWordWrap(True)
        file_row_layout.addWidget(self.file_display, 1)
        
        btn_browse_file = QPushButton("Browse")
        btn_browse_file.setObjectName("btnBrowse")
        btn_browse_file.clicked.connect(self.browse_file)
        file_row_layout.addWidget(btn_browse_file)
        
        file_layout.addWidget(file_row)
        layout.addWidget(file_section)
        
        # Step 2: Project name
        name_section = QWidget()
        name_layout = QVBoxLayout(name_section)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(8)
        
        name_label = QLabel("What should we call this project?")
        name_label.setObjectName("fieldLabel")
        name_layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setObjectName("fieldInput")
        self.name_input.setPlaceholderText("Project Name")
        self.name_input.textChanged.connect(self.update_location_preview)
        name_layout.addWidget(self.name_input)
        
        layout.addWidget(name_section)
        
        # Step 3: Location
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
        
        self.location_preview = QLabel(str(DEFAULT_PROJECTS_ROOT))
        self.location_preview.setObjectName("locationPreview")
        self.location_preview.setWordWrap(True)
        loc_row_layout.addWidget(self.location_preview, 1)
        
        btn_browse_loc = QPushButton("Change")
        btn_browse_loc.setObjectName("btnBrowse")
        btn_browse_loc.clicked.connect(self.browse_location)
        loc_row_layout.addWidget(btn_browse_loc)
        
        loc_layout.addWidget(loc_row)
        layout.addWidget(loc_section)
        
        # Step 4: Additional files (optional)
        extra_section = QWidget()
        extra_layout = QVBoxLayout(extra_section)
        extra_layout.setContentsMargins(0, 0, 0, 0)
        extra_layout.setSpacing(8)
        
        extra_label = QLabel("Any other files to bring along? (optional)")
        extra_label.setObjectName("fieldLabel")
        extra_layout.addWidget(extra_label)
        
        self.extra_list = QListWidget()
        self.extra_list.setObjectName("extraList")
        self.extra_list.setMaximumHeight(80)
        extra_layout.addWidget(self.extra_list)
        
        extra_btn_row = QWidget()
        extra_btn_layout = QHBoxLayout(extra_btn_row)
        extra_btn_layout.setContentsMargins(0, 0, 0, 0)
        extra_btn_layout.setSpacing(8)
        
        btn_add_files = QPushButton("+ Add Files")
        btn_add_files.setObjectName("btnSmall")
        btn_add_files.clicked.connect(self.add_extra_files)
        extra_btn_layout.addWidget(btn_add_files)
        
        btn_remove = QPushButton("Remove Selected")
        btn_remove.setObjectName("btnSmall")
        btn_remove.clicked.connect(self.remove_extra_file)
        extra_btn_layout.addWidget(btn_remove)
        
        extra_btn_layout.addStretch()
        extra_layout.addWidget(extra_btn_row)
        
        layout.addWidget(extra_section)
        
        # Delete original option
        self.delete_original = QCheckBox("Delete original from Downloads after copying")
        self.delete_original.setObjectName("deleteCheckbox")
        layout.addWidget(self.delete_original)
        
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
        
        btn_adopt = QPushButton("Adopt Project")
        btn_adopt.setObjectName("btnCreate")
        btn_adopt.clicked.connect(self.adopt_project)
        btn_layout.addWidget(btn_adopt)
        
        layout.addWidget(btn_row)
        
        self.apply_styles()
    
    def browse_file(self):
        """Open file picker, defaulting to Downloads."""
        downloads = Path.home() / "Downloads"
        start_dir = str(downloads) if downloads.exists() else str(Path.home())
        
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Python Script",
            start_dir,
            "Python Files (*.py *.pyw);;All Files (*)"
        )
        
        if filepath:
            self.source_file = Path(filepath)
            self.file_display.setText(str(self.source_file))
            
            # Auto-suggest project name
            suggested = suggest_name_from_file(self.source_file)
            self.name_input.setText(suggested)
            self.update_location_preview()
    
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
    
    def update_location_preview(self):
        """Update the location preview as name changes."""
        name = self.name_input.text().strip() or "Project Name"
        self.location_preview.setText(str(self.selected_location / name))
    
    def add_extra_files(self):
        """Add additional files to bring along."""
        start_dir = str(self.source_file.parent) if self.source_file else str(Path.home())
        
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Additional Files",
            start_dir,
            "All Files (*)"
        )
        
        for f in files:
            path = Path(f)
            if path not in self.additional_files and path != self.source_file:
                self.additional_files.append(path)
                self.extra_list.addItem(path.name)
    
    def remove_extra_file(self):
        """Remove selected file from the additional files list."""
        current = self.extra_list.currentRow()
        if current >= 0:
            self.extra_list.takeItem(current)
            self.additional_files.pop(current)
    
    def adopt_project(self):
        """Validate and adopt the project."""
        if not self.source_file:
            QMessageBox.warning(
                self,
                "No File Selected",
                "Please select the Python script you want to adopt."
            )
            return
        
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                "Name Required",
                "Every project needs a name.\n\n"
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
                "Try a different name."
            )
            return
        
        try:
            self.adopted_project = Project.adopt(
                source_file=self.source_file,
                name=name,
                location=self.selected_location,
                additional_files=self.additional_files if self.additional_files else None,
                delete_original=self.delete_original.isChecked()
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Something Went Wrong",
                f"Couldn't adopt the project:\n\n{e}\n\n"
                "Check that you have access to both the source and destination."
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
            
            #wizardSubheader {
                color: #888888;
                font-size: 14px;
                margin-bottom: 8px;
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
            
            #fileDisplay {
                color: #666666;
                font-size: 13px;
                background-color: #f5f5f5;
                padding: 10px 12px;
                border-radius: 6px;
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
            
            #extraList {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                color: #333333;
                font-size: 13px;
            }
            
            #btnSmall {
                background-color: transparent;
                color: #666666;
                border: 1px solid #cccccc;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            
            #btnSmall:hover {
                background-color: #f0f0f0;
                color: #333333;
            }
            
            #deleteCheckbox {
                color: #666666;
                font-size: 13px;
            }
            
            #deleteCheckbox::indicator {
                width: 16px;
                height: 16px;
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
