import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import sys
from PIL import Image
import queue

# Handle imports for both development and PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle - files are in 'python' subfolder
    sys.path.insert(0, os.path.join(sys._MEIPASS, 'python'))
from comparator import PDFComparator

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PDF Comparison Tool")
        self.geometry("1400x900")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.file_a_path = ""
        self.file_b_path = ""

        # Queue for thread-safe communication
        self.result_queue = queue.Queue()

        # File A Selection
        self.label_a = ctk.CTkLabel(self, text="PDF A: Not Selected")
        self.label_a.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        self.btn_a = ctk.CTkButton(self, text="Select PDF A", command=self.select_file_a)
        self.btn_a.grid(row=0, column=1, padx=20, pady=10, sticky="e")

        # File B Selection
        self.label_b = ctk.CTkLabel(self, text="PDF B: Not Selected")
        self.label_b.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.btn_b = ctk.CTkButton(self, text="Select PDF B", command=self.select_file_b)
        self.btn_b.grid(row=1, column=1, padx=20, pady=10, sticky="e")

        # Compare Button
        self.btn_compare = ctk.CTkButton(self, text="Compare PDFs", command=self.start_comparison)
        self.btn_compare.grid(row=2, column=0, padx=20, pady=20, sticky="e")
        
        # Download Button
        self.btn_download = ctk.CTkButton(self, text="Download Report", command=self.save_report, state="disabled")
        self.btn_download.grid(row=2, column=1, padx=20, pady=20, sticky="w")

        # Output Area - Scrollable Frame for Images
        self.scrollable_frame = ctk.CTkScrollableFrame(self, width=1300, height=700)
        self.scrollable_frame.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        
        self.diff_results = []

    def select_file_a(self):
        filename = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if filename:
            self.file_a_path = filename
            self.label_a.configure(text=f"PDF A: {os.path.basename(filename)}")

    def select_file_b(self):
        filename = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if filename:
            self.file_b_path = filename
            self.label_b.configure(text=f"PDF B: {os.path.basename(filename)}")

    def start_comparison(self):
        if not self.file_a_path or not self.file_b_path:
            messagebox.showerror("Error", "Please select both PDF files.")
            return

        self.btn_compare.configure(state="disabled", text="Comparing...")
        self.btn_download.configure(state="disabled")
        
        # Clear previous results
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Run in thread to not freeze GUI
        thread = threading.Thread(target=self.run_comparison, daemon=False)
        thread.start()

        # Start checking for results
        self.check_queue()

    def run_comparison(self):
        try:
            print("Starting comparison...")
            comparator = PDFComparator(self.file_a_path, self.file_b_path)
            # First do text comparison for logging/info if needed, but user wants visuals
            # Let's do visual comparison
            print("Calling compare_visuals()...")
            diff_images = comparator.compare_visuals()
            print(f"Comparison complete. Found {len(diff_images)} result images.")

            # Put result in queue
            print("Putting result in queue...")
            self.result_queue.put(('success', diff_images))
            print("Result queued.")

        except Exception as e:
            print(f"Error during comparison: {e}")
            import traceback
            traceback.print_exc()
            self.result_queue.put(('error', str(e)))

    def check_queue(self):
        """Check the queue for results from the worker thread"""
        try:
            # Non-blocking check
            result_type, data = self.result_queue.get_nowait()
            print(f"Got result from queue: {result_type}")

            if result_type == 'success':
                self.update_ui_result(data)
            elif result_type == 'error':
                self.update_ui_error(data)

        except queue.Empty:
            # No result yet, check again in 100ms
            self.after(100, self.check_queue)

    def update_ui_result(self, diff_images):
        print(f"update_ui_result called with {len(diff_images)} images")
        self.diff_results = diff_images

        if not diff_images:
            print("No differences found, showing message")
            lbl = ctk.CTkLabel(self.scrollable_frame, text="No visual differences found.")
            lbl.pack(pady=10)
            self.btn_download.configure(state="disabled")
        else:
            print(f"Processing {len(diff_images)} difference images...")
            for i, img in enumerate(diff_images):
                print(f"  Displaying image {i+1}/{len(diff_images)} (size: {img.size})")
                # Resize for display if too large
                display_width = 1300
                ratio = display_width / float(img.width)
                display_height = int((float(img.height) * float(ratio)))
                img_resized = img.resize((display_width, display_height), Image.Resampling.LANCZOS)

                ctk_img = ctk.CTkImage(light_image=img_resized, dark_image=img_resized, size=(display_width, display_height))

                lbl = ctk.CTkLabel(self.scrollable_frame, text="", image=ctk_img)
                lbl.image = ctk_img  # Keep a reference to prevent garbage collection
                lbl.pack(pady=10)

            print("All images displayed, enabling download button")
            self.btn_download.configure(state="normal")

        print("Re-enabling compare button")
        self.btn_compare.configure(state="normal", text="Compare PDFs")
        print("UI update complete")

    def save_report(self):
        if not self.diff_results:
            return
            
        filename = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if filename:
            try:
                # Save all images as a single PDF
                images = self.diff_results
                if images:
                    images[0].save(filename, save_all=True, append_images=images[1:])
                    messagebox.showinfo("Success", "Report saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save report: {e}")

    def update_ui_error(self, error_msg):
        messagebox.showerror("Error", f"An error occurred: {error_msg}")
        self.btn_compare.configure(state="normal", text="Compare PDFs")

if __name__ == "__main__":
    app = App()
    app.mainloop()
