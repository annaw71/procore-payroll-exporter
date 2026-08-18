from datetime import datetime

VALID_TIME_TYPES = {
    "REG",
    "OVE",
    "SICK",
    "VAC",
    "HOL",
}


def validate_timecards(timecards):
    errors = []

    employee_hours = {}
    seen_timecard_ids = set()

    for timecard in timecards:
        timecard_id = timecard.get("id")

        date = datetime.strptime(
            timecard.get("date"),
            "%Y-%m-%d",
        ).strftime("%m/%d/%Y")

        employee = (timecard.get("party") or {}).get("employee_id")

        employee_name = (timecard.get("party") or {}).get("name") or ""

        job = timecard.get("project_name")

        cost_code = (timecard.get("cost_code") or {}).get("code") or ""

        time_type = (timecard.get("timecard_time_type") or {}).get(
            "abbreviated_time_type"
        ) or ""

        hours = float(timecard.get("hours") or 0)

        approval_status = timecard.get("approval_status")

        # -------------------------
        # BLOCKING ERRORS
        # -------------------------

        if not employee:
            errors.append(f"{employee_name}: Employee ID is missing.")

        if not cost_code and job != "Shop / Admin Time":
            errors.append(
                f"{employee_name}: Missing cost code " f"on job {job} on {date}."
            )

        if time_type not in VALID_TIME_TYPES:
            errors.append(
                f"{employee_name}: Invalid time type " f"'{time_type}' on {date}."
            )

        if hours <= 0 or hours > 24:
            errors.append(f"{employee_name}: Timecard has " f"'{hours}' on {date}.")

        if approval_status != "approved":
            errors.append(f"{employee_name}: Timecard is not " f"approved on {date}.")

        if not job:
            errors.append(f"{employee_name}: Project is missing " f"on {date}.")

        elif timecard_id in seen_timecard_ids:
            errors.append(
                f"{employee_name}: Duplicate timecard " f"ID {timecard_id} on {date}."
            )

        else:
            seen_timecard_ids.add(timecard_id)

        # -------------------------
        # EMPLOYEE TOTALS
        # -------------------------

        key = (
            employee,
            employee_name,
        )

        employee_hours[key] = employee_hours.get(key, 0) + hours

    return errors
