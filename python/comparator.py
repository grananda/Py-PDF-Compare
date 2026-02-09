import pdfplumber
from pdf2image import convert_from_path
import difflib
import os
from PIL import Image, ImageChops, ImageDraw, ImageFont
import cv2
import numpy as np


class PDFComparator:
    def __init__(self, file_path_a, file_path_b):
        self.file_path_a = file_path_a
        self.file_path_b = file_path_b
        # Try different font paths for cross-platform compatibility
        font_options = [
            "arial.ttf",  # Windows
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux/WSL
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux alternative
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
        ]

        self.font = None
        for font_path in font_options:
            try:
                self.font = ImageFont.truetype(font_path, 60)
                break
            except (IOError, OSError):
                continue

        if self.font is None:
            print("Warning: No TrueType font found, using default bitmap font.")
            # Fallback to default font
            self.font = ImageFont.load_default()

    def extract_text(self, file_path):
        text_content = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
                else:
                    text_content.append("") # Empty page or image-only
        return text_content

    def compare_text(self):
        text_a = self.extract_text(self.file_path_a)
        text_b = self.extract_text(self.file_path_b)
        
        # Join all pages for a full document diff, or we could do page-by-page
        # Let's do a full document diff for simplicity in the report
        full_text_a = "\n".join(text_a)
        full_text_b = "\n".join(text_b)
        
        diff = difflib.unified_diff(
            full_text_a.splitlines(), 
            full_text_b.splitlines(), 
            fromfile='PDF A', 
            tofile='PDF B', 
            lineterm=''
        )
        
        return list(diff)

    def get_poppler_path(self):
        """
        Find Poppler binaries in the following order:
        1. Bundled with PyInstaller executable (Windows)
        2. Bundled in vendor/poppler (Windows development)
        3. Platform-specific common paths
        4. System PATH (return None)
        """
        import sys
        import platform

        system = platform.system()

        # Check if running as PyInstaller bundle (Windows only)
        if system == "Windows" and getattr(sys, 'frozen', False):
            bundle_dir = sys._MEIPASS
            bundled_poppler = os.path.join(bundle_dir, 'poppler', 'Library', 'bin')
            if os.path.exists(bundled_poppler):
                return bundled_poppler

        # Check vendor directory (Windows development only - contains .exe files)
        if system == "Windows":
            script_dir = os.path.dirname(os.path.abspath(__file__))
            vendor_poppler = os.path.join(script_dir, 'vendor', 'poppler', 'Library', 'bin')
            if os.path.exists(vendor_poppler):
                return vendor_poppler

        # Platform-specific paths
        if system == "Windows":
            user_paths = [
                r"C:\poppler-25.11.0\Library\bin",
                r"C:\poppler-24.08.0\Library\bin",
                r"C:\Program Files\poppler\Library\bin",
                r"C:\Program Files (x86)\poppler\Library\bin",
            ]
        elif system == "Darwin":  # macOS
            user_paths = [
                "/opt/homebrew/bin",           # Apple Silicon Homebrew
                "/usr/local/bin",              # Intel Homebrew
                "/opt/homebrew/opt/poppler/bin",
                "/usr/local/opt/poppler/bin",
            ]
        else:  # Linux
            user_paths = [
                "/usr/bin",
                "/usr/local/bin",
            ]

        for path in user_paths:
            pdftoppm = os.path.join(path, "pdftoppm.exe" if system == "Windows" else "pdftoppm")
            if os.path.exists(pdftoppm):
                return path

        # Fall back: check if pdftoppm is in system PATH
        import shutil
        pdftoppm_path = shutil.which("pdftoppm")
        if pdftoppm_path:
            # Return the directory containing pdftoppm
            return os.path.dirname(pdftoppm_path)

        # Not found anywhere
        return None

    def convert_to_images(self, file_path):
        import platform
        import shutil

        poppler_path = self.get_poppler_path()
        system = platform.system()
        pdftoppm_name = "pdftoppm.exe" if system == "Windows" else "pdftoppm"

        # Verify pdftoppm is accessible
        pdftoppm_found = False
        if poppler_path:
            pdftoppm_found = os.path.exists(os.path.join(poppler_path, pdftoppm_name))
        else:
            pdftoppm_found = shutil.which("pdftoppm") is not None

        if not pdftoppm_found:
            print("Error: Poppler (pdftoppm) not found!")
            if system == "Windows":
                print("Install from: https://github.com/oschwartz10612/poppler-windows/releases")
                print("Or run: uv run python scripts/download_poppler.py")
            elif system == "Darwin":
                print("Install with: brew install poppler")
            else:
                print("Install with: sudo apt install poppler-utils  (Debian/Ubuntu)")
                print("          or: sudo dnf install poppler-utils  (Fedora)")
            return []

        try:
            # Use 75 DPI for optimal balance between quality and file size
            # (default is 200 DPI which creates very large files)
            return convert_from_path(file_path, dpi=75, poppler_path=poppler_path)
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            return []

    def align_pages(self, text_a, text_b):
        """
        Aligns pages based on their text content similarity.
        Returns a list of tuples (tag, i1, i2, j1, j2) describing alignment.
        Uses similarity scoring to detect inserted/deleted pages.
        """
        len_a = len(text_a)
        len_b = len(text_b)

        # Similarity threshold - pages above this are considered matching
        SIMILARITY_THRESHOLD = 0.6
        LOOKAHEAD_WINDOW = 3  # How many pages to look ahead

        alignments = []
        i, j = 0, 0

        while i < len_a or j < len_b:
            if i >= len_a:
                # All remaining pages in B are insertions
                alignments.append(('insert', i, i, j, len_b))
                break
            elif j >= len_b:
                # All remaining pages in A are deletions
                alignments.append(('delete', i, len_a, j, j))
                break
            else:
                # Calculate similarity between current pages
                current_similarity = difflib.SequenceMatcher(None, text_a[i], text_b[j]).ratio()

                # Look ahead to find best alignment
                best_match = {'type': 'equal', 'i': i, 'j': j, 'similarity': current_similarity}

                # Check if skipping page(s) in B gives better match (insertion in B)
                for skip_j in range(1, min(LOOKAHEAD_WINDOW, len_b - j)):
                    similarity = difflib.SequenceMatcher(None, text_a[i], text_b[j + skip_j]).ratio()
                    if similarity > best_match['similarity'] and similarity > SIMILARITY_THRESHOLD:
                        best_match = {'type': 'insert', 'i': i, 'j': j + skip_j, 'similarity': similarity, 'skip': skip_j}

                # Check if skipping page(s) in A gives better match (deletion in A)
                for skip_i in range(1, min(LOOKAHEAD_WINDOW, len_a - i)):
                    similarity = difflib.SequenceMatcher(None, text_a[i + skip_i], text_b[j]).ratio()
                    if similarity > best_match['similarity'] and similarity > SIMILARITY_THRESHOLD:
                        best_match = {'type': 'delete', 'i': i + skip_i, 'j': j, 'similarity': similarity, 'skip': skip_i}

                # Apply best match found
                if best_match['type'] == 'insert':
                    # Pages in B (j to j+skip) are insertions
                    alignments.append(('insert', i, i, j, best_match['j']))
                    j = best_match['j']
                elif best_match['type'] == 'delete':
                    # Pages in A (i to i+skip) are deletions
                    alignments.append(('delete', i, best_match['i'], j, j))
                    i = best_match['i']
                elif current_similarity > SIMILARITY_THRESHOLD:
                    # Current pages match well enough
                    alignments.append(('equal', i, i + 1, j, j + 1))
                    i += 1
                    j += 1
                else:
                    # Pages are different - replacement
                    alignments.append(('replace', i, i + 1, j, j + 1))
                    i += 1
                    j += 1

        return alignments

    def create_blank_page(self, width, height):
        """Creates a white blank page image."""
        return Image.new('RGB', (width, height), 'white')

    def draw_labels(self, image, text_label, color=(0, 0, 0), bg_color="white", x=10, y=5):
        """Draws a label on the image at (x, y) with a background box."""
        draw = ImageDraw.Draw(image)

        # Calculate text size based on font type
        try:
            bbox = draw.textbbox((0, 0), text_label, font=self.font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            padding = 10
        except (AttributeError, TypeError):
            # Fallback for bitmap or problematic fonts
            text_width = len(text_label) * 6
            text_height = 12
            padding = 5

        # Draw background rectangle
        draw.rectangle(
            [x - 5, y, x + text_width + padding, y + text_height + padding],
            fill=bg_color,
            outline="black"
        )

        # Draw text
        draw.text((x, y + padding/2), text_label, fill=color, font=self.font)

    def compare_visuals(self):
        # 1. Extract text from all pages first for alignment
        text_a = self.extract_text(self.file_path_a)
        text_b = self.extract_text(self.file_path_b)
        
        # 2. Align pages
        opcodes = self.align_pages(text_a, text_b)
        
        # 3. Convert pages to images
        images_a = self.convert_to_images(self.file_path_a)
        images_b = self.convert_to_images(self.file_path_b)
        
        diff_results = []
        
        # Open PDFs for coordinate extraction
        with pdfplumber.open(self.file_path_a) as pdf_a, pdfplumber.open(self.file_path_b) as pdf_b:
            
            for tag, i1, i2, j1, j2 in opcodes:
                
                if tag == 'equal' or tag == 'replace':
                    # Compare range of pages
                    count = max(i2 - i1, j2 - j1)
                    
                    for k in range(count):
                        idx_a = i1 + k if i1 + k < i2 else None
                        idx_b = j1 + k if j1 + k < j2 else None
                        
                        # Prepare images
                        img_a = images_a[idx_a] if idx_a is not None and idx_a < len(images_a) else None
                        img_b = images_b[idx_b] if idx_b is not None and idx_b < len(images_b) else None
                        
                        if img_a and img_b:
                            # Normal comparison
                            page_a = pdf_a.pages[idx_a]
                            page_b = pdf_b.pages[idx_b]
                            
                            # Calculate scale factors
                            scale_x_a = img_a.width / float(page_a.width)
                            scale_y_a = img_a.height / float(page_a.height)
                            scale_x_b = img_b.width / float(page_b.width)
                            scale_y_b = img_b.height / float(page_b.height)
                            
                            words_a = page_a.extract_words()
                            words_b = page_b.extract_words()
                            
                            page_text_a = [w['text'] for w in words_a]
                            page_text_b = [w['text'] for w in words_b]
                            
                            matcher = difflib.SequenceMatcher(None, page_text_a, page_text_b)
                            
                            width_a, height_a = img_a.size
                            width_b, height_b = img_b.size
                            combined = Image.new('RGBA', (width_a + width_b, max(height_a, height_b)))
                            combined.paste(img_a, (0, 0))
                            combined.paste(img_b, (width_a, 0))
                            
                            overlay = Image.new('RGBA', combined.size, (0, 0, 0, 0))
                            draw = ImageDraw.Draw(overlay)
                            
                            has_changes = False
                            
                            for inner_tag, ii1, ii2, jj1, jj2 in matcher.get_opcodes():
                                if inner_tag == 'equal': continue
                                has_changes = True
                                if inner_tag in ('replace', 'delete'):
                                    for w_idx in range(ii1, ii2):
                                        w = words_a[w_idx]
                                        draw.rectangle([w['x0']*scale_x_a, w['top']*scale_y_a, w['x1']*scale_x_a, w['bottom']*scale_y_a], fill=(255, 180, 180, 128))
                                if inner_tag in ('replace', 'insert'):
                                    for w_idx in range(jj1, jj2):
                                        w = words_b[w_idx]
                                        draw.rectangle([w['x0']*scale_x_b + width_a, w['top']*scale_y_b, w['x1']*scale_x_b + width_a, w['bottom']*scale_y_b], fill=(180, 255, 180, 128))
                            
                            final_img = None
                            if has_changes or idx_a != idx_b:
                                combined = Image.alpha_composite(combined, overlay)
                                final_img = combined.convert("RGB")
                                
                                label_text = f"Left: Page {idx_a+1} | Right: Page {idx_b+1}"
                                bg_color = "white"
                                if idx_a != idx_b:
                                    label_text += f" (Shifted)"
                                    bg_color = "yellow"
                                
                                self.draw_labels(final_img, label_text, bg_color=bg_color)
                                diff_results.append(final_img)
                            else:
                                # No changes
                                final_img = combined.convert("RGB")
                                label_text = f"Left: Page {idx_a+1} | Right: Page {idx_b+1} (No Differences)"
                                self.draw_labels(final_img, label_text, bg_color="white")
                                diff_results.append(final_img)

                        elif img_a is None and img_b:
                            # Extra page in B (Insertion)
                            img_a_blank = self.create_blank_page(img_b.width, img_b.height)
                            combined = Image.new('RGB', (img_a_blank.width + img_b.width, img_b.height))
                            combined.paste(img_a_blank, (0, 0))
                            combined.paste(img_b, (img_a_blank.width, 0))
                            
                            # Right: Page X (Added) (Green)
                            self.draw_labels(combined, f"Page {idx_b+1} (Added)", bg_color="#ccffcc", x=img_a_blank.width + 10)
                            # Left: Blank (No label needed or "Missing" if desired, but user said "keep empty page in left")
                            
                            diff_results.append(combined)
                            
                        elif img_b is None and img_a:
                            # Extra page in A (Deletion)
                            img_b_blank = self.create_blank_page(img_a.width, img_a.height)
                            combined = Image.new('RGB', (img_a.width + img_b_blank.width, img_a.height))
                            combined.paste(img_a, (0, 0))
                            combined.paste(img_b_blank, (img_a.width, 0))
                            
                            # Left: Page X (Missing) (Red)
                            self.draw_labels(combined, f"Page {idx_a+1} (Missing)", bg_color="#ffcccc", x=10)
                            # Right: Blank (No label)
                            
                            diff_results.append(combined)
                        
                elif tag == 'delete':
                    # Pages in A but not in B
                    for k in range(i1, i2):
                        img_a = images_a[k]
                        img_b = self.create_blank_page(img_a.width, img_a.height)
                        
                        combined = Image.new('RGB', (img_a.width + img_b.width, img_a.height))
                        combined.paste(img_a, (0, 0))
                        combined.paste(img_b, (img_a.width, 0))
                        
                        # Left: Page X (Missing) (Red)
                        self.draw_labels(combined, f"Page {k+1} (Missing)", bg_color="#ffcccc", x=10)
                        # Right: Blank (No label)
                        
                        diff_results.append(combined)
                        
                elif tag == 'insert':
                    # Pages in B but not in A
                    for k in range(j1, j2):
                        img_b = images_b[k]
                        img_a = self.create_blank_page(img_b.width, img_b.height)
                        
                        combined = Image.new('RGB', (img_a.width + img_b.width, img_b.height))
                        combined.paste(img_a, (0, 0))
                        combined.paste(img_b, (img_a.width, 0))
                        
                        # Right: Page X (Added) (Green)
                        self.draw_labels(combined, f"Page {k+1} (Added)", bg_color="#ccffcc", x=img_a.width + 10)
                        
                        diff_results.append(combined)
                        
        return diff_results
