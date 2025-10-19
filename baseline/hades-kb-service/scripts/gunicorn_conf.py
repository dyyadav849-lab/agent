import os

# debugging
reload = False  # default: False

# logging
loglevel = "info"  # default: "info"

# server socket
host = os.environ.get("HOST", "0.0.0.0")  # nosec # noqa: S104
port = os.environ.get("PORT", "8088")
bind = [f"{host}:{port}"]  # default: ["127.0.0.1:8088"]

# secure scheme settings
forwarded_allow_ips = (
    "*"  # required to allow for redirections to server, e.g. for oidc login flow
)

# worker processes
workers = 4  # default: 1, You may need to adjust this based on your application needed
worker_class = "uvicorn.workers.UvicornWorker"  # default: "sync", https://fastapi.tiangolo.com/deployment/server-workers/#run-gunicorn-with-uvicorn-workers

# restarting rules
max_requests = 0  # default: 0, Gunicorn restarts workers after this many requests to help limit the damage of memory leaks. 0 means disabled this feature
max_requests_jitter = 0  # default: 0, random value to add or subtract from max_requests to avoid restarting all workers at the same time

# timeout
# set a longer timeout because GPT endpoint mar require more time to respond to complex queries
timeout = 300  # default: 30, Adjust based on the complexity of your task
graceful_timeout = 300  # default: 30, Adjust based on the complexity of your task

keepalive = 2  # default: 2
