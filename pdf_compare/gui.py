import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import sys
import queue
import tempfile
import subprocess
import platform
import fitz  # PyMuPDF for PDF to image conversion (preview only)
from PIL import Image
import io

# Load configuration from config.py (kept for backward compatibility)
try:
    from pdf_compare.config import PDF_RENDER_DPI, JPEG_QUALITY
except ImportError:
    # Fallback defaults if config.py is not found
    PDF_RENDER_DPI = 75
    JPEG_QUALITY = 75

from pdf_compare.comparator import PDFComparator

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PDF Comparison Tool - Vector Edition")
        self.geometry("1400x950")
        self.minsize(1200, 800)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(5, weight=1)  # Make scrollable_frame expandable

        self.file_a_path = ""
        self.file_b_path = ""
        self.output_path = ""
        self.pdf_bytes = None

        # Queue for thread-safe communication
        self.result_queue = queue.Queue()

        # Title Label
        title_label = ctk.CTkLabel(
            self,
            text="PDF Comparison Tool",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(10, 5))

        # File A Selection
        self.label_a = ctk.CTkLabel(self, text="Original PDF: Not Selected")
        self.label_a.grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.btn_a = ctk.CTkButton(self, text="Select PDF A", command=self.select_file_a, width=150)
        self.btn_a.grid(row=1, column=1, padx=20, pady=5, sticky="e")

        # File B Selection
        self.label_b = ctk.CTkLabel(self, text="Modified PDF: Not Selected")
        self.label_b.grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.btn_b = ctk.CTkButton(self, text="Select PDF B", command=self.select_file_b, width=150)
        self.btn_b.grid(row=2, column=1, padx=20, pady=5, sticky="e")

        # Compare Button
        self.btn_compare = ctk.CTkButton(
            self,
            text="Compare PDFs",
            command=self.start_comparison,
            height=35,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.btn_compare.grid(row=3, column=0, columnspan=2, padx=20, pady=(10, 5))

        # Action buttons frame
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=4, column=0, columnspan=2, padx=20, pady=5, sticky="ew")

        # Progress bar (hidden by default)
        self.progress_bar = ctk.CTkProgressBar(self.action_frame)
        self.progress_bar.pack(pady=5)
        self.progress_bar.pack_forget()

        # Status label
        self.status_label = ctk.CTkLabel(
            self.action_frame,
            text="",
            font=ctk.CTkFont(size=10)
        )
        self.status_label.pack(pady=2)

        # Buttons frame (always visible but disabled until comparison is complete)
        self.buttons_frame = ctk.CTkFrame(self.action_frame)
        self.buttons_frame.pack(pady=5)

        self.btn_download = ctk.CTkButton(
            self.buttons_frame,
            text="Download Report",
            command=self.download_report,
            width=150,
            fg_color="green",
            hover_color="darkgreen",
            state="disabled"
        )
        self.btn_download.pack(side="left", padx=10)

        self.btn_open = ctk.CTkButton(
            self.buttons_frame,
            text="Open in PDF Viewer",
            command=self.open_report,
            width=150,
            state="disabled"
        )
        self.btn_open.pack(side="left", padx=10)

        self.btn_save_as = ctk.CTkButton(
            self.buttons_frame,
            text="Save As...",
            command=self.save_report_as,
            width=150,
            state="disabled"
        )
        self.btn_save_as.pack(side="left", padx=10)

        # Output Area - Scrollable Frame for Preview Images
        self.scrollable_frame = ctk.CTkScrollableFrame(self, width=1300, height=480)
        self.scrollable_frame.grid(row=5, column=0, columnspan=2, padx=20, pady=(5, 10), sticky="nsew")

        self.preview_label = ctk.CTkLabel(
            self.scrollable_frame,
            text="Select two PDF files to compare",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.preview_label.pack(pady=20)

        # Info label
        info_label = ctk.CTkLabel(
            self,
            text="Vector-based PDF output • Preview rendered at lower resolution for display",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        info_label.grid(row=6, column=0, columnspan=2, pady=10)

    def select_file_a(self):
        filename = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if filename:
            self.file_a_path = filename
            self.label_a.configure(text=f"Original PDF: {os.path.basename(filename)}")

    def select_file_b(self):
        filename = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if filename:
            self.file_b_path = filename
            self.label_b.configure(text=f"Modified PDF: {os.path.basename(filename)}")

    def start_comparison(self):
        if not self.file_a_path or not self.file_b_path:
            messagebox.showerror("Error", "Please select both PDF files.")
            return

        self.btn_compare.configure(state="disabled", text="Comparing...")
        self.btn_download.configure(state="disabled")
        self.btn_open.configure(state="disabled")
        self.btn_save_as.configure(state="disabled")
        self.preview_label.pack_forget()

        # Clear previous results
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Show progress
        self.status_label.configure(text="Comparing PDFs...", text_color="gray")
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        self.progress_bar.start()

        # Run in thread to not freeze GUI
        thread = threading.Thread(target=self.run_comparison, daemon=False)
        thread.start()

        # Start checking for results
        self.check_queue()

    def run_comparison(self):
        try:
            print("Starting comparison...")
            comparator = PDFComparator(self.file_a_path, self.file_b_path)

            print("Calling compare_visuals()...")
            pdf_bytes = comparator.compare_visuals()
            print(f"Comparison complete. Generated {len(pdf_bytes)} bytes.")

            if pdf_bytes:
                file_size_mb = len(pdf_bytes) / (1024 * 1024)

                # Save to temporary file
                temp_dir = tempfile.gettempdir()
                self.output_path = os.path.join(temp_dir, "pdf_comparison_report.pdf")

                with open(self.output_path, 'wb') as f:
                    f.write(pdf_bytes)

                print(f"Temporary report saved to: {self.output_path} ({file_size_mb:.2f} MB)")

                # Convert PDF to images for preview (using PyMuPDF)
                print("Generating preview images...")
                preview_images = self.pdf_to_images(pdf_bytes)
                print(f"Generated {len(preview_images)} preview images")

                self.result_queue.put(('success', (self.output_path, file_size_mb, preview_images)))
            else:
                self.result_queue.put(('empty', None))

        except Exception as e:
            print(f"Error during comparison: {e}")
            import traceback
            traceback.print_exc()
            self.result_queue.put(('error', str(e)))

    def pdf_to_images(self, pdf_bytes, dpi=100):
        """Convert PDF bytes to PIL Images for preview (lower DPI for display)"""
        images = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        for page_num in range(len(doc)):
            page = doc[page_num]
            # Render at lower DPI for preview (saves memory)
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)

            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)

        doc.close()
        return images

    def check_queue(self):
        """Check the queue for results from the worker thread"""
        try:
            # Non-blocking check
            result = self.result_queue.get_nowait()
            result_type = result[0]
            print(f"Got result from queue: {result_type}")

            self.progress_bar.stop()
            self.progress_bar.pack_forget()

            if result_type == 'success':
                output_path, file_size_mb, preview_images = result[1]
                self.update_ui_success(output_path, file_size_mb, preview_images)
            elif result_type == 'empty':
                self.update_ui_empty()
            elif result_type == 'error':
                self.update_ui_error(result[1])

        except queue.Empty:
            # No result yet, check again in 100ms
            self.after(100, self.check_queue)

    def update_ui_success(self, output_path, file_size_mb, preview_images):
        print(f"Displaying {len(preview_images)} preview images...")

        # Show status
        self.status_label.configure(
            text=f"✓ Comparison complete! Report size: {file_size_mb:.2f} MB • Vector-based PDF (text is searchable)",
            text_color="green"
        )

        # Enable action buttons
        self.btn_download.configure(state="normal")
        self.btn_open.configure(state="normal")
        self.btn_save_as.configure(state="normal")

        # Display preview images
        if preview_images:
            for i, img in enumerate(preview_images):
                print(f"  Displaying preview {i+1}/{len(preview_images)} (size: {img.size})")

                # Resize for display if needed
                display_width = 1280
                if img.width > display_width:
                    ratio = display_width / float(img.width)
                    display_height = int((float(img.height) * float(ratio)))
                    img_resized = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
                else:
                    img_resized = img

                ctk_img = ctk.CTkImage(
                    light_image=img_resized,
                    dark_image=img_resized,
                    size=(img_resized.width, img_resized.height)
                )

                lbl = ctk.CTkLabel(self.scrollable_frame, text="", image=ctk_img)
                lbl.image = ctk_img  # Keep reference
                lbl.pack(pady=10)

        self.btn_compare.configure(state="normal", text="Compare PDFs")
        print("UI update complete")

    def update_ui_empty(self):
        self.status_label.configure(
            text="No visual differences found between the PDFs.",
            text_color="blue"
        )

        no_diff_label = ctk.CTkLabel(
            self.scrollable_frame,
            text="✓ No Differences Found",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="green"
        )
        no_diff_label.pack(pady=50)

        self.btn_compare.configure(state="normal", text="Compare PDFs")

    def update_ui_error(self, error_msg):
        self.status_label.configure(
            text=f"✗ Error occurred",
            text_color="red"
        )

        error_label = ctk.CTkLabel(
            self.scrollable_frame,
            text=f"Error: {error_msg}",
            font=ctk.CTkFont(size=12),
            text_color="red"
        )
        error_label.pack(pady=20)

        messagebox.showerror("Error", f"An error occurred: {error_msg}")
        self.btn_compare.configure(state="normal", text="Compare PDFs")

    def download_report(self):
        """Download report to Downloads folder automatically"""
        if not self.output_path or not os.path.exists(self.output_path):
            messagebox.showerror("Error", "Report file not found.")
            return

        try:
            # Get Downloads folder path
            if platform.system() == "Windows":
                import winreg
                sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
                downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                    downloads_folder = winreg.QueryValueEx(key, downloads_guid)[0]
            else:
                # macOS and Linux
                downloads_folder = os.path.join(os.path.expanduser('~'), 'Downloads')

            # Generate unique filename
            base_name = "pdf_comparison_report"
            extension = ".pdf"
            counter = 1
            filename = os.path.join(downloads_folder, f"{base_name}{extension}")

            # If file exists, add number
            while os.path.exists(filename):
                filename = os.path.join(downloads_folder, f"{base_name}_{counter}{extension}")
                counter += 1

            # Copy file
            import shutil
            shutil.copy2(self.output_path, filename)

            # Show success message with option to open folder
            result = messagebox.showinfo(
                "Download Complete",
                f"Report downloaded successfully!\n\n{filename}\n\nFile size: {os.path.getsize(filename) / (1024*1024):.2f} MB"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to download report: {e}")

    def open_report(self):
        if not self.output_path or not os.path.exists(self.output_path):
            messagebox.showerror("Error", "Report file not found.")
            return

        try:
            # Open with default PDF viewer
            system = platform.system()
            if system == "Windows":
                os.startfile(self.output_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", self.output_path])
            else:  # Linux
                subprocess.run(["xdg-open", self.output_path])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open report: {e}")

    def save_report_as(self):
        if not self.output_path or not os.path.exists(self.output_path):
            messagebox.showerror("Error", "Report file not found.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            initialfile="comparison_report.pdf"
        )

        if filename:
            try:
                # Copy the temporary file to the selected location
                import shutil
                shutil.copy2(self.output_path, filename)
                messagebox.showinfo("Success", f"Report saved successfully!\n\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save report: {e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
