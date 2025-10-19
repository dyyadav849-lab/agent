import requests

from zion.config import global_config
from zion.util.concedo import sign_concedo_token

SERVICE_ACCOUNT_NAME = "svc.apex.tibot"


# first is concedo token
# second is helix token
def get_helix_token() -> tuple[str, str]:
    """Gets concedo token and helix token.
    performs exchange token using the concedo token to get a jwt token for helix.
    """
    try:
        concedo_token = sign_concedo_token()

        res = requests.post(
            url=f"{global_config.helix_base_url}/api/exchangeToken",
            headers={"Authorization": f"Bearer {concedo_token}"},
            timeout=5,
        )
        res_body_text = res.json()

        return concedo_token, res_body_text["token"]
    except (requests.exceptions.RequestException, Exception) as e:
        err_msg = f"Unable to get helix exchange token with error: {e!s}"
        raise ConnectionError(err_msg) from e
