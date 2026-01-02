"""
Icon Alchemist for TPC.

Converts user-provided images to platform-specific icon formats:
- .icns for macOS
- .ico for Windows

Users drag in a PNG (or JPG), we handle the rest.
Warns if the source is too small (< 128px) since it'll look blurry.
"""

import subprocess
import sys
import platform
import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


def _subprocess_args() -> dict:
    """
    Get platform-specific subprocess arguments.
    
    On Windows, this prevents console windows from popping up
    when running commands from a frozen PyInstaller executable.
    """
    kwargs = {}
    if sys.platform == "win32":
        # CREATE_NO_WINDOW = 0x08000000
        kwargs["creationflags"] = 0x08000000
    return kwargs


# Try to import PIL, but don't fail if it's not available
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


@dataclass
class IconResult:
    """Result of an icon conversion operation."""
    success: bool
    message: str
    output_path: Optional[Path] = None
    warnings: list[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class ImageInfo:
    """Information about a source image."""
    path: Path
    width: int
    height: int
    format: str
    is_square: bool
    is_too_small: bool  # < 128px
    is_recommended: bool  # >= 512px
    
    @property
    def size_warning(self) -> Optional[str]:
        """Get a warning message if the image size is problematic."""
        if self.is_too_small:
            return f"Image is only {self.width}x{self.height}px — icon may look blurry"
        elif not self.is_square:
            return f"Image is not square ({self.width}x{self.height}) — will be stretched"
        elif not self.is_recommended:
            return f"Image is {self.width}x{self.height}px — 512x512 or larger recommended"
        return None


class IconAlchemist:
    """
    Converts images to platform-specific icon formats.
    
    Usage:
        alchemist = IconAlchemist()
        
        # Check an image before converting
        info = alchemist.analyze_image(Path("my_icon.png"))
        if info.size_warning:
            print(f"Warning: {info.size_warning}")
        
        # Convert to macOS icon
        result = alchemist.create_icns(Path("my_icon.png"), Path("output/"))
        
        # Convert to Windows icon
        result = alchemist.create_ico(Path("my_icon.png"), Path("output/"))
    """
    
    # Standard icon sizes for each platform
    ICNS_SIZES = [16, 32, 64, 128, 256, 512, 1024]
    ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
    
    def __init__(self):
        self.has_pil = HAS_PIL
        self.system = platform.system()
    
    def analyze_image(self, image_path: Path) -> Optional[ImageInfo]:
        """
        Analyze an image to check if it's suitable for icon conversion.
        
        Returns None if the image can't be read.
        """
        if not image_path.exists():
            return None
        
        if self.has_pil:
            try:
                with Image.open(image_path) as img:
                    width, height = img.size
                    fmt = img.format or image_path.suffix.upper().lstrip('.')
                    
                    return ImageInfo(
                        path=image_path,
                        width=width,
                        height=height,
                        format=fmt,
                        is_square=(width == height),
                        is_too_small=(min(width, height) < 128),
                        is_recommended=(min(width, height) >= 512)
                    )
            except Exception:
                return None
        else:
            # Without PIL, use sips on Mac to get dimensions
            if self.system == "Darwin":
                try:
                    result = subprocess.run(
                        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(image_path)],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        **_subprocess_args()
                    )
                    
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        width = height = 0
                        for line in lines:
                            if 'pixelWidth' in line:
                                width = int(line.split(':')[1].strip())
                            elif 'pixelHeight' in line:
                                height = int(line.split(':')[1].strip())
                        
                        if width and height:
                            return ImageInfo(
                                path=image_path,
                                width=width,
                                height=height,
                                format=image_path.suffix.upper().lstrip('.'),
                                is_square=(width == height),
                                is_too_small=(min(width, height) < 128),
                                is_recommended=(min(width, height) >= 512)
                            )
                except Exception:
                    pass
            
            return None
    
    def create_icns(self, source: Path, output_dir: Path, name: Optional[str] = None) -> IconResult:
        """
        Create a macOS .icns icon from a source image.
        
        Args:
            source: Path to source image (PNG recommended)
            output_dir: Directory to save the .icns file
            name: Optional output filename (without extension)
            
        Returns:
            IconResult with success status and output path
        """
        if not source.exists():
            return IconResult(False, f"Source image not found: {source}")
        
        if self.system != "Darwin":
            return IconResult(
                False, 
                "Creating .icns files requires macOS",
                warnings=["You can create the icon on a Mac and copy it to your project"]
            )
        
        output_name = name or source.stem
        output_path = output_dir / f"{output_name}.icns"
        
        # Analyze the source
        info = self.analyze_image(source)
        warnings = []
        if info and info.size_warning:
            warnings.append(info.size_warning)
        
        # Create iconset directory
        with tempfile.TemporaryDirectory() as tmpdir:
            iconset_path = Path(tmpdir) / f"{output_name}.iconset"
            iconset_path.mkdir()
            
            try:
                # Generate all required sizes using sips
                # macOS iconset requires specific filenames
                icon_specs = [
                    (16, "icon_16x16.png", 1),
                    (32, "icon_16x16@2x.png", 2),  # 16@2x = 32
                    (32, "icon_32x32.png", 1),
                    (64, "icon_32x32@2x.png", 2),  # 32@2x = 64
                    (128, "icon_128x128.png", 1),
                    (256, "icon_128x128@2x.png", 2),  # 128@2x = 256
                    (256, "icon_256x256.png", 1),
                    (512, "icon_256x256@2x.png", 2),  # 256@2x = 512
                    (512, "icon_512x512.png", 1),
                    (1024, "icon_512x512@2x.png", 2),  # 512@2x = 1024
                ]
                
                for size, filename, scale in icon_specs:
                    output_file = iconset_path / filename
                    
                    # Use sips to resize
                    result = subprocess.run(
                        [
                            "sips",
                            "-z", str(size), str(size),  # Resize to square
                            str(source),
                            "--out", str(output_file)
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        **_subprocess_args()
                    )
                    
                    if result.returncode != 0:
                        return IconResult(
                            False, 
                            f"Failed to resize image to {size}x{size}",
                            warnings=warnings
                        )
                
                # Convert iconset to icns using iconutil
                output_dir.mkdir(parents=True, exist_ok=True)
                
                result = subprocess.run(
                    ["iconutil", "-c", "icns", str(iconset_path), "-o", str(output_path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    **_subprocess_args()
                )
                
                if result.returncode != 0:
                    return IconResult(
                        False,
                        f"iconutil failed: {result.stderr}",
                        warnings=warnings
                    )
                
                return IconResult(
                    True,
                    f"Created {output_path.name}",
                    output_path=output_path,
                    warnings=warnings
                )
                
            except subprocess.TimeoutExpired:
                return IconResult(False, "Icon conversion timed out", warnings=warnings)
            except Exception as e:
                return IconResult(False, f"Error creating icon: {e}", warnings=warnings)
    
    def create_ico(self, source: Path, output_dir: Path, name: Optional[str] = None) -> IconResult:
        """
        Create a Windows .ico icon from a source image.
        
        Args:
            source: Path to source image (PNG recommended)
            output_dir: Directory to save the .ico file
            name: Optional output filename (without extension)
            
        Returns:
            IconResult with success status and output path
        """
        if not source.exists():
            return IconResult(False, f"Source image not found: {source}")
        
        if not self.has_pil:
            return IconResult(
                False,
                "Creating .ico files requires Pillow (pip install Pillow)",
                warnings=["Install Pillow to enable icon conversion"]
            )
        
        output_name = name or source.stem
        output_path = output_dir / f"{output_name}.ico"
        
        # Analyze the source
        info = self.analyze_image(source)
        warnings = []
        if info and info.size_warning:
            warnings.append(info.size_warning)
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            with Image.open(source) as img:
                # Convert to RGBA if necessary
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Generate all the sizes we need
                # ICO format needs sizes as a list of tuples for the save() method
                icon_sizes = []
                for size in self.ICO_SIZES:
                    # Only include sizes smaller than or equal to source
                    # (upscaling looks bad)
                    if size <= max(img.size):
                        icon_sizes.append((size, size))
                
                # Always include at least 16, 32, 48, 256 for Windows compatibility
                required_sizes = [(16, 16), (32, 32), (48, 48), (256, 256)]
                for req_size in required_sizes:
                    if req_size not in icon_sizes:
                        icon_sizes.append(req_size)
                
                # Sort sizes
                icon_sizes = sorted(set(icon_sizes))
                
                # Resize the image to the largest size first (256x256 is max for ICO)
                max_size = min(256, max(img.size))
                base_img = img.copy()
                base_img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Make it square by padding if needed
                if base_img.width != base_img.height:
                    new_size = max(base_img.width, base_img.height)
                    square = Image.new('RGBA', (new_size, new_size), (0, 0, 0, 0))
                    offset = ((new_size - base_img.width) // 2, (new_size - base_img.height) // 2)
                    square.paste(base_img, offset)
                    base_img = square
                
                # Save with multiple sizes - PIL handles the resizing internally
                # when we pass the sizes parameter
                base_img.save(
                    output_path,
                    format='ICO',
                    sizes=icon_sizes
                )
                
                return IconResult(
                    True,
                    f"Created {output_path.name} with sizes: {', '.join(f'{s[0]}x{s[1]}' for s in icon_sizes)}",
                    output_path=output_path,
                    warnings=warnings
                )
                
        except Exception as e:
            return IconResult(False, f"Error creating icon: {e}", warnings=warnings)
    
    def create_icons(
        self, 
        source: Path, 
        output_dir: Path, 
        name: Optional[str] = None,
        create_icns: bool = True,
        create_ico: bool = True
    ) -> dict[str, IconResult]:
        """
        Create icons for all requested platforms.
        
        Args:
            source: Path to source image
            output_dir: Directory to save icons
            name: Optional base filename (without extension)
            create_icns: Whether to create .icns (Mac)
            create_ico: Whether to create .ico (Windows)
            
        Returns:
            Dict mapping format to IconResult
        """
        results = {}
        
        if create_icns:
            results['icns'] = self.create_icns(source, output_dir, name)
        
        if create_ico:
            results['ico'] = self.create_ico(source, output_dir, name)
        
        return results
    
    def get_capabilities(self) -> dict:
        """
        Check what icon formats can be created on this system.
        
        Returns dict with:
        - can_create_icns: bool
        - can_create_ico: bool
        - icns_reason: str (why icns might not work)
        - ico_reason: str (why ico might not work)
        """
        can_icns = self.system == "Darwin"
        can_ico = self.has_pil
        
        return {
            'can_create_icns': can_icns,
            'can_create_ico': can_ico,
            'icns_reason': None if can_icns else "Requires macOS",
            'ico_reason': None if can_ico else "Requires Pillow (pip install Pillow)"
        }


# === Quick test ===
if __name__ == "__main__":
    alchemist = IconAlchemist()
    
    print("Icon Alchemist Capabilities")
    print("=" * 40)
    caps = alchemist.get_capabilities()
    print(f"Can create .icns: {caps['can_create_icns']}" + 
          (f" ({caps['icns_reason']})" if caps['icns_reason'] else ""))
    print(f"Can create .ico:  {caps['can_create_ico']}" +
          (f" ({caps['ico_reason']})" if caps['ico_reason'] else ""))
    
    # Test with an image if provided
    import sys
    if len(sys.argv) > 1:
        test_image = Path(sys.argv[1])
        print(f"\nAnalyzing: {test_image}")
        
        info = alchemist.analyze_image(test_image)
        if info:
            print(f"  Size: {info.width}x{info.height}")
            print(f"  Format: {info.format}")
            print(f"  Square: {info.is_square}")
            if info.size_warning:
                print(f"  ⚠️  {info.size_warning}")
            else:
                print(f"  ✓ Good size for icons")
        else:
            print("  Could not analyze image")
