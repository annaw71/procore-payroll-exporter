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
            errors.append(f"{employee_name}: Missing cost code on job {job} on {date}.")

        if time_type not in VALID_TIME_TYPES:
            errors.append(
                f"{employee_name}: Invalid time type '{time_type}' on {date}."
            )

        if hours <= 0 or hours > 24:
            errors.append(f"{employee_name}: Timecard has '{hours}' on {date}.")

        if approval_status == "completed":
            return ["Timecards have already been completed for this period."]
        elif approval_status != "approved":
            errors.append(f"{employee_name}: Timecard is not approved on {date}.")

        if not job:
            errors.append(f"{employee_name}: Project is missing on {date}.")

        elif timecard_id in seen_timecard_ids:
            errors.append(
                f"{employee_name}: Duplicate timecard ID {timecard_id} on {date}."
            )

        else:
            seen_timecard_ids.add(timecard_id)

    return errors
