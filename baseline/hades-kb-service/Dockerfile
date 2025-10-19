# Use a regular Python image to install packages
FROM 288440521858.dkr.ecr.ap-southeast-1.amazonaws.com/python:latest as builder

# Install PostgreSQL development libraries
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# install poetry and all dependencies
COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock

RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --only main

# Stage 2: Final stage with distroless image
FROM 288440521858.dkr.ecr.ap-southeast-1.amazonaws.com/distroless/python3-debian12:latest

WORKDIR /app

# Copy necessary libraries from builder
# COPY --from=builder /usr/lib/aarch64-linux-gnu/libpq.so.5 /usr/lib/aarch64-linux-gnu/libpq.so.5
# COPY --from=builder /usr/lib/aarch64-linux-gnu/libldap-2.5.so.0 /usr/lib/aarch64-linux-gnu/libldap-2.5.so.0
# COPY --from=builder /usr/lib/aarch64-linux-gnu/liblber-2.5.so.0 /usr/lib/aarch64-linux-gnu/liblber-2.5.so.0
# COPY --from=builder /usr/lib/aarch64-linux-gnu/libsasl2.so.2 /usr/lib/aarch64-linux-gnu/libsasl2.so.2
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
COPY scripts scripts
COPY app app
COPY pyproject.toml pyproject.toml

# Set Python path
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages:/app

# Run the application
EXPOSE 8088
ENTRYPOINT ["python", "-m", "gunicorn", "app.server:app", "-c", "scripts/gunicorn_conf.py"]
