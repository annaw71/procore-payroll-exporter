import streamlit as st
import requests
import pandas as pd
import json
from datetime import date, timedelta, datetime
from urllib.parse import urlencode

st.title("Procore Payroll Exporter")

st.write(
    "Pull Procore timesheet data for a pay period "
    "and format it for Sage 100 Contractor."
)

client_id = st.secrets["PROCORE_CLIENT_ID"]
client_secret = st.secrets["PROCORE_CLIENT_SECRET"]
login_url = st.secrets["PROCORE_LOGIN_URL"]
api_url = st.secrets["PROCORE_API_URL"]
redirect_uri = st.secrets["PROCORE_REDIRECT_URI"]


# -------------------------
# PROCORE AUTHORIZATION
# -------------------------

auth_params = {
    "response_type": "code",
    "client_id": client_id,
    "redirect_uri": redirect_uri,
}

authorization_url = f"{login_url}/oauth/authorize?" + urlencode(auth_params)

st.subheader("1. Connect to Procore")

st.link_button("Authorize Procore", authorization_url)

authorization_code = st.text_input(
    "Paste Procore authorization code here", type="password"
)


if st.button("Connect to Procore"):

    token_url = f"{login_url}/oauth/token"

    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": authorization_code,
        "redirect_uri": redirect_uri,
    }

    response = requests.post(token_url, json=payload)

    if response.ok:

        token_data = response.json()

        st.session_state["access_token"] = token_data["access_token"]

        st.session_state["refresh_token"] = token_data.get("refresh_token")

        st.success("Connected to Procore!")

    else:

        st.error("Procore connection failed.")

        st.code(response.text)


# ============================================================
# 2. PAY PERIOD
# ============================================================

st.divider()

st.subheader("2. Pay Period")


def get_previous_week():
    """Return Monday-Sunday for the previous completed week."""

    today = date.today()

    # Monday of the current week
    current_monday = today - timedelta(days=today.weekday())

    # Previous completed week
    previous_monday = current_monday - timedelta(days=7)

    previous_sunday = previous_monday + timedelta(days=6)

    return previous_monday, previous_sunday


# Set the default pay period only once.
if "pay_period_start" not in st.session_state:
    (
        st.session_state["pay_period_start"],
        st.session_state["pay_period_end"],
    ) = get_previous_week()

# Navigation buttons
back_col, date_col, forward_col = st.columns([1, 5, 1])

with back_col:
    if st.button(
        "⬅️",
        help="Previous week",
        use_container_width=True,
    ):
        st.session_state["pay_period_start"] -= timedelta(days=7)

        st.session_state["pay_period_end"] -= timedelta(days=7)

        st.rerun()

with date_col:
    start_date = st.session_state["pay_period_start"]

    end_date = st.session_state["pay_period_end"]

    st.markdown(
        f"""
        <div style="
            text-align: center;
            font-size: 1.25rem;
            font-weight: 600;
            padding-top: 0.35rem;
        ">
            {start_date.strftime("%A, %B %d, %Y")}
            <br>
            through
            <br>
            {end_date.strftime("%A, %B %d, %Y")}
        </div>
        """,
        unsafe_allow_html=True,
    )

with forward_col:
    if st.button(
        "➡️",
        help="Next week",
        use_container_width=True,
    ):
        st.session_state["pay_period_start"] += timedelta(days=7)

        st.session_state["pay_period_end"] += timedelta(days=7)

        st.rerun()

# -------------------------
# LOAD PROCORE COMPANIES
# -------------------------

if "access_token" in st.session_state:

    st.divider()
    st.subheader("3. Choose Procore Company")

    headers = {"Authorization": (f"Bearer {st.session_state['access_token']}")}

    companies_url = f"{api_url}/rest/v1.0/companies"

    response = requests.get(companies_url, headers=headers)

    if response.ok:

        companies = response.json()

        company_options = {company["name"]: company["id"] for company in companies}

        selected_company_name = st.selectbox("Company", company_options.keys())

        selected_company_id = company_options[selected_company_name]

        st.session_state["company_id"] = selected_company_id

        st.success(f"Using company ID: {selected_company_id}")

    else:

        st.error("Could not load companies.")
        st.code(response.text)

# -------------------------
# LOAD ALL PROCORE PROJECTS
# -------------------------

if "access_token" in st.session_state and "company_id" in st.session_state:

    headers = {
        "Authorization": f"Bearer {st.session_state['access_token']}",
        "Procore-Company-Id": str(st.session_state["company_id"]),
    }

    projects_url = f"{api_url}/rest/v1.1/projects"

    all_projects = []

    page = 1
    per_page = 100

    while True:
        params = {
            "company_id": st.session_state["company_id"],
            "per_page": per_page,
            "page": page,
        }

        response = requests.get(projects_url, headers=headers, params=params)

        response.raise_for_status()

        page_projects = response.json()

        all_projects.extend(page_projects)

        total = int(response.headers.get("Total", 0))

        if len(all_projects) >= total:
            break

        page += 1

    st.session_state["projects"] = all_projects

# -------------------------
# LOAD TIMECARDS
# FROM ALL PROJECTS
# -------------------------

if (
    "access_token" in st.session_state
    and "company_id" in st.session_state
    and "projects" in st.session_state
):

    st.divider()
    st.subheader("4. Procore Timesheets")

    if st.button("Pull Timesheets"):

        headers = {
            "Authorization": (f"Bearer {st.session_state['access_token']}"),
            "Procore-Company-Id": str(st.session_state["company_id"]),
        }

        all_timecards = []

        progress_bar = st.progress(0)

        projects = st.session_state["projects"]

        for index, project in enumerate(projects):

            project_id = project["id"]
            project_name = project["name"]

            timecards_url = (
                f"{api_url}/rest/v1.0/projects/" f"{project_id}/timecard_entries"
            )

            project_timecards = []

            page = 1
            per_page = 100

            while True:

                params = {
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "per_page": per_page,
                    "page": page,
                }

                response = requests.get(timecards_url, headers=headers, params=params)

                if not response.ok:
                    st.warning(f"Could not load timecards for {project_name}.")
                    break

                page_timecards = response.json()

                project_timecards.extend(page_timecards)

                total = int(response.headers.get("Total", 0))

                if len(project_timecards) >= total:
                    break

                page += 1

            # Add project info to every timecard
            for timecard in project_timecards:

                timecard["project_id"] = project_id
                timecard["project_name"] = project_name

                all_timecards.append(timecard)

            progress_bar.progress((index + 1) / len(projects))

        st.session_state["timecards"] = all_timecards

# -------------------------
# FORMAT TIMECARDS
# -------------------------

if "timecards" in st.session_state:

    all_timecards = st.session_state["timecards"]

    errors = []
    warnings = []
    payroll_rows = []
    employee_hours = {}
    valid_time_types = {"REG", "OVE", "SICK", "VAC", "HOL"}
    seen_timecard_ids = set()

    for timecard in all_timecards:

        # input values
        timecard_id = timecard.get("id")
        date = datetime.strptime(timecard.get("date"), "%Y-%m-%d").strftime("%m/%d/%Y")
        employee = (timecard.get("party") or {}).get("employee_id")
        employee_name = (timecard.get("party") or {}).get("name") or ""

        job = timecard.get("project_name")
        cost_code = (timecard.get("cost_code") or {}).get("code") or ""

        time_type = (timecard.get("timecard_time_type") or {}).get(
            "abbreviated_time_type"
        ) or ""
        hours = float(timecard.get("hours") or 0)

        notes = timecard.get("description")
        approval_status = timecard.get("approval_status")

        # -------------------------------
        # BLOCKING ERRORS
        # -------------------------------

        if not employee:
            errors.append(f"{employee_name}: Employee ID is missing.")

        if not cost_code and job != "Shop / Admin Time":
            errors.append(f"{employee_name}: Missing cost code on job {job} on {date}.")

        if time_type not in valid_time_types:
            errors.append(
                f"{employee_name}: Invalid time type '{time_type}' on {date}."
            )

        if hours <= 0 or hours > 24:
            errors.append(f"{employee_name}: Timecard has '{hours}' on {date}.")

        if approval_status != "approved":
            errors.append(f"{employee_name}: Timecard is not approved on {date}.")

        if not job:
            errors.append(f"{employee_name}: Project is missing on {date}.")

        elif timecard_id in seen_timecard_ids:
            errors.append(
                f"{employee_name}: Duplicate timecard ID {timecard_id} on {date}."
            )

        else:
            seen_timecard_ids.add(timecard_id)

        # -------------------------------
        # ACCUMULATE HOURS BY EMPLOYEE
        # -------------------------------

        key = (employee, employee_name)
        employee_hours[key] = employee_hours.get(key, 0) + hours

        # FORMAT PAYROLL ROW
        overtime_hours = hours if time_type == "OVE" else None
        sick_hours = hours if time_type == "SICK" else None
        vacation_hours = hours if time_type == "VAC" else None
        holiday_hours = hours if time_type == "HOL" else None

        # shop / admin doesn't need job or cost code in Sage
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

    # -------------------------------
    # AGGREGATE WARNINGS AND ERRORS
    # -------------------------------

    for (employee, employee_name), hours in employee_hours.items():
        warnings.append(
            f"{employee_name}: {hours:,.1f} total hours in this pay period."
        )

    if errors:

        st.error("Payroll Export Blocked - Errors Found")

        st.write(f"**{len(errors)} error" f"{'s' if len(errors) != 1 else ''} found.**")

        error_df = pd.DataFrame(
            {"Problem": errors},
        )

        st.dataframe(error_df, use_container_width=True, hide_index=True)

        if warnings:
            st.warning("Payroll Warnings")

            warning_df = pd.DataFrame(
                {"Warning": warnings},
            )

            st.dataframe(warning_df, use_container_width=True, hide_index=True)

        if st.button("Refresh From Procore"):
            st.session_state.pop("timecards", None)
            st.session_state.pop("payroll_df", None)

            st.rerun()

    # ------------------------------
    # NO ERRORS - CREATE SAGE OUTPUT
    # -----------------------------

    else:

        # show warnings but allow export
        if warnings:
            st.warning("Payroll Warnings")

            warning_df = pd.DataFrame(
                {"Warning": warnings},
            )

            st.dataframe(warning_df, use_container_width=True, hide_index=True)

        # BUILD DATA FRAME
        payroll_df = pd.DataFrame(
            payroll_rows,
            columns=[
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
            ],
        )

        payroll_df = payroll_df.sort_values(
            by="Job", ascending=True, na_position="last"
        ).reset_index(drop=True)

        sage_copy_text = payroll_df.fillna("").to_csv(
            sep="\t", index=False, header=False
        )

        # ------------------------------
        # DISPLAY TABLE TOTALS
        # ------------------------------

        total_hours = payroll_df["Total Hours"].sum()
        overtime_hours = payroll_df["Overtime Hours"].sum()
        sick_hours = payroll_df["Sick Hours"].sum()
        vacation_hours = payroll_df["Vacation Hours"].sum()
        holiday_hours = payroll_df["Holiday Hours"].sum()
        employee_count = payroll_df["Employee"].nunique()
        job_count = payroll_df["Job"].nunique()

        st.success(f"{len(payroll_df)} approved timecards ready.")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Employees", employee_count)
        col2.metric("Jobs", job_count)
        col3.metric("Total Hours", f"{total_hours:,.1f}")
        col4.metric("Overtime Hours", f"{overtime_hours:,.1f}")

        col1, col2, col3 = st.columns(3)

        col1.metric("Sick Hours", f"{sick_hours:,.1f}")
        col2.metric("Vacation Hours", f"{vacation_hours:,.1f}")
        col3.metric("Holiday Hours", f"{holiday_hours:,.1f}")

        st.session_state["payroll_df"] = payroll_df

        # ------------------------------
        # COPY TO SAGE
        # ------------------------------

        sage_copy_json = json.dumps(sage_copy_text)
        row_count = len(payroll_df)

        st.html(
            f"""
            <button
                id="copy-sage-button"
                style="
                    padding: 0.5rem 0.9rem;
                    font-size: 1rem;
                    cursor: pointer;
                    border-radius: 0.5rem;
                    border: 1px solid #ccc;"
            >
                Copy Table for Sage
            </button>

            <span
                id="copy-sage-status"
                style="margin-left: 10px;"
            ></span>

            <script>
                const button = document.getElementById("copy-sage-button");
                const status = document.getElementById("copy-sage-status");

                button.addEventListener("click", async () => {{
                    const text = {sage_copy_json};

                    try {{
                        await navigator.clipboard.writeText(text);

                        button.innerText = "✅ Copied {row_count} rows to clipboard";
                        status.innerText = "";
                    }} catch (error) {{
                        status.innerText = "Unable to copy to clipboard.";
                        console.error(error);
                    }}
                }});
            </script>
            """,
            unsafe_allow_javascript=True,
        )

        st.markdown("""
        ### After copying:

        1. Open **Sage 100 Contractor**.
        2. Open **5-6-2**.
        3. Click the first cell in the entry grid.
        4. Paste using **Ctrl+V**.
        5. Review totals before saving.
        """)

        # ------------------------------
        # OPTIONAL CSV DOWNLOAD
        # ------------------------------

        csv = payroll_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Optional: Download Payroll Preview CSV",
            data=csv,
            file_name=(f"procore_payroll_" f"{start_date}_to_{end_date}.csv"),
            mime="text/csv",
        )
