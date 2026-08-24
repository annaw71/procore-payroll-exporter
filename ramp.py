import requests

RAMP_BASE_URL = "https://api.ramp.com/developer/v1"


def get_ready_transactions(access_token):

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    transactions = []

    params = {
        "sync_status": "SYNC_READY",
        "page_size": 100,
    }

    url = f"{RAMP_BASE_URL}/transactions"

    while True:

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        result = response.json()

        transactions.extend(result.get("data", []))

        page = result.get("page", {})
        next_page = page.get("next")

        if not next_page:
            break

        params["start"] = next_page

    return transactions
