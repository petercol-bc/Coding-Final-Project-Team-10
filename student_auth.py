# student_auth.py
# Helper functions for making requests to the Game Server.
#
# Every request carries your team's access code, which the Game Server uses to
# recognize your team. The code lives in client_config.json, next to the URL of
# the Game Server:
#
#     {
#         "server_url": "http://...",
#         "team_code": "maple-otter-harbor-42"
#     }
#
# Your instructor gives each team its own code. Keep it within your team: anyone
# with your code can play as your team.

import json
import requests

CONFIG_FILE_PATH = "client_config.json"
PLACEHOLDER_CODE = "PASTE-YOUR-TEAM-CODE-HERE"

_cached_team_code = None


def _load_team_code():
    global _cached_team_code
    if _cached_team_code is None:
        try:
            with open(CONFIG_FILE_PATH, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            raise RuntimeError(
                f"Could not find '{CONFIG_FILE_PATH}'. Make sure it's in the same folder "
                "as your code -- see the assignment instructions."
            )
        except json.JSONDecodeError:
            raise RuntimeError(
                f"'{CONFIG_FILE_PATH}' is not valid JSON. Check for a missing quote or comma."
            )
        team_code = str(config.get("team_code", "")).strip()
        if not team_code or team_code == PLACEHOLDER_CODE:
            raise RuntimeError(
                f"No team code found in '{CONFIG_FILE_PATH}'. Put the code your instructor "
                'gave your team in the "team_code" entry.'
            )
        _cached_team_code = team_code
    return _cached_team_code


def _auth_headers():
    return {"Authorization": f"Bearer {_load_team_code()}"}


def get(url, params=None):
    """
    Makes a GET request to the Game Server, with your team code attached.
    Behaves like requests.get().
    """
    headers = _auth_headers()
    return requests.get(url, params=params, headers=headers)


def post(url, data=None):
    """
    Makes a POST request to the Game Server, with your team code attached.
    Sends `data` as JSON. Behaves like requests.post().
    """
    headers = _auth_headers()
    return requests.post(url, json=data, headers=headers)
