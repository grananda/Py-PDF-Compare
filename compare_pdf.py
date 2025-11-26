import argparse
import os
import sys
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
            
            diff_images[0].save(args.output, save_all=True, append_images=diff_images[1:])
            print("Done.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
