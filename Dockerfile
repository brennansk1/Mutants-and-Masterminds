# Dockerfile for HeroForge M&M (Streamlit Version)

# --- Base Image ---
# Using a Python 3.10 slim image based on Debian Bullseye for a good balance of size and compatibility.
FROM python:3.10-slim-bullseye

# --- Environment Variables ---
# Prevents Python from buffering stdout and stderr, making logs appear immediately.
ENV PYTHONUNBUFFERED=1
# Prevents apt-get from asking for user input during installs.
ENV DEBIAN_FRONTEND=noninteractive

# --- System Dependencies ---
# Install system libraries required by WeasyPrint and potentially other Python packages.
# fontconfig is crucial for WeasyPrint to find and use system fonts for PDF generation.
# build-essential and python3-dev might be needed if some pip packages compile C extensions.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # WeasyPrint dependencies (Pango, Cairo, GDK-PixBuf, libffi)
    # and their own dependencies (fontconfig, freetype, etc.)
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    # XML/XSLT processing (often needed by WeasyPrint or related HTML/CSS parsing)
    libxml2-dev \
    libxslt1-dev \
    # Font management
    fontconfig \
    # Common utilities that might be helpful
    build-essential \
    python3-dev \
    && \
    # Clean up apt caches to reduce image size
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# --- Application Setup ---
# Set the working directory in the container.
WORKDIR /app

# Copy the requirements file first to leverage Docker cache layers.
# If requirements.txt doesn't change, this layer won't be rebuilt.
COPY requirements.txt .

# Install Python dependencies specified in requirements.txt.
# --no-cache-dir reduces image size by not storing the pip download cache.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the working directory.
# This includes app.py, core_engine.py, pdf_utils.py, and the rules/ and assets/ directories.
# Ensure you have a .dockerignore file to exclude unnecessary files (e.g., .git, __pycache__, venv).
COPY . .

# --- Port Exposure ---
# Expose the default port Streamlit runs on.
EXPOSE 8501

# --- Healthcheck ---
# Basic healthcheck to see if the Streamlit server is responding.
# Adjust timeout and interval as needed.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD streamlit healthcheck || exit 1

# --- Run Command ---
# Command to run the Streamlit application when the container starts.
# --server.port: Sets the port Streamlit listens on.
# --server.address=0.0.0.0: Makes Streamlit accessible from outside the container.
# --browser.gatherUsageStats=false: Disables telemetry.
# --client.showErrorDetails=true: Shows more detailed errors in the browser during development.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--browser.gatherUsageStats=false", "--client.showErrorDetails=true"]