"""
Pack Workspace for TPC.

The full-screen workspace for building distributable apps.
Shown when user clicks "Build" in the sidebar.

Contains:
- Dependency scanning and requirements.txt management
- Environment setup (venv creation and package installation)
- Icon picker and conversion (future)
- Build options and PyInstaller integration (future)
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QLineEdit,
    QFileDialog, QCheckBox, QMessageBox, QSizePolicy,
    QProgressBar, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QPixmap

from core.project import Project
from core.deps import DependencyDetective, ScanResult, generate_requirements, compare_requirements
from core.venv import EnvironmentWrangler, VenvResult, InstallProgress
from core.icons import IconAlchemist, ImageInfo
from core.build import BuildOrchestrator, BuildResult, BuildProgress


class DependencyScanWorker(QThread):
    """Background worker for scanning dependencies."""
    
    finished = pyqtSignal(object)  # Emits ScanResult
    error = pyqtSignal(str)
    
    def __init__(self, project_path: Path):
        super().__init__()
        self.project_path = project_path
    
    def run(self):
        try:
            detective = DependencyDetective()
            result = detective.scan_project(self.project_path)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class EnvironmentWorker(QThread):
    """Background worker for environment setup."""
    
    progress = pyqtSignal(str)  # Status messages
    install_progress = pyqtSignal(object)  # InstallProgress objects
    finished = pyqtSignal(object)  # VenvResult
    error = pyqtSignal(str)
    
    def __init__(self, project_name: str, packages: list[str], import_modules: list[str] | None = None):
        super().__init__()
        self.project_name = project_name
        self.packages = packages  # pip package names for installation
        # import names for verification (if not provided, skip verification)
        self.import_modules = import_modules if import_modules else []
    
    def run(self):
        try:
            wrangler = EnvironmentWrangler()
            
            # Step 1: Create venv
            self.progress.emit("Creating virtual environment...")
            result = wrangler.create_venv(self.project_name)
            
            if not result.success:
                self.finished.emit(result)
                return
            
            # Step 2: Install packages
            if self.packages:
                self.progress.emit(f"Installing {len(self.packages)} package(s)...")
                
                def on_progress(p: InstallProgress):
                    self.install_progress.emit(p)
                
                result = wrangler.install_packages(
                    self.project_name, 
                    self.packages,
                    progress_callback=on_progress
                )
                
                if not result.success:
                    self.finished.emit(result)
                    return
            
            # Step 3: Verify imports (only if we have import module names)
            if self.import_modules:
                self.progress.emit("Verifying installations...")
                verify_result = wrangler.verify_imports(self.project_name, self.import_modules)
                
                if not verify_result.success:
                    # Verification failed, but packages installed - report as partial success
                    self.finished.emit(VenvResult(
                        success=True,  # Don't block on verify failures
                        message=f"Environment ready (some imports couldn't be verified)",
                        details=verify_result.details
                    ))
                    return
            
            # Report final success with size info
            size = wrangler.get_venv_size(self.project_name)
            size_str = wrangler.format_size(size) if size else "unknown size"
            
            self.finished.emit(VenvResult(
                success=True,
                message=f"Environment ready ({size_str})",
                details=f"Installed {len(self.packages)} package(s)"
            ))
                
        except Exception as e:
            self.error.emit(str(e))


class BuildWorker(QThread):
    """Background worker for building the application."""
    
    progress = pyqtSignal(object)  # BuildProgress objects
    finished = pyqtSignal(object)  # BuildResult
    error = pyqtSignal(str)
    
    def __init__(
        self,
        project_path: Path,
        project_name: str,
        main_file: str,
        app_name: str,
        onefile: bool,
        windowed: bool,
        icon_path: Path | None,
        packages: list[str]
    ):
        super().__init__()
        self.project_path = project_path
        self.project_name = project_name
        self.main_file = main_file
        self.app_name = app_name
        self.onefile = onefile
        self.windowed = windowed
        self.icon_path = icon_path
        self.packages = packages
    
    def run(self):
        try:
            orchestrator = BuildOrchestrator()
            
            def on_progress(p: BuildProgress):
                self.progress.emit(p)
            
            result = orchestrator.build(
                project_path=self.project_path,
                project_name=self.project_name,
                main_file=self.main_file,
                app_name=self.app_name,
                onefile=self.onefile,
                windowed=self.windowed,
                icon_path=self.icon_path,
                packages=self.packages,
                progress_callback=on_progress
            )
            
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))


class PackWorkspace(QWidget):
    """
    Full workspace for Pack (build/distribution) features.
    
    Replaces the main workspace when "Build" is clicked.
    """
    
    back_clicked = pyqtSignal()  # Emitted when user wants to go back to project
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: Project | None = None
        self.scan_result: ScanResult | None = None
        self.worker: DependencyScanWorker | None = None
        self.env_worker: EnvironmentWorker | None = None
        self.build_worker: BuildWorker | None = None
        
        # Icon state
        self.icon_path: Path | None = None
        self.icon_alchemist = IconAlchemist()
        
        # Build state
        self.build_orchestrator = BuildOrchestrator()
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)
        
        # === HEADER ===
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Back button
        self.btn_back = QPushButton("← Back to Project")
        self.btn_back.setObjectName("btnBack")
        self.btn_back.clicked.connect(self.back_clicked.emit)
        header_layout.addWidget(self.btn_back)
        
        header_layout.addStretch()
        
        # Project name
        self.project_name = QLabel("Build for Distribution")
        self.project_name.setObjectName("packHeader")
        header_layout.addWidget(self.project_name)
        
        layout.addWidget(header)
        
        # === NO PROJECT MESSAGE ===
        self.no_project_msg = QLabel(
            "Select a project from the sidebar first,\n"
            "then click Build to package it for distribution."
        )
        self.no_project_msg.setObjectName("noProjectMsg")
        self.no_project_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.no_project_msg)
        
        # === MAIN CONTENT (hidden until project selected) ===
        self.main_content = QWidget()
        main_layout = QVBoxLayout(self.main_content)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)
        
        # === TWO COLUMN LAYOUT ===
        columns = QSplitter(Qt.Orientation.Horizontal)
        columns.setChildrenCollapsible(False)
        
        # === LEFT COLUMN ===
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 12, 0)
        left_layout.setSpacing(16)
        
        # --- DEPENDENCIES SECTION ---
        deps_section = QFrame()
        deps_section.setObjectName("packSection")
        deps_layout = QVBoxLayout(deps_section)
        deps_layout.setContentsMargins(20, 16, 20, 16)
        deps_layout.setSpacing(12)
        
        # Section header
        deps_header = QWidget()
        deps_header_layout = QHBoxLayout(deps_header)
        deps_header_layout.setContentsMargins(0, 0, 0, 0)
        
        deps_title = QLabel("Dependencies")
        deps_title.setObjectName("sectionTitle")
        deps_header_layout.addWidget(deps_title)
        
        deps_header_layout.addStretch()
        
        self.btn_scan = QPushButton("Scan Project")
        self.btn_scan.setObjectName("actionButton")
        self.btn_scan.clicked.connect(self.on_scan_dependencies)
        deps_header_layout.addWidget(self.btn_scan)
        
        deps_layout.addWidget(deps_header)
        
        # Scan results
        self.deps_status = QLabel("Click 'Scan Project' to detect third-party packages")
        self.deps_status.setObjectName("statusText")
        deps_layout.addWidget(self.deps_status)
        
        # Package list
        self.package_display = QLabel("")
        self.package_display.setObjectName("packageDisplay")
        self.package_display.setWordWrap(True)
        self.package_display.hide()
        deps_layout.addWidget(self.package_display)
        
        # Requirements actions
        self.deps_actions = QWidget()
        self.deps_actions.hide()
        deps_actions_layout = QHBoxLayout(self.deps_actions)
        deps_actions_layout.setContentsMargins(0, 8, 0, 0)
        deps_actions_layout.setSpacing(12)
        
        self.btn_save_reqs = QPushButton("Save requirements.txt")
        self.btn_save_reqs.setObjectName("secondaryButton")
        self.btn_save_reqs.clicked.connect(self.on_save_requirements)
        deps_actions_layout.addWidget(self.btn_save_reqs)
        
        deps_actions_layout.addStretch()
        deps_layout.addWidget(self.deps_actions)
        
        left_layout.addWidget(deps_section)
        
        # --- ENVIRONMENT SECTION ---
        env_section = QFrame()
        env_section.setObjectName("packSection")
        env_layout = QVBoxLayout(env_section)
        env_layout.setContentsMargins(20, 16, 20, 16)
        env_layout.setSpacing(12)
        
        # Section header
        env_header = QWidget()
        env_header_layout = QHBoxLayout(env_header)
        env_header_layout.setContentsMargins(0, 0, 0, 0)
        
        env_title = QLabel("Build Environment")
        env_title.setObjectName("sectionTitle")
        env_header_layout.addWidget(env_title)
        
        env_header_layout.addStretch()
        
        self.btn_setup_env = QPushButton("Setup Environment")
        self.btn_setup_env.setObjectName("actionButton")
        self.btn_setup_env.clicked.connect(self.on_setup_environment)
        self.btn_setup_env.setEnabled(False)  # Enabled after scan
        env_header_layout.addWidget(self.btn_setup_env)
        
        env_layout.addWidget(env_header)
        
        # Environment status
        self.env_status = QLabel("Scan dependencies first, then set up the build environment")
        self.env_status.setObjectName("statusText")
        env_layout.addWidget(self.env_status)
        
        # Progress bar (hidden by default)
        self.env_progress = QProgressBar()
        self.env_progress.setObjectName("envProgress")
        self.env_progress.setTextVisible(True)
        self.env_progress.hide()
        env_layout.addWidget(self.env_progress)
        
        # Environment details (hidden by default)
        self.env_details = QLabel("")
        self.env_details.setObjectName("envDetails")
        self.env_details.setWordWrap(True)
        self.env_details.hide()
        env_layout.addWidget(self.env_details)
        
        # Environment actions (hidden by default)
        self.env_actions = QWidget()
        self.env_actions.hide()
        env_actions_layout = QHBoxLayout(self.env_actions)
        env_actions_layout.setContentsMargins(0, 8, 0, 0)
        env_actions_layout.setSpacing(12)
        
        self.btn_rebuild_env = QPushButton("Rebuild Environment")
        self.btn_rebuild_env.setObjectName("secondaryButton")
        self.btn_rebuild_env.clicked.connect(self.on_rebuild_environment)
        env_actions_layout.addWidget(self.btn_rebuild_env)
        
        self.btn_delete_env = QPushButton("Delete Environment")
        self.btn_delete_env.setObjectName("secondaryButtonDanger")
        self.btn_delete_env.clicked.connect(self.on_delete_environment)
        env_actions_layout.addWidget(self.btn_delete_env)
        
        env_actions_layout.addStretch()
        env_layout.addWidget(self.env_actions)
        
        left_layout.addWidget(env_section)
        left_layout.addStretch()
        
        columns.addWidget(left_column)
        
        # === RIGHT COLUMN ===
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(12, 0, 0, 0)
        right_layout.setSpacing(16)
        
        # --- BUILD SECTION ---
        build_section = QFrame()
        build_section.setObjectName("packSection")
        build_layout = QVBoxLayout(build_section)
        build_layout.setContentsMargins(20, 16, 20, 16)
        build_layout.setSpacing(12)
        
        build_title = QLabel("Build Application")
        build_title.setObjectName("sectionTitle")
        build_layout.addWidget(build_title)
        
        # Icon row
        icon_row = QWidget()
        icon_row_layout = QHBoxLayout(icon_row)
        icon_row_layout.setContentsMargins(0, 0, 0, 0)
        icon_row_layout.setSpacing(16)
        
        # Icon preview placeholder
        self.icon_preview = QLabel("")
        self.icon_preview.setObjectName("iconPreview")
        self.icon_preview.setFixedSize(64, 64)
        self.icon_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_preview.setScaledContents(False)
        icon_row_layout.addWidget(self.icon_preview)
        
        # Icon info
        icon_info = QWidget()
        icon_info_layout = QVBoxLayout(icon_info)
        icon_info_layout.setContentsMargins(0, 0, 0, 0)
        icon_info_layout.setSpacing(4)
        
        icon_label = QLabel("App Icon")
        icon_label.setObjectName("fieldLabel")
        icon_info_layout.addWidget(icon_label)
        
        self.btn_choose_icon = QPushButton("Choose Image...")
        self.btn_choose_icon.setObjectName("secondaryButton")
        self.btn_choose_icon.clicked.connect(self.on_choose_icon)
        icon_info_layout.addWidget(self.btn_choose_icon)
        
        # Icon warning (hidden by default)
        self.icon_warning = QLabel("")
        self.icon_warning.setObjectName("iconWarning")
        self.icon_warning.setWordWrap(True)
        self.icon_warning.hide()
        icon_info_layout.addWidget(self.icon_warning)
        
        icon_row_layout.addWidget(icon_info)
        icon_row_layout.addStretch()
        build_layout.addWidget(icon_row)
        
        # App name
        name_row = QWidget()
        name_row_layout = QHBoxLayout(name_row)
        name_row_layout.setContentsMargins(0, 0, 0, 0)
        name_row_layout.setSpacing(12)
        
        name_label = QLabel("App Name:")
        name_label.setObjectName("fieldLabel")
        name_label.setFixedWidth(80)
        name_row_layout.addWidget(name_label)
        
        self.app_name_input = QLineEdit()
        self.app_name_input.setObjectName("fieldInput")
        self.app_name_input.setPlaceholderText("My App")
        name_row_layout.addWidget(self.app_name_input)
        
        build_layout.addWidget(name_row)
        
        # Build options
        options_label = QLabel("Build Options")
        options_label.setObjectName("fieldLabel")
        build_layout.addWidget(options_label)
        
        self.opt_onefile = QCheckBox("Single file (recommended)")
        self.opt_onefile.setChecked(True)
        self.opt_onefile.setEnabled(True)
        build_layout.addWidget(self.opt_onefile)
        
        self.opt_windowed = QCheckBox("No console window (GUI app)")
        self.opt_windowed.setChecked(True)
        self.opt_windowed.setEnabled(True)
        build_layout.addWidget(self.opt_windowed)
        
        # Build buttons
        build_btn_row = QWidget()
        build_btn_layout = QHBoxLayout(build_btn_row)
        build_btn_layout.setContentsMargins(0, 12, 0, 0)
        build_btn_layout.setSpacing(12)
        
        # Show appropriate button based on platform
        import platform
        current_platform = platform.system()
        
        self.btn_build_mac = QPushButton("Build for Mac")
        self.btn_build_mac.setObjectName("buildButton")
        self.btn_build_mac.setEnabled(False)
        self.btn_build_mac.clicked.connect(self.on_build)
        if current_platform == "Darwin":
            self.btn_build_mac.setToolTip("Build a Mac application")
        else:
            self.btn_build_mac.setToolTip("Requires macOS")
            self.btn_build_mac.setObjectName("buildButtonDisabled")
        build_btn_layout.addWidget(self.btn_build_mac)
        
        self.btn_build_win = QPushButton("Build for Windows")
        self.btn_build_win.setObjectName("buildButton")
        self.btn_build_win.setEnabled(False)
        self.btn_build_win.clicked.connect(self.on_build)
        if current_platform == "Windows":
            self.btn_build_win.setToolTip("Build a Windows executable")
        else:
            self.btn_build_win.setToolTip("Requires Windows")
            self.btn_build_win.setObjectName("buildButtonDisabled")
        build_btn_layout.addWidget(self.btn_build_win)
        
        build_btn_layout.addStretch()
        build_layout.addWidget(build_btn_row)
        
        # Build progress section (hidden by default)
        self.build_progress_section = QWidget()
        build_progress_layout = QVBoxLayout(self.build_progress_section)
        build_progress_layout.setContentsMargins(0, 8, 0, 0)
        build_progress_layout.setSpacing(8)
        
        self.build_status = QLabel("")
        self.build_status.setObjectName("buildStatus")
        self.build_status.setWordWrap(True)
        build_progress_layout.addWidget(self.build_status)
        
        self.build_progress = QProgressBar()
        self.build_progress.setObjectName("buildProgressBar")
        self.build_progress.setMinimum(0)
        self.build_progress.setMaximum(100)
        self.build_progress.setValue(0)
        build_progress_layout.addWidget(self.build_progress)
        
        self.build_progress_section.hide()
        build_layout.addWidget(self.build_progress_section)
        
        # Build result section (hidden by default)
        self.build_result_section = QWidget()
        build_result_layout = QHBoxLayout(self.build_result_section)
        build_result_layout.setContentsMargins(0, 8, 0, 0)
        build_result_layout.setSpacing(12)
        
        self.build_result_label = QLabel("")
        self.build_result_label.setObjectName("buildResultLabel")
        self.build_result_label.setWordWrap(True)
        build_result_layout.addWidget(self.build_result_label, 1)
        
        self.btn_open_build_folder = QPushButton("Open Build Folder")
        self.btn_open_build_folder.setObjectName("btnSmall")
        self.btn_open_build_folder.clicked.connect(self.on_open_build_folder)
        build_result_layout.addWidget(self.btn_open_build_folder)
        
        self.build_result_section.hide()
        build_layout.addWidget(self.build_result_section)
        
        right_layout.addWidget(build_section)
        right_layout.addStretch()
        
        columns.addWidget(right_column)
        
        # Set column proportions (50% left, 50% right)
        columns.setSizes([450, 450])
        
        main_layout.addWidget(columns, 1)
        
        self.main_content.hide()
        layout.addWidget(self.main_content, 1)
        
        self.apply_styles()
    
    def set_project(self, project: Project | None):
        """Set the current project to build."""
        self.project = project
        self.scan_result = None
        
        if project:
            self.project_name.setText(f"Build: {project.name}")
            self.app_name_input.setText(project.name)
            self.app_name_input.setPlaceholderText(project.name)
            
            self.no_project_msg.hide()
            self.main_content.show()
            
            # Reset scan state
            self.deps_status.setText("Click 'Scan Project' to detect third-party packages")
            self.package_display.hide()
            self.deps_actions.hide()
            self.btn_scan.setText("Scan Project")
            self.btn_scan.setEnabled(True)
            
            # Check for existing requirements.txt
            if (project.path / "requirements.txt").exists():
                self.deps_status.setText(
                    "requirements.txt exists. Click Scan to verify it's complete."
                )
            
            # Reset and check environment state
            self.env_progress.hide()
            self.env_details.hide()
            self.env_actions.hide()
            self.btn_setup_env.setEnabled(False)  # Enable after scan
            self._check_existing_environment()
            
            # Reset icon state and check for existing icon
            self._reset_icon_state()
            self._check_existing_icon()
            
            # Reset build state
            self.build_progress_section.hide()
            self.build_result_section.hide()
            # Build buttons are enabled/disabled by _check_existing_environment
            
        else:
            self.project_name.setText("Build for Distribution")
            self.no_project_msg.show()
            self.main_content.hide()
    
    def _reset_icon_state(self):
        """Reset icon UI to default state."""
        self.icon_path = None
        self.icon_preview.setText("")
        self.icon_preview.setPixmap(QPixmap())  # Clear any pixmap
        self.icon_warning.hide()
        self.btn_choose_icon.setText("Choose Image...")
    
    def _check_existing_icon(self):
        """Check if project already has an icon file."""
        if not self.project:
            return
        
        # Look for common icon locations
        icon_patterns = [
            self.project.path / "icon.png",
            self.project.path / f"{self.project.name}.png",
            self.project.path / "resources" / "icon.png",
            self.project.path / "assets" / "icon.png",
        ]
        
        for icon_path in icon_patterns:
            if icon_path.exists():
                self._set_icon(icon_path)
                break
    
    def _check_existing_environment(self):
        """Check if an environment already exists for this project."""
        if not self.project:
            return
        
        wrangler = EnvironmentWrangler()
        
        if wrangler.venv_exists(self.project.name):
            # Environment exists
            size = wrangler.get_venv_size(self.project.name)
            size_str = wrangler.format_size(size) if size else "unknown size"
            
            installed = wrangler.get_installed_packages(self.project.name)
            pkg_count = len(installed)
            
            self.env_status.setText(f"✓ Environment ready ({size_str})")
            self.env_status.setStyleSheet("color: #27ae60;")
            
            self.env_details.setText(
                f"<b>{pkg_count} package(s) installed</b><br>"
                f"<span style='color: #666;'>{', '.join(installed[:10])}"
                f"{'...' if len(installed) > 10 else ''}</span>"
            )
            self.env_details.show()
            
            self.btn_setup_env.setText("✓ Environment Ready")
            self.btn_setup_env.setEnabled(False)
            self.env_actions.show()
            
            # Enable build buttons for current platform
            self._enable_build_buttons()
        else:
            self.env_status.setText("Scan dependencies first, then set up the build environment")
            self.env_status.setStyleSheet("")
            self.btn_setup_env.setText("Setup Environment")
            self.btn_setup_env.setEnabled(False)
            
            # Disable build buttons
            self._disable_build_buttons()
    
    def _enable_build_buttons(self):
        """Enable build buttons for the current platform."""
        import platform
        current_platform = platform.system()
        
        if current_platform == "Darwin":
            self.btn_build_mac.setEnabled(True)
            self.btn_build_win.setEnabled(False)
        elif current_platform == "Windows":
            self.btn_build_mac.setEnabled(False)
            self.btn_build_win.setEnabled(True)
        else:  # Linux - could potentially build, but less common
            self.btn_build_mac.setEnabled(False)
            self.btn_build_win.setEnabled(False)
    
    def _disable_build_buttons(self):
        """Disable all build buttons."""
        self.btn_build_mac.setEnabled(False)
        self.btn_build_win.setEnabled(False)
    
    def on_choose_icon(self):
        """Let user choose an icon image."""
        if not self.project:
            return
        
        # Start in the project folder
        start_dir = str(self.project.path)
        
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Choose App Icon",
            start_dir,
            "Images (*.png *.jpg *.jpeg *.gif *.bmp);;PNG Files (*.png);;All Files (*)"
        )
        
        if filepath:
            self._set_icon(Path(filepath))
    
    def _set_icon(self, icon_path: Path):
        """Set the icon from a file path and show preview."""
        if not icon_path.exists():
            return
        
        self.icon_path = icon_path
        
        # Analyze the image
        info = self.icon_alchemist.analyze_image(icon_path)
        
        # Show preview
        pixmap = QPixmap(str(icon_path))
        if not pixmap.isNull():
            # Scale to fit preview size while maintaining aspect ratio
            scaled = pixmap.scaled(
                64, 64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.icon_preview.setPixmap(scaled)
            self.icon_preview.setText("")  # Clear emoji
        
        # Update button text
        self.btn_choose_icon.setText(f"✓ {icon_path.name}")
        
        # Show warning if needed
        if info and info.size_warning:
            self.icon_warning.setText(f"⚠️ {info.size_warning}")
            self.icon_warning.setStyleSheet("color: #e67e22;")
            self.icon_warning.show()
        else:
            self.icon_warning.hide()
            if info:
                self.icon_warning.setText(f"✓ {info.width}x{info.height} — good size")
                self.icon_warning.setStyleSheet("color: #27ae60;")
                self.icon_warning.show()
        
        # Auto-convert to platform-specific format if needed
        self._convert_icon_if_needed(icon_path)
    
    def _convert_icon_if_needed(self, source_path: Path):
        """Convert icon to platform-specific format if needed."""
        import platform
        
        suffix = source_path.suffix.lower()
        system = platform.system()
        
        # Check if conversion is needed
        if system == "Windows" and suffix != '.ico':
            # Need to convert to .ico for Windows builds
            self._convert_to_ico(source_path)
        elif system == "Darwin" and suffix not in ('.icns', '.ico'):
            # Need to convert to .icns for Mac builds
            self._convert_to_icns(source_path)
    
    def _convert_to_ico(self, source_path: Path):
        """Convert image to .ico format for Windows."""
        # Check capabilities
        caps = self.icon_alchemist.get_capabilities()
        if not caps['can_create_ico']:
            self.icon_warning.setText(
                f"⚠️ Can't convert to .ico: {caps['ico_reason']}\n"
                "Build may fail without proper icon."
            )
            self.icon_warning.setStyleSheet("color: #e74c3c;")
            self.icon_warning.show()
            return
        
        # Convert - put the .ico next to the source file
        output_dir = source_path.parent
        result = self.icon_alchemist.create_ico(source_path, output_dir, source_path.stem)
        
        if result.success:
            # Update our icon path to point to the .ico
            self.icon_path = result.output_path
            
            # Update UI
            current_warning = self.icon_warning.text()
            if current_warning and "good size" in current_warning:
                self.icon_warning.setText(f"✓ Converted to {result.output_path.name}")
            else:
                self.icon_warning.setText(
                    f"✓ Converted to {result.output_path.name}\n"
                    f"{current_warning}" if current_warning else f"✓ Converted to {result.output_path.name}"
                )
            self.icon_warning.setStyleSheet("color: #27ae60;")
            self.icon_warning.show()
        else:
            self.icon_warning.setText(f"⚠️ Icon conversion failed: {result.message}")
            self.icon_warning.setStyleSheet("color: #e74c3c;")
            self.icon_warning.show()
    
    def _convert_to_icns(self, source_path: Path):
        """Convert image to .icns format for Mac."""
        # Check capabilities
        caps = self.icon_alchemist.get_capabilities()
        if not caps['can_create_icns']:
            # Not on Mac - this is fine, we'll use PNG
            return
        
        # Convert - put the .icns next to the source file
        output_dir = source_path.parent
        result = self.icon_alchemist.create_icns(source_path, output_dir, source_path.stem)
        
        if result.success:
            # Update our icon path to point to the .icns
            self.icon_path = result.output_path
            
            # Update UI
            current_warning = self.icon_warning.text()
            if current_warning and "good size" in current_warning:
                self.icon_warning.setText(f"✓ Converted to {result.output_path.name}")
            else:
                self.icon_warning.setText(
                    f"✓ Converted to {result.output_path.name}\n"
                    f"{current_warning}" if current_warning else f"✓ Converted to {result.output_path.name}"
                )
            self.icon_warning.setStyleSheet("color: #27ae60;")
            self.icon_warning.show()
        else:
            # Show warning but don't block - PyInstaller might handle PNG
            if result.warnings:
                self.icon_warning.setText(f"⚠️ {result.message}")
                self.icon_warning.setStyleSheet("color: #e67e22;")
                self.icon_warning.show()
    
    def on_scan_dependencies(self):
        """Start scanning for dependencies."""
        if not self.project:
            return
        
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("Scanning...")
        self.deps_status.setText("🔍 Scanning Python files for imports...")
        self.package_display.hide()
        self.deps_actions.hide()
        
        # Run scan in background
        self.worker = DependencyScanWorker(self.project.path)
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.error.connect(self._on_scan_error)
        self.worker.start()
    
    @pyqtSlot(object)
    def _on_scan_finished(self, result: ScanResult):
        """Handle scan completion."""
        self.scan_result = result
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("Rescan")
        
        # Show results
        file_count = len(result.scanned_files)
        pkg_count = len(result.third_party)
        
        if result.errors:
            self.deps_status.setText(
                f"Scanned {file_count} file(s), found {pkg_count} package(s). "
                f"⚠️ {len(result.errors)} file(s) had errors."
            )
        else:
            self.deps_status.setText(
                f"✓ Scanned {file_count} Python file(s), found {pkg_count} third-party package(s)"
            )
        
        if result.third_party:
            packages = sorted(result.third_party)
            display_text = "<b>Detected packages:</b><br>" + ", ".join(packages)
            
            # Check against requirements.txt
            req_path = self.project.path / "requirements.txt"
            show_save_button = True  # Default: show if no requirements.txt exists
            
            if req_path.exists():
                comparison = compare_requirements(result, req_path)
                if comparison.missing_from_requirements:
                    missing = ", ".join(sorted(comparison.missing_from_requirements))
                    display_text += (
                        f"<br><br><span style='color: #e67e22;'>"
                        f"⚠️ Missing from requirements.txt: {missing}</span>"
                    )
                    show_save_button = True  # Need to update requirements.txt
                else:
                    show_save_button = False  # Everything's already there
                
                # Calculate packages that are in both
                in_both = comparison.detected & comparison.in_requirements
                if in_both:
                    display_text += (
                        f"<br><span style='color: #27ae60;'>"
                        f"✓ {len(in_both)} package(s) already in requirements.txt</span>"
                    )
            
            self.package_display.setText(display_text)
            self.package_display.show()
            
            # Only show Save button if there's something to add
            if show_save_button:
                self.deps_actions.show()
            else:
                self.deps_actions.hide()
        else:
            self.package_display.setText(
                "No third-party packages detected.<br>"
                "<i>Your project only uses Python's standard library — nice and simple!</i>"
            )
            self.package_display.show()
            self.deps_actions.hide()
        
        # Enable environment setup if we have packages or if there are none (still valid)
        wrangler = EnvironmentWrangler()
        if not wrangler.venv_exists(self.project.name):
            self.btn_setup_env.setEnabled(True)
            self.btn_setup_env.setText("Setup Environment")
            if result.third_party:
                self.env_status.setText(
                    f"Ready to create build environment with {len(result.third_party)} package(s)"
                )
            else:
                self.env_status.setText(
                    "Ready to create build environment (no extra packages needed)"
                )
    
    @pyqtSlot(str)
    def _on_scan_error(self, error_msg: str):
        """Handle scan error."""
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("Scan Project")
        self.deps_status.setText(f"❌ Scan failed: {error_msg}")
    
    def on_save_requirements(self):
        """Save detected dependencies to requirements.txt."""
        if not self.project or not self.scan_result:
            return
        
        req_path = self.project.path / "requirements.txt"
        
        if req_path.exists():
            reply = QMessageBox.question(
                self,
                "Replace requirements.txt?",
                "requirements.txt already exists.\n\n"
                "Do you want to replace it with the scanned dependencies?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        try:
            content = generate_requirements(self.scan_result)
            req_path.write_text(content)
            
            QMessageBox.information(
                self,
                "Saved!",
                f"Created requirements.txt with {len(self.scan_result.third_party)} packages.\n\n"
                "Don't forget to Save Version in the project workspace to include it."
            )
            
            self.deps_status.setText(
                f"✓ Saved requirements.txt with {len(self.scan_result.third_party)} packages"
            )
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Couldn't save requirements.txt:\n\n{e}"
            )
    
    def on_setup_environment(self):
        """Create the build environment and install packages."""
        if not self.project:
            return
        
        # Get packages to install (use pip package names, not import names)
        pip_packages = list(self.scan_result.get_pip_packages()) if self.scan_result else []
        
        # Get import names for verification (the raw third_party set)
        import_modules = list(self.scan_result.third_party) if self.scan_result else []
        
        # Always include pyinstaller - it's needed for building
        if 'pyinstaller' not in [p.lower() for p in pip_packages]:
            pip_packages.append('pyinstaller')
        
        # Disable button and show progress
        self.btn_setup_env.setEnabled(False)
        self.btn_setup_env.setText("Setting up...")
        self.env_status.setText("Creating build environment...")
        self.env_status.setStyleSheet("")
        
        # Setup progress bar
        self.env_progress.setMaximum(len(pip_packages) if pip_packages else 0)
        self.env_progress.setValue(0)
        self.env_progress.setFormat("Initializing...")
        self.env_progress.show()
        self.env_details.hide()
        self.env_actions.hide()
        
        # Start worker with both pip names (for install) and import names (for verify)
        self.env_worker = EnvironmentWorker(self.project.name, pip_packages, import_modules)
        self.env_worker.progress.connect(self._on_env_progress)
        self.env_worker.install_progress.connect(self._on_env_install_progress)
        self.env_worker.finished.connect(self._on_env_finished)
        self.env_worker.error.connect(self._on_env_error)
        self.env_worker.start()
    
    def on_rebuild_environment(self):
        """Delete and recreate the environment."""
        if not self.project:
            return
        
        reply = QMessageBox.question(
            self,
            "Rebuild Environment?",
            "This will delete the existing environment and create a fresh one.\n\n"
            "This can help if packages aren't working correctly.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Delete first
        wrangler = EnvironmentWrangler()
        result = wrangler.delete_venv(self.project.name)
        
        if not result.success:
            QMessageBox.warning(
                self,
                "Error",
                f"Couldn't delete environment:\n\n{result.details}"
            )
            return
        
        # Then setup fresh
        self.on_setup_environment()
    
    def on_delete_environment(self):
        """Delete the build environment to save disk space."""
        if not self.project:
            return
        
        wrangler = EnvironmentWrangler()
        size = wrangler.get_venv_size(self.project.name)
        size_str = wrangler.format_size(size) if size else "some"
        
        reply = QMessageBox.question(
            self,
            "Delete Environment?",
            f"This will delete the build environment and free up {size_str} of disk space.\n\n"
            "You'll need to set it up again before building.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        result = wrangler.delete_venv(self.project.name)
        
        if result.success:
            self.env_status.setText("Environment deleted. Scan and set up when you're ready to build.")
            self.env_status.setStyleSheet("")
            self.env_details.hide()
            self.env_actions.hide()
            
            # Enable setup button if we have scan results
            if self.scan_result:
                self.btn_setup_env.setText("Setup Environment")
                self.btn_setup_env.setEnabled(True)
            else:
                self.btn_setup_env.setText("Setup Environment")
                self.btn_setup_env.setEnabled(False)
        else:
            QMessageBox.warning(
                self,
                "Error",
                f"Couldn't delete environment:\n\n{result.details}"
            )
    
    @pyqtSlot(str)
    def _on_env_progress(self, message: str):
        """Handle environment progress updates."""
        self.env_status.setText(message)
        self.env_progress.setFormat(message)
    
    @pyqtSlot(object)
    def _on_env_install_progress(self, progress: InstallProgress):
        """Handle package installation progress."""
        self.env_progress.setValue(progress.index)
        self.env_progress.setFormat(f"{progress.index}/{progress.total}: {progress.package}")
        self.env_status.setText(progress.message)
    
    @pyqtSlot(object)
    def _on_env_finished(self, result: VenvResult):
        """Handle environment setup completion."""
        self.env_progress.hide()
        
        if result.success:
            self.env_status.setText(f"✓ {result.message}")
            self.env_status.setStyleSheet("color: #27ae60;")
            
            self.env_details.setText(result.details)
            self.env_details.show()
            
            self.btn_setup_env.setText("✓ Environment Ready")
            self.btn_setup_env.setEnabled(False)
            self.env_actions.show()
            
            # Enable build buttons for current platform
            self._enable_build_buttons()
        else:
            self.env_status.setText(f"❌ {result.message}")
            self.env_status.setStyleSheet("color: #e74c3c;")
            
            if result.details:
                self.env_details.setText(f"<span style='color: #666;'>{result.details}</span>")
                self.env_details.show()
            
            self.btn_setup_env.setText("Retry Setup")
            self.btn_setup_env.setEnabled(True)
    
    @pyqtSlot(str)
    def _on_env_error(self, error_msg: str):
        """Handle environment setup error."""
        self.env_progress.hide()
        self.env_status.setText(f"❌ Error: {error_msg}")
        self.env_status.setStyleSheet("color: #e74c3c;")
        self.btn_setup_env.setText("Retry Setup")
        self.btn_setup_env.setEnabled(True)
    
    # === Build handlers ===
    
    def on_build(self):
        """Start the build process."""
        if not self.project:
            return
        
        # Get build options
        app_name = self.app_name_input.text().strip() or self.project.name
        onefile = self.opt_onefile.isChecked()
        windowed = self.opt_windowed.isChecked()
        
        # Get packages for hidden imports detection
        # Start with scanned packages
        packages = []
        if self.scan_result:
            packages = list(self.scan_result.third_party)
        
        # Also include packages from requirements.txt (for manually added packages like customtkinter)
        req_path = self.project.path / "requirements.txt"
        if req_path.exists():
            from core.deps import parse_requirements
            req_packages = parse_requirements(req_path)
            for pkg in req_packages:
                if pkg.lower() not in [p.lower() for p in packages]:
                    packages.append(pkg)
        
        # Check for icon - conversion already happened in _set_icon()
        # self.icon_path should already be the correct format (.ico on Windows, .icns on Mac)
        icon_path = self.icon_path  # Will be None if no icon selected
        
        # Disable build buttons during build
        self._disable_build_buttons()
        self.btn_back.setEnabled(False)
        
        # Show progress
        self.build_status.setText("Starting build...")
        self.build_progress.setValue(0)
        self.build_progress_section.show()
        self.build_result_section.hide()
        
        # Start worker
        self.build_worker = BuildWorker(
            project_path=self.project.path,
            project_name=self.project.name,
            main_file=self.project.main_file,
            app_name=app_name,
            onefile=onefile,
            windowed=windowed,
            icon_path=icon_path,
            packages=packages
        )
        self.build_worker.progress.connect(self._on_build_progress)
        self.build_worker.finished.connect(self._on_build_finished)
        self.build_worker.error.connect(self._on_build_error)
        self.build_worker.start()
    
    @pyqtSlot(object)
    def _on_build_progress(self, progress: BuildProgress):
        """Handle build progress updates."""
        self.build_status.setText(progress.message)
        self.build_progress.setValue(progress.percent)
    
    @pyqtSlot(object)
    def _on_build_finished(self, result: BuildResult):
        """Handle build completion."""
        self.build_progress_section.hide()
        self.btn_back.setEnabled(True)
        
        if result.success:
            # Show success
            self.build_result_label.setText(
                f"<span style='color: #27ae60; font-weight: 600;'>✓ {result.message}</span>"
            )
            if result.warnings:
                warnings_text = "<br>".join(f"⚠️ {w}" for w in result.warnings[:3])
                self.build_result_label.setText(
                    self.build_result_label.text() + f"<br><span style='color: #e67e22;'>{warnings_text}</span>"
                )
            
            self.build_result_section.show()
            
            # Re-enable build buttons
            self._enable_build_buttons()
            
            # Show success message
            QMessageBox.information(
                self,
                "Build Complete!",
                f"{result.message}\n\n"
                f"Your app is ready in:\n{result.output_path}\n\n"
                "Click 'Open Build Folder' to find it."
            )
        else:
            # Show error
            self.build_result_label.setText(
                f"<span style='color: #e74c3c; font-weight: 600;'>❌ {result.message}</span>"
            )
            if result.details:
                # Truncate long details
                details = result.details[:200] + "..." if len(result.details) > 200 else result.details
                self.build_result_label.setText(
                    self.build_result_label.text() + f"<br><span style='color: #666;'>{details}</span>"
                )
            
            self.build_result_section.show()
            
            # Re-enable build buttons for retry
            self._enable_build_buttons()
            
            QMessageBox.warning(
                self,
                "Build Failed",
                f"{result.message}\n\n"
                f"Details:\n{result.details[:500] if result.details else 'No additional details'}"
            )
    
    @pyqtSlot(str)
    def _on_build_error(self, error_msg: str):
        """Handle build error."""
        self.build_progress_section.hide()
        self.btn_back.setEnabled(True)
        
        self.build_result_label.setText(
            f"<span style='color: #e74c3c; font-weight: 600;'>❌ Error: {error_msg}</span>"
        )
        self.build_result_section.show()
        
        # Re-enable build buttons for retry
        self._enable_build_buttons()
        
        QMessageBox.critical(
            self,
            "Build Error",
            f"An unexpected error occurred:\n\n{error_msg}"
        )
    
    def on_open_build_folder(self):
        """Open the TPC Builds folder."""
        if not self.project:
            return
        
        orchestrator = BuildOrchestrator()
        orchestrator.open_build_folder(self.project.path)
    
    def apply_styles(self):
        self.setStyleSheet("""
            PackWorkspace {
                background-color: #ffffff;
            }
            
            #btnBack {
                background-color: transparent;
                color: #4a9eff;
                border: none;
                padding: 8px 0;
                font-size: 14px;
                text-align: left;
            }
            
            #btnBack:hover {
                color: #3a8eef;
                text-decoration: underline;
            }
            
            #packHeader {
                color: #333333;
                font-size: 22px;
                font-weight: 600;
            }
            
            #noProjectMsg {
                color: #888888;
                font-size: 16px;
                padding: 60px;
            }
            
            #packSection {
                background-color: #f8f8f8;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
            }
            
            #sectionTitle {
                color: #333333;
                font-size: 16px;
                font-weight: 600;
            }
            
            #statusText {
                color: #666666;
                font-size: 14px;
            }
            
            #packageDisplay {
                color: #333333;
                font-size: 14px;
                background-color: #ffffff;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
                padding: 12px 16px;
            }
            
            #fieldLabel {
                color: #555555;
                font-size: 14px;
            }
            
            #fieldInput {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 14px;
            }
            
            #fieldInput:disabled {
                background-color: #f5f5f5;
                color: #999999;
            }
            
            #iconPreview {
                background-color: #ffffff;
                border: 2px dashed #cccccc;
                border-radius: 8px;
                font-size: 24px;
            }
            
            #iconWarning {
                color: #e67e22;
                font-size: 12px;
                padding: 4px 0;
            }
            
            #actionButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            
            #actionButton:hover {
                background-color: #5aafff;
            }
            
            #actionButton:disabled {
                background-color: #cccccc;
            }
            
            #secondaryButton {
                background-color: #e8e8e8;
                color: #555555;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            
            #secondaryButton:hover {
                background-color: #d8d8d8;
            }
            
            #secondaryButton:disabled {
                background-color: #f0f0f0;
                color: #aaaaaa;
            }
            
            #buildButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 500;
            }
            
            #buildButton:hover {
                background-color: #3ddc81;
            }
            
            #buildButton:disabled {
                background-color: #95a5a6;
            }
            
            #buildButtonDisabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 15px;
            }
            
            #comingSoon {
                color: #888888;
                font-size: 13px;
                font-style: italic;
                padding: 8px 0;
            }
            
            #envProgress {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #ffffff;
                height: 20px;
            }
            
            #envProgress::chunk {
                background-color: #4a9eff;
                border-radius: 3px;
            }
            
            #envDetails {
                color: #333333;
                font-size: 13px;
                background-color: #ffffff;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
                padding: 12px 16px;
            }
            
            #secondaryButtonDanger {
                background-color: #fff5f5;
                color: #e74c3c;
                border: 1px solid #e74c3c;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            
            #secondaryButtonDanger:hover {
                background-color: #ffe0e0;
            }
            
            QCheckBox {
                color: #555555;
                font-size: 14px;
                spacing: 8px;
            }
            
            QCheckBox:disabled {
                color: #aaaaaa;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            
            #buildStatus {
                color: #555555;
                font-size: 14px;
            }
            
            #buildProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #ffffff;
                height: 20px;
            }
            
            #buildProgressBar::chunk {
                background-color: #2ecc71;
                border-radius: 3px;
            }
            
            #buildResultLabel {
                color: #333333;
                font-size: 14px;
            }
        """)
