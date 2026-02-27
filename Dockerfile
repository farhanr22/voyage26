# Use a slim, multi-stage build 
FROM python:3.10-slim AS builder

WORKDIR /app

# Create a virtual environment
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN python -m venv $VIRTUAL_ENV

# Copy and install requirements in a separate layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# === Final Stage ===
FROM python:3.10-slim

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application source
COPY backend/ ./backend/

# Copy worker script
COPY worker.sh /app/worker.sh
RUN chmod +x /app/worker.sh

# Activate the virtual environment for subsequent commands
ENV PATH="/opt/venv/bin:$PATH"

# Expose the port the app runs on
EXPOSE 5000

# Run the application using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "backend.wsgi:app"]