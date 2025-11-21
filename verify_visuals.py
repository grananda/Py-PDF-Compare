from reportlab.pdfgen import canvas
from reportlab.lib.colors import red
from comparator import PDFComparator
import os

def create_visual_pdf_a(filename):
    c = canvas.Canvas(filename)
    c.drawString(100, 750, "Paragraph One: This text stays the same.")
    c.drawString(100, 700, "Paragraph Two: This text also stays the same but will move.")
    c.save()

def create_visual_pdf_b(filename):
    c = canvas.Canvas(filename)
    c.drawString(100, 750, "Paragraph One: This text stays the same.")
    c.drawString(100, 725, "INSERTED PARAGRAPH: This is new content.") # Insertion
    c.drawString(100, 700, "Paragraph Two: This text also stays the same but will move.") # Shifted down
    c.save()

def test_visual_comparison():
    pdf_a = "visual_test_a.pdf"
    pdf_b = "visual_test_b.pdf"
    
    create_visual_pdf_a(pdf_a)
    create_visual_pdf_b(pdf_b)
    
    comparator = PDFComparator(pdf_a, pdf_b)
    diff_images = comparator.compare_visuals()
    
    print(f"Generated {len(diff_images)} diff images.")
    
    if diff_images:
        diff_images[0].save("diff_result_preview.png")
        print("Saved diff_result_preview.png")
    
    # Cleanup
    # if os.path.exists(pdf_a):
    #     os.remove(pdf_a)
    # if os.path.exists(pdf_b):
    #     os.remove(pdf_b)

if __name__ == "__main__":
    test_visual_comparison()
