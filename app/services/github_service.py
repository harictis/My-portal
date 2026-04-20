import requests
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_ORG = os.getenv("GITHUB_ORG")
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"


def add_user_to_team(username: str, team_slug: str):
    
    if TEST_MODE:
        print(f"[MOCK MODE] Adding {username} to {team_slug}")

        return 200, {
            "message": "Mock success - user added to team",
            "user": username,
            "team": team_slug
        }

    # REAL GITHUB CALL
    url = f"https://api.github.com/orgs/{GITHUB_ORG}/teams/{team_slug}/memberships/{username}"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.put(url, headers=headers)

    return response.status_code, response.json()