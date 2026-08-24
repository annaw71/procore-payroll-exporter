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
                    "Transaction ID": transaction.get("id"),
                    "Date": transaction.get("accounting_date"),
                    "Merchant": transaction.get("merchant_name"),
                    "Merchant Description": transaction.get("merchant_descriptor"),
                    "Employee": employee_name,
                    "Department": card_holder.get("department_name"),
                    "Location": card_holder.get("location_name"),
                    "Amount": transaction.get("amount"),
                    "Memo": transaction.get("memo"),
                    "GL Account": gl_account["code"],
                    "GL Account Name": gl_account["name"],
                    "State": transaction.get("state"),
                    "Sync Status": transaction.get("sync_status"),
                    "Approved": transaction.get("all_requirements_met_and_approved"),
                }
            )

    return pd.DataFrame(rows)
