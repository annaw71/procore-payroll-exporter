import requests
from urllib.parse import urlencode
import streamlit as st


def build_authorization_url(login_url, client_id, redirect_uri):
    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    }

    return f"{login_url}/oauth/authorize?" + urlencode(auth_params)


def exchange_authorization_code(
    login_url,
    client_id,
    client_secret,
    authorization_code,
    redirect_uri,
):
    token_url = f"{login_url}/oauth/token"

    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": authorization_code,
        "redirect_uri": redirect_uri,
    }

    response = requests.post(token_url, json=payload)

    if not response.ok:
        raise RuntimeError(f"Procore connection failed.\n{response.text}")

    return response.json()


def get_companies(api_url, access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    companies_url = f"{api_url}/rest/v1.0/companies"

    response = requests.get(
        companies_url,
        headers=headers,
    )

    if not response.ok:
        raise RuntimeError(f"Could not load Procore companies.\n{response.text}")

    return response.json()


def get_all_projects(
    api_url,
    access_token,
    company_id,
):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Procore-Company-Id": str(company_id),
    }

    projects_url = f"{api_url}/rest/v1.1/projects"

    all_projects = []

    page = 1
    per_page = 100

    while True:
        params = {
            "company_id": company_id,
            "per_page": per_page,
            "page": page,
            "filters[by_status]": "active",
        }

        response = requests.get(
            projects_url,
            headers=headers,
            params=params,
        )

        response.raise_for_status()

        page_projects = response.json()
        all_projects.extend(page_projects)

        total = int(response.headers.get("Total", 0))

        if len(all_projects) >= total:
            break

        page += 1

    return all_projects


def get_timecards(
    api_url,
    access_token,
    company_id,
    projects,
    start_date,
    end_date,
    progress_callback=None,
):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Procore-Company-Id": str(company_id),
    }

    all_timecards = []
    failed_projects = []

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

            response = requests.get(
                timecards_url,
                headers=headers,
                params=params,
            )

            if not response.ok:
                failed_projects.append(project_name)
                break

            page_timecards = response.json()

            project_timecards.extend(page_timecards)

            total = int(response.headers.get("Total", 0))

            if len(project_timecards) >= total:
                break

            page += 1

        # Procore's timecard response doesn't contain the project
        # name we need for Sage, so attach it here.
        for timecard in project_timecards:
            timecard["project_id"] = project_id
            timecard["project_name"] = project_name

            all_timecards.append(timecard)

        if progress_callback and projects:
            progress_callback((index + 1) / len(projects))

    return all_timecards, failed_projects
