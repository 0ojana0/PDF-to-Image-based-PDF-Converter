# ==============================================================================
# CUSTOMIZABLE CONFIGURATION SETTINGS
# ==============================================================================
# Set your target DPI and maximum pixel dimension for the wider side here.
# The other side will be automatically calculated to preserve aspect ratio.

TARGET_DPI = 150              # Target DPI resolution for rendering & PDF layout
WIDER_SIDE_PIXELS = 1680     # Length (in pixels) of the wider side (width or height)
IMAGE_FORMAT = "JPEG"        # Compression format: "JPEG" (smaller size) or "PNG" (lossless)
JPEG_QUALITY = 97            # JPEG quality between 1 and 100 (higher = better quality, larger size)
OUTPUT_SUFFIX = "_scanned"   # Suffix added to output filenames (e.g. document_scanned.pdf)

# ==============================================================================


import os
import sys
import subprocess

def install_package_if_missing(package_name: str, import_module_name: str = None) -> None:
    """
    Checks if a Python module is installed; if not, automatically installs
    it via pip and ensures it is ready for use.
    """
    module_to_check = import_module_name if import_module_name else package_name
    try:
        __import__(module_to_check)
    except ImportError:
        print(f"Required package '{package_name}' not found. Installing via pip...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            print(f"Successfully installed '{package_name}'.")
        except subprocess.CalledProcessError as exc:
            # If pip installation fails, raise an informative error
            raise RuntimeError(
                f"Failed to automatically install {package_name}. "
                f"Please manually run: pip install {package_name}"
            ) from exc

# Auto-install PyMuPDF (fitz) which provides high-speed, self-contained PDF rasterization
install_package_if_missing("pymupdf", "fitz")


from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import fitz  # PyMuPDF


def convert_pdf_to_images_pdf(
    input_path: str,
    output_path: str,
    progress_callback=None
) -> None:
    """
    Renders every page of the text-based PDF into a rasterized image
    and packages them into a new photo-based PDF.
    
    The wider side of each page is scaled to WIDER_SIDE_PIXELS, while the other side
    is adjusted proportionally. The resulting PDF page dimensions are scaled to match TARGET_DPI.
    """
    source_doc = fitz.open(input_path)
    output_doc = fitz.open()
    total_pages = len(source_doc)

    try:
        for page_idx in range(total_pages):
            page = source_doc[page_idx]
            rect = page.rect  # Original page dimensions in PDF points (1/72 inch)
            
            # Identify the longer side (width or height)
            longer_side_pt = max(rect.width, rect.height)
            
            # Calculate the scaling factor required to make the wider side equal WIDER_SIDE_PIXELS
            if longer_side_pt > 0:
                scale_factor = WIDER_SIDE_PIXELS / longer_side_pt
            else:
                scale_factor = 1.0

            # Create scaling matrix for PyMuPDF rasterization
            matrix = fitz.Matrix(scale_factor, scale_factor)
            
            # Render page to pixmap (raster image)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            
            # Auto-calculate PDF page dimensions in points so that (pixels / TARGET_DPI) * 72 pt/in
            # exactly matches the raster image's physical size at TARGET_DPI
            pdf_page_width_pt = (pixmap.width / TARGET_DPI) * 72.0
            pdf_page_height_pt = (pixmap.height / TARGET_DPI) * 72.0
            
            # Create a blank new page in the destination document
            new_page = output_doc.new_page(
                width=pdf_page_width_pt,
                height=pdf_page_height_pt
            )
            
            # Encode image to byte stream
            fmt = IMAGE_FORMAT.strip().upper()
            if fmt == "PNG":
                image_bytes = pixmap.tobytes("png")
            else:
                try:
                    image_bytes = pixmap.tobytes("jpeg", jpg_quality=JPEG_QUALITY)
                except Exception:
                    # Fallback to standard jpeg without quality kwarg if older build
                    image_bytes = pixmap.tobytes("jpg")
            
            # Place the image spanning the entire newly created page
            dest_rect = fitz.Rect(0, 0, pdf_page_width_pt, pdf_page_height_pt)
            new_page.insert_image(dest_rect, stream=image_bytes)
            
            # Release pixmap memory
            pixmap = None
            
            if progress_callback:
                progress_callback(page_idx + 1, total_pages)
                
        # Save output PDF with compression & garbage collection
        output_doc.save(output_path, deflate=True, garbage=3)
    finally:
        source_doc.close()
        output_doc.close()


class ConversionProgressDialog:
    """
    A GUI dialog providing progress bars and status updates
    during batch conversion of PDF files.
    """
    def __init__(self, root: tk.Tk, total_files: int):
        self.root = root
        self.total_files = total_files
        self.current_file_index = 0
        
        # Configure modal window
        self.win = tk.Toplevel(root)
        self.win.title("Converting PDFs...")
        self.win.geometry("520x260")
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", lambda: None)  # Prevent closing mid-conversion
        
        # Center the window on screen
        self.win.update_idletasks()
        x = (self.win.winfo_screenwidth() // 2) - (520 // 2)
        y = (self.win.winfo_screenheight() // 2) - (260 // 2)
        self.win.geometry(f"+{x}+{y}")
        
        # Styling
        padding_frame = ttk.Frame(self.win, padding="20 20 20 20")
        padding_frame.pack(fill=tk.BOTH, expand=True)

        # File status label
        self.file_label = ttk.Label(
            padding_frame, 
            text="Preparing conversion...", 
            font=("Segoe UI", 10, "bold")
        )
        self.file_label.pack(anchor=tk.W, pady=(0, 5))

        # Overall progress bar
        self.overall_bar = ttk.Progressbar(
            padding_frame, 
            maximum=total_files, 
            length=480, 
            mode='determinate'
        )
        self.overall_bar.pack(pady=(0, 15))

        # Page status label
        self.page_label = ttk.Label(
            padding_frame, 
            text="Processing pages...", 
            font=("Segoe UI", 9)
        )
        self.page_label.pack(anchor=tk.W, pady=(0, 5))

        # Current page progress bar
        self.page_bar = ttk.Progressbar(
            padding_frame, 
            maximum=100, 
            length=480, 
            mode='determinate'
        )
        self.page_bar.pack(pady=(0, 15))

        # Info note
        self.info_label = ttk.Label(
            padding_frame, 
            text=f"Target: {TARGET_DPI} DPI | Wider side: {WIDER_SIDE_PIXELS}px ({IMAGE_FORMAT})",
            font=("Segoe UI", 8),
            foreground="#666666"
        )
        self.info_label.pack(anchor=tk.W)

    def set_active_file(self, file_index: int, filename: str) -> None:
        """Updates UI for the newly active file."""
        self.current_file_index = file_index
        self.file_label.config(
            text=f"File [{file_index + 1}/{self.total_files}]: {filename}"
        )
        self.overall_bar['value'] = file_index
        self.page_bar['value'] = 0
        self.page_label.config(text="Starting page conversion...")
        self.win.update()

    def update_page_progress(self, current_page: int, total_pages: int) -> None:
        """Updates UI for page progress within the current file."""
        percentage = (current_page / total_pages) * 100
        self.page_bar['value'] = percentage
        self.page_label.config(text=f"Rendering page {current_page} of {total_pages}...")
        self.win.update()

    def close(self) -> None:
        """Closes the dialog."""
        self.win.destroy()


def main():
    """
    Main entry point: initializes Tkinter, opens multi-file picker,
    and runs batch conversion with progress feedback.
    """
    # Create root Tkinter instance
    root = tk.Tk()
    root.withdraw()  # Hide main blank window

    # Open file picker with multi-selection enabled
    selected_files = filedialog.askopenfilenames(
        title="Select Text-Based PDF(s) to Convert to Photo-Based PDF",
        filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")]
    )

    # Exit gracefully if user canceled the file dialog
    if not selected_files:
        return

    progress_dialog = ConversionProgressDialog(root, total_files=len(selected_files))
    successful_conversions = []
    failed_files = []

    for idx, file_path_str in enumerate(selected_files):
        source_path = Path(file_path_str)
        progress_dialog.set_active_file(idx, source_path.name)
        
        # Generate output path alongside input file with the chosen suffix
        out_name = f"{source_path.stem}{OUTPUT_SUFFIX}.pdf"
        out_path = source_path.parent / out_name

        try:
            convert_pdf_to_images_pdf(
                str(source_path),
                str(out_path),
                progress_callback=progress_dialog.update_page_progress
            )
            successful_conversions.append(str(out_path))
        except Exception as exc:
            failed_files.append((source_path.name, str(exc)))

    progress_dialog.close()

    # Construct final summary message
    summary_messages = []
    if successful_conversions:
        summary_messages.append(
            f"Successfully converted {len(successful_conversions)} file(s):\n"
            + "\n".join([f"• {Path(p).name}" for p in successful_conversions[:5]])
        )
        if len(successful_conversions) > 5:
            summary_messages.append(f"...and {len(successful_conversions) - 5} more.")

    if failed_files:
        summary_messages.append(
            "\nErrors encountered:\n"
            + "\n".join([f"• {name}: {err}" for name, err in failed_files])
        )

    if successful_conversions and not failed_files:
        messagebox.showinfo("Conversion Complete", "\n\n".join(summary_messages))
    elif successful_conversions and failed_files:
        messagebox.showwarning("Completed with Warnings", "\n\n".join(summary_messages))
    else:
        messagebox.showerror("Conversion Failed", "\n\n".join(summary_messages))

    # Optional: Open output directory if files were converted
    if successful_conversions:
        last_dir = str(Path(successful_conversions[0]).parent)
        try:
            if sys.platform == "win32":
                os.startfile(last_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", last_dir])
            else:
                subprocess.Popen(["xdg-open", last_dir])
        except Exception:
            pass


if __name__ == "__main__":
    main()