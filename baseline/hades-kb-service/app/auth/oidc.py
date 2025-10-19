from datetime import datetime, timezone
from typing import List, Optional

from authlib.integrations.starlette_client import OAuth, OAuthError
from authlib.jose import jwt
from fastapi import Request

from app.auth.errors import UnauthenticatedError
from app.core.config import app_config, logger

oauth = OAuth()

# registers the Dex OIDC provider with some defined scopes
# Note: this pattern can be extended to other OIDC providers as well
# to use in other packages: oauth.dex.<method>,
# For available methods, please refer to StarletteOAuth2App and its mix-ins
oauth.register(
    name="dex",
    server_metadata_url=app_config.oidc_provider_wellknown_endpoint,
    client_id=app_config.oidc_client_id,
    client_secret=app_config.oidc_client_secret,
    client_kwargs={"scope": app_config.oidc_scopes},
)


async def verify_token(id_token: str = "") -> None:
    jwks = await oauth.dex.fetch_jwk_set()
    try:
        decoded_jwt = jwt.decode(s=id_token, key=jwks)
    except Exception as e:
        raise UnauthenticatedError from e
    metadata = await oauth.dex.load_server_metadata()
    if decoded_jwt["iss"] != metadata["issuer"]:
        raise UnauthenticatedError from None
    if decoded_jwt["aud"] != app_config.oidc_client_id:
        raise UnauthenticatedError from None
    exp = datetime.fromtimestamp(decoded_jwt["exp"], tz=timezone.utc)
    if exp < datetime.now(tz=timezone.utc):
        raise UnauthenticatedError from None
    return decoded_jwt


async def verify_session(request: Request) -> str:
    access_token = request.session.get("access_token")
    if access_token is None:
        raise UnauthenticatedError from None
    _ = await verify_token(id_token=access_token)
    # do extra checks with user from decoded claims
    return f"Bearer {access_token}"


# verifies a user from the access token used to access the protected resource
async def verify_user(request: Request) -> str:
    access_token = request.session.get("access_token")
    if access_token is None:
        raise UnauthenticatedError from None
    decoded_jwt = await verify_token(id_token=access_token)
    # do extra checks with user from decoded claims
    return decoded_jwt.get("email")


# uses RFC8693 token exchange to change for an upstream access token
# do not set the `audience:server:client_id:` claim
# id_token is used to conduct the exchange
# @param upstream_client_id is used to denote the target aud,
# this can be in form of an identified URM which is recognized by the IDP
async def impersonate_user(
    access_token: str = "",
    upstream_connector_id: str = "",
    upstream_client_id: str = "",
    scopes: Optional[List[str]] = None,
    *,
    add_aud_to_scopes: bool,
) -> str:
    if access_token is None:
        raise UnauthenticatedError from None
    _ = await verify_token(id_token=access_token)

    # format scopes
    for index, scope in enumerate(scopes):
        # escape for any spaces to prevent faulty scope
        scopes[index] = "".join(scope.split())

    # append formatted upstream aud claim to scopes (required for Dex OIDC)
    if add_aud_to_scopes:
        scopes.append(f"audience:server:client_id:{upstream_client_id}")

    # format scopes into expected input structure: "scope1 scope2 scope3"
    formatted_scopes = " ".join(scopes)

    try:
        upstream_token = await oauth.dex.fetch_access_token(
            connector_id=upstream_connector_id,
            grant_type="urn:ietf:params:oauth:grant-type:token-exchange",  # ; token-exchange grant type
            scope=formatted_scopes,
            requested_token_type="urn:ietf:params:oauth:token-type:access_token",  # noqa: S106; static param
            subject_token=access_token,
            subject_token_type="urn:ietf:params:oauth:token-type:access_token",  # noqa: S106; static param
            audience=upstream_client_id,  # general RFC-8693 spec compliant audience setting
        )
        return upstream_token.get("access_token")
    except OAuthError:
        logger.error(f"failed to impersonate user for {upstream_client_id}")
        raise UnauthenticatedError from None
    except Exception as e:
        logger.error(
            f"unexpected error in impersonate user for {upstream_client_id}, {e}"
        )
        raise UnauthenticatedError from e
