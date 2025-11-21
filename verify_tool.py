from reportlab.pdfgen import canvas
from comparator import PDFComparator
import os

def create_pdf(filename, text):
    c = canvas.Canvas(filename)
    c.drawString(100, 750, text)
    c.save()

def test_comparison():
    pdf_a = "test_a.pdf"
    pdf_b = "test_b.pdf"
    
    create_pdf(pdf_a, "Hello World. This is PDF A.")
    create_pdf(pdf_b, "Hello World. This is PDF B.")
    
    comparator = PDFComparator(pdf_a, pdf_b)
    diff = comparator.compare_text()
    
    print("Diff Result:")
    for line in diff:
        print(line)
        
    # Cleanup
    if os.path.exists(pdf_a):
        os.remove(pdf_a)
    if os.path.exists(pdf_b):
        os.remove(pdf_b)

if __name__ == "__main__":
    test_comparison()
