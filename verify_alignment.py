import unittest
from unittest.mock import MagicMock, patch
from comparator import PDFComparator
from PIL import Image, ImageDraw
import difflib

class TestPDFComparator(unittest.TestCase):
    def setUp(self):
        self.comparator = PDFComparator("dummy_a.pdf", "dummy_b.pdf")

    def test_align_pages_insert(self):
        # A: [P1, P2]
        # B: [P1, New, P2]
        text_a = ["Page 1 Content", "Page 2 Content"]
        text_b = ["Page 1 Content", "Inserted Page", "Page 2 Content"]
        
        opcodes = self.comparator.align_pages(text_a, text_b)
        
        # Expected: equal (0,1,0,1), insert (1,1,1,2), equal (1,2,2,3)
        # Note: difflib might group things differently depending on content, but this is distinct enough.
        print(f"Insert Opcodes: {opcodes}")
        
        # Verify we have an insert
        has_insert = any(tag == 'insert' for tag, _, _, _, _ in opcodes)
        self.assertTrue(has_insert, "Should detect insertion")

    def test_align_pages_delete(self):
        # A: [P1, P2, P3]
        # B: [P1, P3]
        text_a = ["Page 1", "Page 2", "Page 3"]
        text_b = ["Page 1", "Page 3"]
        
        opcodes = self.comparator.align_pages(text_a, text_b)
        print(f"Delete Opcodes: {opcodes}")
        
        has_delete = any(tag == 'delete' for tag, _, _, _, _ in opcodes)
        self.assertTrue(has_delete, "Should detect deletion")

    @patch('comparator.pdfplumber.open')
    @patch('comparator.convert_from_path')
    def test_compare_visuals_logic(self, mock_convert, mock_pdf_open):
        # Mock images
        img_size = (100, 100)
        img_a = [Image.new('RGB', img_size, 'white'), Image.new('RGB', img_size, 'white')]
        img_b = [Image.new('RGB', img_size, 'white'), Image.new('RGB', img_size, 'white'), Image.new('RGB', img_size, 'white')]
        
        # Mock PDF objects
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.side_effect = ["Page 1", "Page 2", "Page 1", "Inserted", "Page 2"] # A then B
        
        # Make pages identical where they match
        # Pair 1: A[0] vs B[0] -> Identical
        # Pair 2: A[1] vs B[2] -> Identical (but shifted)
        
        mock_page.extract_words.side_effect = [
            [{'text': 'Hello', 'x0':0, 'top':0, 'x1':10, 'bottom':10}], # A[0]
            [{'text': 'Hello', 'x0':0, 'top':0, 'x1':10, 'bottom':10}], # B[0] -> Identical
            [{'text': 'Foo', 'x0':0, 'top':0, 'x1':10, 'bottom':10}],   # A[1]
            [{'text': 'Foo', 'x0':0, 'top':0, 'x1':10, 'bottom':10}]    # B[2] -> Identical
        ]
        
        mock_page.width = 100
        mock_page.height = 100
        mock_pdf.pages = [mock_page] * 5 # Just needs to be indexable
        
        # Context manager mock
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        
        # Mock extract_text to return controlled lists
        with patch.object(self.comparator, 'extract_text') as mock_extract:
            mock_extract.side_effect = [
                ["Page 1", "Page 2"], # A
                ["Page 1", "Inserted", "Page 2"] # B
            ]
            
            # Mock convert_to_images
            with patch.object(self.comparator, 'convert_to_images') as mock_convert_method:
                mock_convert_method.side_effect = [
                    [Image.new('RGB', img_size, 'red'), Image.new('RGB', img_size, 'red')], # A images
                    [Image.new('RGB', img_size, 'blue'), Image.new('RGB', img_size, 'blue'), Image.new('RGB', img_size, 'blue')] # B images
                ]
                
                # Run comparison
                # We want to verify the text passed to draw_labels
                with patch.object(self.comparator, 'draw_labels') as mock_draw_labels:
                    results = self.comparator.compare_visuals()
                    
                    print(f"Generated {len(results)} diff images")
                    
                    # Verify calls to draw_labels
                    # We expect 3 calls (one for each page pair)
                    self.assertEqual(mock_draw_labels.call_count, 3)
                    
                    # Check args
                    # Call 1: Match (A0 vs B0) -> "Left: Page 1 | Right: Page 1 (No Differences)"
                    args1, _ = mock_draw_labels.call_args_list[0]
                    self.assertIn("Left: Page 1 | Right: Page 1", args1[1])
                    
                    # Call 2: Insert (B1) -> Right: "Page 2 (Added)"
                    # We expect 1 call for this image now (only Right label)
                    # Note: The mock_draw_labels.call_args_list will accumulate calls.
                    # Call 1 was Match.
                    # Call 2 is Insert -> "Page 2 (Added)"
                    args2, kwargs2 = mock_draw_labels.call_args_list[1]
                    self.assertIn("Page 2 (Added)", args2[1])
                    # Check x coordinate if possible, but kwargs might be in args depending on how called
                    if 'x' in kwargs2:
                        self.assertGreater(kwargs2['x'], 100) # Should be on the right side (width=100)
                    
                    # Call 3: Shift (A1 vs B2) -> "Left: Page 2 | Right: Page 3 (Shifted)"
                    args3, _ = mock_draw_labels.call_args_list[2]
                    self.assertIn("Left: Page 2", args3[1])
                    self.assertIn("Right: Page 3", args3[1])
                    self.assertIn("Shifted", args3[1])
                    
                    self.assertEqual(len(results), 3, "Should generate 3 comparison images")

    @patch('comparator.pdfplumber.open')
    @patch('comparator.convert_from_path')
    def test_unequal_replace_block(self, mock_convert, mock_pdf_open):
        # Scenario: Page 1 in A is replaced by Page 1 and Page 2 in B.
        # This is a 'replace' block of length 1 vs 2.
        
        # Mock images
        img_size = (100, 100)
        img_a = [Image.new('RGB', img_size, 'white')]
        img_b = [Image.new('RGB', img_size, 'white'), Image.new('RGB', img_size, 'white')]
        
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Content"
        mock_page.extract_words.return_value = []
        mock_page.width = 100
        mock_page.height = 100
        mock_pdf.pages = [mock_page] * 5
        
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        
        with patch.object(self.comparator, 'extract_text') as mock_extract:
            # Force align_pages to return a replace block
            with patch.object(self.comparator, 'align_pages') as mock_align:
                mock_align.return_value = [('replace', 0, 1, 0, 2)] # 1 page in A -> 2 pages in B
                
                with patch.object(self.comparator, 'convert_to_images') as mock_convert_method:
                    mock_convert_method.side_effect = [img_a, img_b]
                    
                    with patch.object(self.comparator, 'draw_labels') as mock_draw_labels:
                        results = self.comparator.compare_visuals()
                        
                        print(f"Generated {len(results)} diff images for unequal replace")
                        self.assertEqual(len(results), 2)
                        
                        # 1st image: Match (A0 vs B0)
                        args1, _ = mock_draw_labels.call_args_list[0]
                        self.assertIn("Left: Page 1 | Right: Page 1", args1[1])
                        
                        # 2nd image: Insert (None vs B1) -> Right: "Page 2 (Added)"
                        args2, kwargs2 = mock_draw_labels.call_args_list[1]
                        self.assertIn("Page 2 (Added)", args2[1])
                        if 'x' in kwargs2:
                             self.assertGreater(kwargs2['x'], 100)

if __name__ == '__main__':
    unittest.main()
