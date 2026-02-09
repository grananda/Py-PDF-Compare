import argparse
import os
import sys
import img2pdf
from io import BytesIO
from comparator import PDFComparator

def main():
    parser = argparse.ArgumentParser(description="Compare two PDF files and generate a visual diff report.")
    parser.add_argument("file_a", help="Path to the first PDF file (Original)")
    parser.add_argument("file_b", help="Path to the second PDF file (Modified)")
    parser.add_argument("-o", "--output", default="report.pdf", help="Path to save the output report (default: report.pdf)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file_a):
        print(f"Error: File '{args.file_a}' not found.")
        sys.exit(1)
        
    if not os.path.exists(args.file_b):
        print(f"Error: File '{args.file_b}' not found.")
        sys.exit(1)
        
    print(f"Comparing '{args.file_a}' and '{args.file_b}'...")
    
    try:
        comparator = PDFComparator(args.file_a, args.file_b)
        diff_images = comparator.compare_visuals()
        
        if not diff_images:
            print("No visual differences found.")
        else:
            print(f"Report generated with {len(diff_images)} page(s).")
            print(f"Saving report to '{args.output}'...")

            # Convert images to JPEG format with compression for smaller file size
            # Then use img2pdf to create an optimized PDF
            jpeg_buffers = []
            for img in diff_images:
                buffer = BytesIO()
                # Convert to RGB if needed (RGBA can't be saved as JPEG)
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                # Save as JPEG with 75% quality for optimal file size
                img.save(buffer, format='JPEG', quality=75, optimize=True)
                jpeg_buffers.append(buffer.getvalue())

            # Use img2pdf to create optimized PDF from compressed JPEGs
            with open(args.output, 'wb') as f:
                f.write(img2pdf.convert(jpeg_buffers))

            print("Done.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
