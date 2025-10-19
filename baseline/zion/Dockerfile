# Use a regular Python image to install packages
FROM 288440521858.dkr.ecr.ap-southeast-1.amazonaws.com/python:latest as builder

# Install PostgreSQL development libraries and build dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy poetry files
COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock

# install poetry and all dependencies
RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --only main

# Stage 2: Final stage with distroless image
FROM 288440521858.dkr.ecr.ap-southeast-1.amazonaws.com/distroless/python3-debian12:latest

WORKDIR /app

# Copy system libraries
COPY --from=builder /usr/lib/aarch64-linux-gnu /usr/lib/aarch64-linux-gnu

# Copy Python and required libraries
COPY --from=builder /usr/local/lib/libpython3.11.so.1.0 /usr/local/lib/libpython3.11.so.1.0
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11

# Copy the installed packages
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source code
COPY Makefile Makefile
COPY configs configs
COPY zion zion
COPY pyproject.toml pyproject.toml

# Set environment variables
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages:/app

# Run the application
EXPOSE 8000
ENTRYPOINT ["python", "-m", "gunicorn", "zion.main:app", "-c", "zion/gunicorn_conf.py"]
