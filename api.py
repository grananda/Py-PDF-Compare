#!/usr/bin/env python3
"""
PDF Compare API Server
Provides REST API endpoints to compare PDFs from JavaScript/Node.js
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile
from comparator import PDFComparator

app = Flask(__name__)
CORS(app)  # Enable CORS for JavaScript requests

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'PDF Compare API'})

@app.route('/compare', methods=['POST'])
def compare_pdfs():
    """
    Compare two PDF files

    Request:
        - file_a: PDF file (multipart/form-data)
        - file_b: PDF file (multipart/form-data)
        - output_format: 'pdf' or 'json' (optional, default: 'pdf')

    Response:
        - If output_format='pdf': Returns PDF file
        - If output_format='json': Returns JSON with comparison results
    """
    try:
        # Validate request
        if 'file_a' not in request.files or 'file_b' not in request.files:
            return jsonify({'error': 'Both file_a and file_b are required'}), 400

        file_a = request.files['file_a']
        file_b = request.files['file_b']
        output_format = request.form.get('output_format', 'pdf')

        if file_a.filename == '' or file_b.filename == '':
            return jsonify({'error': 'Both files must have filenames'}), 400

        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded files
            path_a = os.path.join(temp_dir, 'file_a.pdf')
            path_b = os.path.join(temp_dir, 'file_b.pdf')
            output_path = os.path.join(temp_dir, 'comparison_report.pdf')

            file_a.save(path_a)
            file_b.save(path_b)

            # Compare PDFs
            comparator = PDFComparator(path_a, path_b)

            if output_format == 'json':
                # Return JSON with text differences
                text_diff = comparator.compare_text()
                return jsonify({
                    'status': 'success',
                    'text_differences': text_diff,
                    'file_a': file_a.filename,
                    'file_b': file_b.filename
                })
            else:
                # Generate visual comparison report
                visual_results = comparator.compare_visuals()

                if not visual_results:
                    return jsonify({'error': 'No comparison results generated'}), 500

                # Save PDF report using PIL
                visual_results[0].save(output_path, save_all=True, append_images=visual_results[1:])

                # Return PDF file
                return send_file(
                    output_path,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name='comparison_report.pdf'
                )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/compare-urls', methods=['POST'])
def compare_pdf_urls():
    """
    Compare two PDFs from URLs

    Request JSON:
        {
            "url_a": "https://example.com/file_a.pdf",
            "url_b": "https://example.com/file_b.pdf",
            "output_format": "pdf" or "json" (optional)
        }
    """
    try:
        import requests

        data = request.get_json()
        if not data or 'url_a' not in data or 'url_b' not in data:
            return jsonify({'error': 'Both url_a and url_b are required'}), 400

        url_a = data['url_a']
        url_b = data['url_b']
        output_format = data.get('output_format', 'pdf')

        with tempfile.TemporaryDirectory() as temp_dir:
            # Download PDFs
            path_a = os.path.join(temp_dir, 'file_a.pdf')
            path_b = os.path.join(temp_dir, 'file_b.pdf')
            output_path = os.path.join(temp_dir, 'comparison_report.pdf')

            # Download file A
            response_a = requests.get(url_a, timeout=30)
            response_a.raise_for_status()
            with open(path_a, 'wb') as f:
                f.write(response_a.content)

            # Download file B
            response_b = requests.get(url_b, timeout=30)
            response_b.raise_for_status()
            with open(path_b, 'wb') as f:
                f.write(response_b.content)

            # Compare PDFs
            comparator = PDFComparator(path_a, path_b)

            if output_format == 'json':
                text_diff = comparator.compare_text()
                return jsonify({
                    'status': 'success',
                    'text_differences': text_diff,
                    'url_a': url_a,
                    'url_b': url_b
                })
            else:
                visual_results = comparator.compare_visuals()

                if not visual_results:
                    return jsonify({'error': 'No comparison results generated'}), 500

                visual_results[0].save(output_path, save_all=True, append_images=visual_results[1:])

                return send_file(
                    output_path,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name='comparison_report.pdf'
                )

    except requests.RequestException as e:
        return jsonify({'error': f'Failed to download PDF: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'

    print(f"Starting PDF Compare API on port {port}")
    print(f"Debug mode: {debug}")
    print("\nAvailable endpoints:")
    print("  GET  /health - Health check")
    print("  POST /compare - Compare two uploaded PDFs")
    print("  POST /compare-urls - Compare two PDFs from URLs")

    app.run(host='0.0.0.0', port=port, debug=debug)
