import pdfplumber
from pdf2image import convert_from_path
import difflib
import os
from PIL import Image, ImageChops, ImageDraw
import cv2
import numpy as np

class PDFComparator:
    def __init__(self, file_path_a, file_path_b):
        self.file_path_a = file_path_a
        self.file_path_b = file_path_b

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

    def convert_to_images(self, file_path):
        # This requires poppler installed and in PATH
        # User provided path: C:\poppler-25.11.0\Library\bin
        poppler_path = r"C:\poppler-25.11.0\Library\bin"
        try:
            return convert_from_path(file_path, poppler_path=poppler_path)
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            return []

class PDFComparator:
    def __init__(self, file_path_a, file_path_b):
        self.file_path_a = file_path_a
        self.file_path_b = file_path_b

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

    def convert_to_images(self, file_path):
        # This requires poppler installed and in PATH
        # User provided path: C:\poppler-25.11.0\Library\bin
        poppler_path = r"C:\poppler-25.11.0\Library\bin"
        try:
            return convert_from_path(file_path, poppler_path=poppler_path)
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            return []

    def compare_visuals(self):
        # Convert pages to images for display
        images_a = self.convert_to_images(self.file_path_a)
        images_b = self.convert_to_images(self.file_path_b)
        
        diff_results = []
        
        # Open PDFs with pdfplumber for text coordinates
        with pdfplumber.open(self.file_path_a) as pdf_a, pdfplumber.open(self.file_path_b) as pdf_b:
            max_pages = min(len(images_a), len(images_b), len(pdf_a.pages), len(pdf_b.pages))
            
            for i in range(max_pages):
                img_a = images_a[i]
                img_b = images_b[i]
                
                page_a = pdf_a.pages[i]
                page_b = pdf_b.pages[i]
                
                # Calculate scale factors (Image Pixels / PDF Points)
                scale_x_a = img_a.width / float(page_a.width)
                scale_y_a = img_a.height / float(page_a.height)
                
                scale_x_b = img_b.width / float(page_b.width)
                scale_y_b = img_b.height / float(page_b.height)
                
                # Extract words with coordinates
                words_a = page_a.extract_words()
                words_b = page_b.extract_words()
                
                # Prepare text sequences for comparison
                text_a = [w['text'] for w in words_a]
                text_b = [w['text'] for w in words_b]
                
                # Use SequenceMatcher to find differences
                matcher = difflib.SequenceMatcher(None, text_a, text_b)
                
                # Create combined image
                width_a, height_a = img_a.size
                width_b, height_b = img_b.size
                combined = Image.new('RGBA', (width_a + width_b, max(height_a, height_b)))
                combined.paste(img_a, (0, 0))
                combined.paste(img_b, (width_a, 0))
                
                # Overlay for highlights
                overlay = Image.new('RGBA', combined.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)
                
                has_changes = False
                
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag == 'equal':
                        continue
                    
                    has_changes = True
                    
                    if tag == 'replace' or tag == 'delete':
                        # Highlight words in A (Red)
                        for k in range(i1, i2):
                            word = words_a[k]
                            # Scale coordinates
                            x0 = word['x0'] * scale_x_a
                            top = word['top'] * scale_y_a
                            x1 = word['x1'] * scale_x_a
                            bottom = word['bottom'] * scale_y_a
                            
                            # Soft Red for Subtraction
                            draw.rectangle([x0, top, x1, bottom], fill=(255, 180, 180, 128))
                            
                    if tag == 'replace' or tag == 'insert':
                        # Highlight words in B (Green)
                        for k in range(j1, j2):
                            word = words_b[k]
                            # Scale coordinates and shift by width_a
                            x0 = word['x0'] * scale_x_b + width_a
                            top = word['top'] * scale_y_b
                            x1 = word['x1'] * scale_x_b + width_a
                            bottom = word['bottom'] * scale_y_b
                            
                            # Soft Green for Addition
                            draw.rectangle([x0, top, x1, bottom], fill=(180, 255, 180, 128))
                
                if has_changes:
                    combined = Image.alpha_composite(combined, overlay)
                    diff_results.append(combined.convert("RGB"))
                else:
                    pass # No text changes
                    
        return diff_results
