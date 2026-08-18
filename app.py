import json
import pandas as pd
import streamlit as st
import requests

from datetime import date, timedelta

from procore import (
    build_authorization_url,
    get_companies,
    get_all_projects,
    get_timecards,
)

from validators import validate_timecards

from sage_formatter import (
    format_timecards_for_sage,
    make_sage_clipboard_text,
    get_payroll_totals,
)

# ============================================================
# CONFIGURATION
# ============================================================

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

code = st.query_params.get("code")
oauth_error = st.query_params.get("error")

if oauth_error:
    st.error(f"Procore authorization failed: {oauth_error}")

elif code and "procore_access_token" not in st.session_state:
    st.info("Authorization code received from Procore.")

    token_response = requests.post(
        f"{login_url}/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        },
        timeout=30,
    )

    if token_response.ok:
        tokens = token_response.json()

        st.session_state["procore_access_token"] = tokens["access_token"]
        st.session_state["procore_refresh_token"] = tokens.get("refresh_token")

        st.success("Procore connnection established successfully!")

        # clear the one time OAuth code from the URL to prevent reusing it
        st.query_params.clear()
        st.rerun()
    else:
        st.error("Failed to exchange authorization code for access token.")
        st.code(token_response.text)

# ============================================================
# 1. PROCORE AUTHORIZATION
# ============================================================

st.subheader("1. Connect to Procore")

if "procore_access_token" in st.session_state:
    st.success("Connected to Procore.")

else:
    authorization_url = build_authorization_url(
        login_url=login_url,
        client_id=client_id,
        redirect_uri=redirect_uri,
    )

    st.link_button(
        "Authorize Procore",
        authorization_url,
    )

# ============================================================
# 2. PAY PERIOD
# ============================================================

st.divider()

st.subheader("2. Pay Period")


def get_previous_week():

    today = date.today()

    # Monday of the current week
    current_monday = today - timedelta(days=today.weekday())

    # Previous completed week
    previous_monday = current_monday - timedelta(days=7)
    previous_sunday = previous_monday + timedelta(days=6)

    return previous_monday, previous_sunday


def change_pay_period(days):
    st.session_state["pay_period_start"] += timedelta(days=days)
    st.session_state["pay_period_end"] += timedelta(days=days)
    st.session_state.pop("timecards", None)
    st.session_state.pop("payroll_df", None)


# Set the default pay period only once.
if "pay_period_start" not in st.session_state:
    previous_monday, previous_sunday = get_previous_week()
    st.session_state["pay_period_start"] = previous_monday
    st.session_state["pay_period_end"] = previous_sunday

# Navigation buttons
st.markdown(
    """
    <style>
    div.stButton > button {
        font-size: 1.25rem !important;
        font-weight: 400 !important;
        padding: 10px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

back_col, date_col, forward_col = st.columns([1, 5, 1])

with back_col:
    if st.button(
        "<",
        help="Previous week",
        use_container_width=True,
    ):
        change_pay_period(-7)
        st.rerun()


with date_col:
    start_date = st.session_state["pay_period_start"]
    end_date = st.session_state["pay_period_end"]

    st.markdown(
        f"""
        <div style="
            text-align: center;
            font-size: 1.25rem;
            font-weight: 400;
            padding-top: 0.35rem;
        ">
            {start_date.strftime("%m/%d/%Y")} - {end_date.strftime("%m/%d/%Y")}
        </div>
        """,
        unsafe_allow_html=True,
    )

with forward_col:
    if st.button(
        ">",
        help="Next week",
        use_container_width=True,
    ):
        change_pay_period(7)
        st.rerun()

# ============================================================
# 3. COMPANY
# ============================================================

if "procore_access_token" in st.session_state:
    st.divider()

    st.subheader("3. Choose Procore Company")

    try:
        companies = get_companies(
            api_url=api_url,
            access_token=st.session_state["procore_access_token"],
        )

        company_options = {company["name"]: company["id"] for company in companies}

        selected_company_name = company_options[0]()

        st.session_state["company_id"] = selected_company_name

    except Exception as exc:
        st.error("Could not load companies.")
        st.code(str(exc))

# ============================================================
# LOAD PROJECTS
# ============================================================

if (
    "procore_access_token" in st.session_state
    and "company_id" in st.session_state
    and "projects" not in st.session_state
):
    try:
        projects = get_all_projects(
            api_url=api_url,
            access_token=st.session_state["procore_access_token"],
            company_id=st.session_state["company_id"],
        )

        st.session_state["projects"] = projects

    except Exception as exc:
        st.error("Could not load Procore projects.")
        st.code(str(exc))

# ============================================================
# 4. PULL TIMESHEETS
# ============================================================

if (
    "procore_access_token" in st.session_state
    and "company_id" in st.session_state
    and "projects" in st.session_state
):
    st.divider()

    st.subheader("4. Procore Timesheets")

    if st.button("Pull Timesheets"):
        progress_bar = st.progress(0)

        try:
            (
                all_timecards,
                failed_projects,
            ) = get_timecards(
                api_url=api_url,
                access_token=st.session_state["procore_access_token"],
                company_id=st.session_state["company_id"],
                projects=st.session_state["projects"],
                start_date=start_date,
                end_date=end_date,
                progress_callback=(progress_bar.progress),
            )

            st.session_state["timecards"] = all_timecards

            for project_name in failed_projects:
                st.warning("Could not load timecards " f"for {project_name}.")

        except Exception as exc:
            st.error("Could not load timesheets.")
            st.code(str(exc))


# ============================================================
# VALIDATE TIMECARDS
# ============================================================

if "timecards" in st.session_state:
    all_timecards = st.session_state["timecards"]

    errors = validate_timecards(all_timecards)

    # --------------------------------------------------------
    # BLOCK EXPORT IF ERRORS EXIST
    # --------------------------------------------------------

    if errors:
        st.error("Payroll Export Blocked - " "Errors Found")

        st.write(
            f"**{len(errors)} error" f"{'s' if len(errors) != 1 else ''} " f"found.**"
        )

        error_df = pd.DataFrame(
            {
                "Problem": errors,
            }
        )

        st.dataframe(
            error_df,
            use_container_width=True,
            hide_index=True,
        )

        if st.button("Refresh From Procore"):
            st.session_state.pop("timecards", None)
            st.session_state.pop("payroll_df", None)
            st.rerun()

    else:
        # ----------------------------------------------------
        # FORMAT FOR SAGE
        # ----------------------------------------------------

        payroll_df = format_timecards_for_sage(all_timecards)

        sage_copy_text = make_sage_clipboard_text(payroll_df)

        totals = get_payroll_totals(payroll_df)

        st.session_state["payroll_df"] = payroll_df

        # ----------------------------------------------------
        # DISPLAY TOTALS
        # ----------------------------------------------------

        st.success(f"{totals['row_count']} " "approved timecards ready.")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Employees",
            totals["employee_count"],
        )

        col2.metric(
            "Jobs",
            totals["job_count"],
        )

        col3.metric(
            "Total Hours",
            f"{totals['total_hours']:,.1f}",
        )

        col4.metric(
            "Overtime Hours",
            f"{totals['overtime_hours']:,.1f}",
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Sick Hours",
            f"{totals['sick_hours']:,.1f}",
        )

        col2.metric(
            "Vacation Hours",
            f"{totals['vacation_hours']:,.1f}",
        )

        col3.metric(
            "Holiday Hours",
            f"{totals['holiday_hours']:,.1f}",
        )

        # ----------------------------------------------------
        # COPY TO SAGE
        # ----------------------------------------------------

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
                const button =
                    document.getElementById(
                        "copy-sage-button"
                    );

                const status =
                    document.getElementById(
                        "copy-sage-status"
                    );

                button.addEventListener(
                    "click",
                    async () => {{
                        const text =
                            {sage_copy_json};

                        try {{
                            await navigator
                                .clipboard
                                .writeText(text);

                            button.innerText =
                                "✅ Copied "
                                + "{row_count}"
                                + " rows to clipboard";

                            status.innerText = "";

                        }} catch (error) {{
                            status.innerText =
                                "Unable to copy "
                                + "to clipboard.";

                            console.error(error);
                        }}
                    }}
                );
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

        # ----------------------------------------------------
        # CSV DOWNLOAD
        # ----------------------------------------------------

        csv = payroll_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label=("Optional: Download " "Payroll Preview CSV"),
            data=csv,
            file_name=(f"procore_payroll_" f"{start_date}_to_" f"{end_date}.csv"),
            mime="text/csv",
        )
