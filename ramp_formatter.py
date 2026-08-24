import pandas as pd


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

        rows.append(
            {
                "Transaction ID": transaction.get("id"),
                "Date": transaction.get("accounting_date"),
                "Merchant": transaction.get("merchant_name"),
                "Employee": employee_name,
                "Department": card_holder.get("department_name"),
                "Amount": transaction.get("amount"),
                "Currency": transaction.get("currency_code"),
                "Memo": transaction.get("memo"),
                "Sync Status": transaction.get("sync_status"),
            }
        )

    return pd.DataFrame(rows)
