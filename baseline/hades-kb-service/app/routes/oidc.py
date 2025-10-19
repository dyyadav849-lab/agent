from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse

from app.auth.errors import UnauthenticatedError
from app.auth.oidc import oauth, verify_token
from app.auth.sessions.redis_session_store import redis_session_store
from app.core.config import app_config

oidc_router = APIRouter()


# login handles the start of the login flow, hitting the provider's Authorize endpoint
@oidc_router.get("/auth/oidc/login")
async def login(request: Request) -> RedirectResponse:
    redirect_uri = request.url_for("auth_callback")
    return await oauth.dex.authorize_redirect(request, redirect_uri)


# auth_callback handles the oauth dance's callback exchange for a token
@oidc_router.get("/auth/oidc/callback")
async def auth_callback(request: Request) -> RedirectResponse:
    try:
        token = await oauth.dex.authorize_access_token(request)
    except OAuthError:
        raise UnauthenticatedError from OAuthError
    user = token.get("userinfo")
    if not user:
        raise ValueError
    # can do extra checks/ authorize with user at this stage if needed
    # we're skipping this for the poc

    # set the obtained JWT to the session for use
    id_token = token.get("id_token")
    access_token = token.get("access_token")
    refresh_token = token.get("refresh_token") or ""

    request.session["id_token"] = id_token
    request.session["access_token"] = access_token

    decoded_claims = await verify_token(id_token)

    username = decoded_claims.get("email").split("@")[0]
    expiry = decoded_claims.get("exp")

    redis_session_store.set_session_token(username, "access_token", access_token)
    redis_session_store.set_session_token(username, "id_token", id_token)

    if refresh_token != "":
        request.session["refresh_token"] = refresh_token
        redis_session_store.set_session_token(username, "refresh_token", refresh_token)

    redis_session_store.set_expiry(username, expiry)
    return RedirectResponse(url=app_config.auth_login_redirect)


# logout clears the session
@oidc_router.post("/auth/oidc/logout")
async def logout(request: Request) -> dict[str, str]:
    # remove the session token if it is there
    # do necessary cleanup here
    id_token = request.session.get("id_token")
    if id_token:
        decoded_claims = await verify_token(id_token)
        username = decoded_claims.get("email").split("@")[0]
        redis_session_store.clear(username)
    request.session.clear()
    return {}
