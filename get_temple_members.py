import requests
import json
import os

# Read API URL from environment variable
API_URL = os.environ.get("TEMPLE_API_URL")

if not API_URL:
    raise RuntimeError("TEMPLE_API_URL is not set in the environment.")

def fetch_members():
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        members = response.json()
        return members
    except requests.RequestException as e:
        print(f"Failed to fetch data: {e}")
        return []

def save_to_file(members, filename="temple.json"):
    with open(filename, "w") as f:
        json.dump(members, f, indent=2)
    print(f"Saved {len(members)} members to {filename}")

if __name__ == "__main__":
    clan_members = fetch_members()
    if clan_members:
        save_to_file(clan_members)

