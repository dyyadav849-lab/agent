import json
from pathlib import Path

from zion.config import global_config

GOOGLE_CREDENTIALS_FOLDER = f"{Path.cwd()}/credentials"
GOOGLE_CREDENTIALS_FILE_LOCATION = (
    f"{GOOGLE_CREDENTIALS_FOLDER}/google_doc_credentials.json"
)


def init_google_credentials() -> None:
    """Initializes google credentials for gdoc into a file called `google_doc_credentials.json`
    The folder and file location are ignored in gitignore
    """
    path_google_credentials_folder = Path(GOOGLE_CREDENTIALS_FOLDER)
    path_google_credentials_file = Path(GOOGLE_CREDENTIALS_FILE_LOCATION)
    if not Path.is_dir(path_google_credentials_folder):
        Path.mkdir(path_google_credentials_folder, parents=True, exist_ok=True)

    # returns if credential file exist to prevent error
    if Path.exists(path_google_credentials_file):
        return

    # the json data to ensure creating correct credentials
    json_data = {
        "type": "service_account",
        "project_id": global_config.google_project_id,
        "private_key_id": global_config.google_private_key_id,
        "private_key": global_config.google_private_key.replace("\\n", "\n"),
        "client_email": global_config.google_client_email,
        "client_id": global_config.google_client_id,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": global_config.google_client_x509_cert_url,
        "universe_domain": "googleapis.com",
    }
    with Path(path_google_credentials_file).open("w") as f:
        f.write(json.dumps(json_data))
        f.close()
