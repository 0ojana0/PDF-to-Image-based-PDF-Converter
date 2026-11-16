import os
import sys
import math
import random
import subprocess

# --- 1. Automatic Dependency Bootstrap ---
REQUIRED_PACKAGES = {
    "fitz": "pymupdf",
    "PIL": "pillow"
}

def install_missing_packages():
    missing = []
    for module_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(module_name)
        except ImportError:
            missing.append(pip_name)
    
    if missing:
        print(f"Installing missing dependencies: {', '.join(missing)}...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", *missing],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as err:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Installation Error", f"Failed to install requirements automatically:\n{err}")
            sys.exit(1)

install_missing_packages()

import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import filedialog, messagebox

# --- 2. Pattern & Aesthetic Color Palettes ---
# Soft alpha values (40-65 out of 255) ensure text remains clear to humans
# while disrupting Otsu and Sauvola thresholding during OCR preprocessing.
PALETTES = [
    (220, 95, 95, 52),    # Light Crimson / Red
    (75, 175, 115, 48),   # Light Mint / Emerald Green
    (85, 135, 230, 50),   # Light Cobalt / Sky Blue
    (145, 150, 160, 58),  # Subtle Slate Grey
    (195, 120, 215, 45)   # Light Lavender
]

def draw_security_patterns(width, height):
    """Generates an aesthetic overlay containing sinusoidal wave bands,
    angled security grids, and stipple dots."""
    overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # 1. Harmonic Sine Waves (disrupts baseline text line segmentation)
    num_wave_bands = random.randint(4, 7)
    for _ in range(num_wave_bands):
        color = random.choice(PALETTES)
        freq = random.uniform(0.006, 0.018)
        amp = random.uniform(14, 32)
        phase = random.uniform(0, math.pi * 2)
        y_offset = random.uniform(0, height)
        line_width = random.choice([1, 2])

        points = []
        for x in range(0, width, 4):
            # Compound harmonic wave
            y = y_offset + amp * math.sin(x * freq + phase) + (amp * 0.4) * math.cos(x * freq * 1.8)
            points.append((x, y))

        if len(points) > 1:
            draw.line(points, fill=color, width=line_width, joint="curve")

    # 2. Angled Micro-Grid / Security Guilloché Mesh
    grid_color = random.choice(PALETTES)
    grid_spacing = random.randint(28, 45)
    angle_offset = random.uniform(-0.5, 0.5)

    # Diagonal forward lines
    for start_x in range(-height, width + height, grid_spacing):
        x1 = start_x
        y1 = 0
        x2 = int(start_x + height * (0.5 + angle_offset))
        y2 = height
        draw.line([(x1, y1), (x2, y2)], fill=grid_color, width=1)

    # Diagonal reverse lines
    cross_color = random.choice(PALETTES)
    for start_x in range(-height, width + height, grid_spacing):
        x1 = start_x
        y1 = 0
        x2 = int(start_x - height * (0.5 - angle_offset))
        y2 = height
        draw.line([(x1, y1), (x2, y2)], fill=cross_color, width=1)

    # 3. Micro-Stippling / Dots (interferes with connected-component analysis)
    dot_color = random.choice(PALETTES)
    dot_spacing = random.randint(40, 60)
    for x in range(10, width, dot_spacing):
        for y in range(10, height, dot_spacing):
            jitter_x = x + random.randint(-8, 8)
            jitter_y = y + random.randint(-8, 8)
            radius = random.choice([1, 2])
            draw.ellipse(
                [(jitter_x - radius, jitter_y - radius), (jitter_x + radius, jitter_y + radius)],
                fill=dot_color
            )

    return overlay

# --- 3. Processing Core ---
def process_pdf(input_path):
    doc = fitz.open(input_path)
    output_doc = fitz.open()

    # 200 DPI gives optimal balance between OCR disruption, speed, and output quality
    render_matrix = fitz.Matrix(200 / 72, 200 / 72)

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        pix = page.get_pixmap(matrix=render_matrix, alpha=False)
        
        # Load page image into PIL
        base_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("RGBA")

        # Generate and apply overlay
        overlay = draw_security_patterns(pix.width, pix.height)
        combined = Image.alpha_composite(base_img, overlay).convert("RGB")

        # Compress to JPEG stream to maintain compact PDF size
        import io
        img_buffer = io.BytesIO()
        combined.save(img_buffer, format="JPEG", quality=88, optimize=True)
        img_bytes = img_buffer.getvalue()

        # Reconstruct PDF page matching original dimensions
        new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(page.rect, stream=img_bytes)

    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_protected{ext}"
    output_doc.save(output_path, garbage=4, deflate=True)
    output_doc.close()
    doc.close()
    return output_path

# --- 4. Main Entry Point & Multi-Select GUI ---
def main():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    file_paths = filedialog.askopenfilenames(
        title="Select Scanned/Photo-Based PDFs to Protect",
        filetypes=[("PDF Documents", "*.pdf")]
    )

    if not file_paths:
        return

    successful = 0
    errors = []

    for path in file_paths:
        try:
            process_pdf(path)
            successful += 1
        except Exception as e:
            errors.append(f"{os.path.basename(path)}: {str(e)}")

    if errors:
        msg = f"Processed {successful} file(s) successfully.\n\nErrors encountered:\n" + "\n".join(errors)
        messagebox.showwarning("Processing Complete (with Warnings)", msg)
    else:
        messagebox.showinfo(
            "Success",
            f"Successfully processed {successful} PDF file(s)!\nSaved as '<filename>_protected.pdf'."
        )

if __name__ == "__main__":
    main()