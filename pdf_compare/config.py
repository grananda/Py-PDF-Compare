# PDF Comparison Configuration
# Vector-based rendering configuration

# NOTE: DPI and JPEG_QUALITY parameters are kept for backward compatibility
# but are no longer used in the vector-based rendering approach.
#
# The new implementation uses PyMuPDF to preserve the original PDF vector content,
# which means:
# - Text remains searchable and selectable
# - File sizes are significantly smaller (20-70x reduction)
# - No quality loss from rasterization

# Legacy parameters (not used in vector rendering)
PDF_RENDER_DPI = 75
JPEG_QUALITY = 75
