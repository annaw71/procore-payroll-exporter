import pandas as pd


def get_accounting_field(line_item, field_name):
    selections = line_item.get("accounting_field_selections", [])

    for selection in selections:
        category_info = selection.get("category_info") or {}

        if category_info.get("name") == field_name:
            return {
                "name": selection.get("name"),
                "code": selection.get("external_code"),
            }

    return {
        "name": None,
        "code": None,
    }


def format_ramp_transactions(transactions):

    rows = []

    for transaction in transactions:

        card_holder = transaction.get("card_holder") or {}

        employee_name = " ".join(
            filter(
                None,
                [
                    card_holder.get("first_name"),
                    card_holder.get("last_name"),
                ],
            )
        )

        line_items = transaction.get("line_items") or []

        if not line_items:
            line_items = [{}]

        for line_item in line_items:

            gl_account = get_accounting_field(
                line_item,
                "Sage GL Account",
            )

            rows.append(
                {
                    "Credit Card": "1 - Ramp",
                    "Include": "Include",
                    "Transaction #": transaction.get("accounting_date"),
                    "Description": employee_name,
                    "Payee": transaction.get("merchant_name"),
                    "Charge Amount": transaction.get("amount"),
                    "Credit Amount": "",
                    "Posted Date": "dont know what to put",
                    "Notes": transaction.get("memo"),
                    "Account": gl_account["code"] + " - " + gl_account["name"],
                    "Subaccount": "don't know what to put",
                    "Job": "dont know - blank?",
                    "Phase": "",
                    "Job Cost Code": "don't know - blank?",
                    "Job Cost Type": "don't know - said something about putting manually",
                    "Equipment": "same as prev",
                    "Equipment Cost Code": "same as prev",
                    "Equipment Cost Type": "same",
                }
            )

    return pd.DataFrame(rows)
