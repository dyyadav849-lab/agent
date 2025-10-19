from fastapi import APIRouter
from fastapi.responses import HTMLResponse

health_check_router = APIRouter()


# This is used for heartbeats and health checks, do not remove
@health_check_router.get(
    "/health_check", response_class=HTMLResponse, summary="Health Check"
)
async def health_check(greeting: str = "Hello", name: str = "World") -> HTMLResponse:
    """Returns greeting message."""

    return f"""
        <html>
        <head>
            <title>Health Check</title>
        </head>
        <body style="background-color:white;">
            <h1>{greeting} {name} 😊</h1>
        </body>
        </html>
        """
