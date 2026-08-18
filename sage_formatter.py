from datetime import datetime

import pandas as pd

SAGE_COLUMNS = [
    "Date",
    "Employee",
    "Job",
    "Phase",
    "Equipment",
    "Cost Code",
    "Total Hours",
    "Overtime Hours",
    "Premium Hours",
    "Sick Hours",
    "Vacation Hours",
    "Holiday Hours",
    "Notes",
]


def format_timecards_for_sage(timecards):
    payroll_rows = []

    for timecard in timecards:
        date = datetime.strptime(
            timecard.get("date"),
            "%Y-%m-%d",
        ).strftime("%m/%d/%Y")

        employee = (timecard.get("party") or {}).get("employee_id")

        job = timecard.get("project_name")

        cost_code = (timecard.get("cost_code") or {}).get("code") or ""

        time_type = (timecard.get("timecard_time_type") or {}).get(
            "abbreviated_time_type"
        ) or ""

        hours = float(timecard.get("hours") or 0)

        notes = timecard.get("description")

        # Allocate hours to the Sage-specific columns.
        overtime_hours = hours if time_type == "OVE" else None

        sick_hours = hours if time_type == "SICK" else None

        vacation_hours = hours if time_type == "VAC" else None

        holiday_hours = hours if time_type == "HOL" else None

        # Shop / Admin doesn't need Job or Cost Code
        # when pasted into Sage.
        if job == "Shop / Admin Time":
            job = None
            cost_code = None

        payroll_rows.append(
            {
                "Date": date,
                "Employee": employee,
                "Job": job,
                "Phase": None,
                "Equipment": None,
                "Cost Code": cost_code,
                "Total Hours": hours,
                "Overtime Hours": overtime_hours,
                "Premium Hours": None,
                "Sick Hours": sick_hours,
                "Vacation Hours": vacation_hours,
                "Holiday Hours": holiday_hours,
                "Notes": notes,
            }
        )

    payroll_df = pd.DataFrame(
        payroll_rows,
        columns=SAGE_COLUMNS,
    )

    payroll_df = payroll_df.sort_values(
        by="Job",
        ascending=True,
        na_position="last",
    ).reset_index(drop=True)

    return payroll_df


def make_sage_clipboard_text(payroll_df):
    """
    Tab-separated data with no column headers,
    ready to paste directly into Sage.
    """
    return payroll_df.fillna("").to_csv(
        sep="\t",
        index=False,
        header=False,
    )


def get_payroll_totals(payroll_df):
    return {
        "row_count": len(payroll_df),
        "employee_count": payroll_df["Employee"].nunique(),
        "job_count": payroll_df["Job"].nunique(),
        "total_hours": payroll_df["Total Hours"].sum(),
        "overtime_hours": payroll_df["Overtime Hours"].sum(),
        "sick_hours": payroll_df["Sick Hours"].sum(),
        "vacation_hours": payroll_df["Vacation Hours"].sum(),
        "holiday_hours": payroll_df["Holiday Hours"].sum(),
    }
