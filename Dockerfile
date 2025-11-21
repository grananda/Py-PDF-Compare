# Use an official Python runtime as a parent image
# python:3.9-slim is based on Debian (Linux)
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# poppler-utils: Required for pdf2image
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Define the entrypoint so arguments can be passed directly
ENTRYPOINT ["python", "compare_pdf.py"]
