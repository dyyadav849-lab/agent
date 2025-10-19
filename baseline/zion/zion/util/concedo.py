from datetime import datetime, timedelta

import jwt
import pytz

from zion.config import global_config


def sign_concedo_token() -> str:
    headers = {
        "alg": "ES256",
        "ckid": global_config.concedo_public_key_id,
        "appid": global_config.concedo_app_id,
        "type": "JWT",
        "tokencat": "service",
    }

    jwt_claims = {
        "aud": global_config.helix_concedo_client_id,
        "concedo_id": "",
        "service_id": global_config.concedo_app_id,
        "exp": int(
            (
                datetime.now(pytz.timezone("Asia/Singapore")) + timedelta(hours=6)
            ).timestamp()
        ),
        "iss": global_config.concedo_client_id,
        "name": "",
        "sub": global_config.concedo_client_id,
        "token_type": "Bearer",
    }

    token = jwt.encode(
        jwt_claims,
        global_config.concedo_private_key.replace("\\n", "\n"),
        "ES256",
        headers,
    )

    if isinstance(token, bytes):
        token = bytes.decode(token)

    return token
