import os

# debugging
reload = False  # default: False

# logging
loglevel = "info"  # default: "info"

# server socket
host = os.environ.get("HOST", "0.0.0.0")  # nosec # noqa: S104
port = os.environ.get("PORT", "8000")
bind = [f"{host}:{port}"]  # default: ["127.0.0.1:8000"]

# workers, default: 1
web_concurrency = os.environ.get("WEB_CONCURRENCY")
workers = int(web_concurrency) if web_concurrency else 1

# worker processes
worker_class = "uvicorn.workers.UvicornWorker"  # default: "sync"

max_requests = 0  # default: 0, Gunicorn restarts workers after this many requests to avoid memory leaks. 0 means disabled this feature
max_requests_jitter = 0  # default: 0, random value to add or subtract from max_requests to avoid restarting all workers at the same time

# Set a longer timeout because GPT API could take a long time to respond for complex queries
timeout = 300  # default: 30
graceful_timeout = 300  # default: 30
keepalive = 300  # default: 2
