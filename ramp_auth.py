import base64
import requests

TOKEN_URL = "https://api.ramp.com/developer/v1/token"


def get_ramp_access_token(client_id, client_secret):

    credentials = f"{client_id}:{client_secret}"

    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "client_credentials",
        "scope": "transaction:read accounting:read",
    }

    response = requests.post(
        TOKEN_URL,
        headers=headers,
        data=data,
        timeout=30,
    )

    response.raise_for_status()

    token_data = response.json()

    return token_data["access_token"]


def get_accounting_connection(access_token):

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    response = requests.get(
        "https://api.ramp.com/developer/v1/accounting/connection",
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    if not response.ok:
        raise Exception(
            f"Ramp accounting error {response.status_code}: {response.text}"
        )

    return response.json()
