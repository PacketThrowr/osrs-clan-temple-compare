import requests
import json

# TempleOSRS API URL for group ID 1265
API_URL = "https://templeosrs.com/api/groupmembers.php?id=1265"

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

