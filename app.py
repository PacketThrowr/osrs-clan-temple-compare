from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import json
import os
import subprocess
import sys
from pathlib import Path
import logging
from datetime import datetime

# -------------------
# Logging
# -------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clan-webhook")

# -------------------
# Config
# -------------------
BASE_DIR = Path(__file__).resolve().parent
TEMPLE_FILE = BASE_DIR / "temple.json"
TEMPLE_SCRIPT = BASE_DIR / "get_temple_members.py"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# -------------------
# Rank progression config
# -------------------
RANK_ORDER = ["Squire", "Striker", "Inquisitor", "Expert", "Knight"]
RANK_INDEX = {rank: i for i, rank in enumerate(RANK_ORDER)}

# -------------------
# Pydantic Models
# -------------------
class ClanMember(BaseModel):
    rsn: str
    rank: str
    joinedDate: str

class ClanPayload(BaseModel):
    clanName: str
    clanMemberMaps: List[ClanMember]

class PromotionCandidate(BaseModel):
    rsn: str
    currentRank: str
    expectedRank: str
    joinedDate: str
    monthsInClan: int

class ComparisonResult(BaseModel):
    clanName: str
    clanNotInTemple: List[str]
    templeNotInClan: List[str]
    needsPromotion: List[PromotionCandidate]

# -------------------
# FastAPI Instance
# -------------------
app = FastAPI(title="Clan / Temple Comparison Webhook")


def normalize_name(name: str) -> str:
    # Lowercase and strip outer whitespace
    s = name.strip().lower()
    # Treat underscores and hyphens as spaces
    s = s.replace("_", " ")
    s = s.replace("-", " ")
    # Collapse multiple spaces to a single space
    s = " ".join(s.split())
    return s

# -------------------
# Refresh Temple Members
# -------------------
def refresh_temple_members() -> None:
    try:
        result = subprocess.run(
            [sys.executable, str(TEMPLE_SCRIPT)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info(result.stdout)
    except Exception as e:
        logger.exception("Temple update failed")
        raise HTTPException(status_code=500, detail=str(e))


def load_temple_list() -> List[str]:
    with open(TEMPLE_FILE, "r") as f:
        return json.load(f)

# -------------------
# Rank Promotion Logic
# -------------------
def months_in_clan(joined_date_str: str) -> int:
    joined_date = datetime.strptime(joined_date_str, "%d-%b-%Y")
    today = datetime.today()
    return (today.year - joined_date.year) * 12 + (today.month - joined_date.month)


def get_expected_rank_from_months(months: int) -> str:
    if months < 3: return "Squire"
    if months < 6: return "Striker"
    if months < 9: return "Inquisitor"
    if months < 12: return "Expert"
    return "Knight"


def calculate_promotion_candidates(members: List[ClanMember]) -> List[PromotionCandidate]:
    candidates = []

    for m in members:
        if m.rank not in RANK_INDEX:
            continue

        months = months_in_clan(m.joinedDate)
        expected = get_expected_rank_from_months(months)

        if RANK_INDEX[m.rank] < RANK_INDEX[expected]:
            candidates.append(
                PromotionCandidate(
                    rsn=m.rsn,
                    currentRank=m.rank,
                    expectedRank=expected,
                    joinedDate=m.joinedDate,
                    monthsInClan=months,
                )
            )
    return candidates


# -------------------
# Discord Helpers
# -------------------
def split_into_chunks(lines: List[str], max_len=1500) -> List[str]:
    chunks = []
    current = []

    for l in lines:
        if sum(len(x) + 1 for x in current) + len(l) + 1 > max_len:
            chunks.append("\n".join(current))
            current = []
        current.append(l)

    if current:
        chunks.append("\n".join(current))

    return chunks


def send_discord_message(text: str):
    subprocess.run([
        "curl", "-X", "POST", DISCORD_WEBHOOK_URL,
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"content": text})
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def post_to_discord(result: ComparisonResult):
    if not DISCORD_WEBHOOK_URL:
        return

    # ---------- SUMMARY MESSAGE ----------
    summary_lines = []
    summary_lines.append(f"**Clan sync results for {result.clanName}**")
    summary_lines.append("")

    # Members in clan but NOT Temple
    summary_lines.append(f"Members in clan but NOT Temple ({len(result.clanNotInTemple)}):")
    if result.clanNotInTemple:
        summary_lines.append("```")
        summary_lines.extend(result.clanNotInTemple)
        summary_lines.append("```")
    else:
        summary_lines.append("`All clan members are in sync with Temple!`")

    summary_lines.append("")
    # Members in Temple but NOT clan  <-- fixed f-string here
    summary_lines.append(f"Members in Temple but NOT clan ({len(result.templeNotInClan)}):")
    if result.templeNotInClan:
        summary_lines.append("```")
        summary_lines.extend(result.templeNotInClan)
        summary_lines.append("```")
    else:
        summary_lines.append("`All clan memberes in Temple are in sync with the in game clan!`")

    summary_lines.append("")
    summary_lines.append(f"Members eligible for promotion: {len(result.needsPromotion)}")
    summary_lines.append("Full list follows below:")

    summary = "\n".join(summary_lines)
    send_discord_message(summary)

    # ---------- PROMOTION LIST ----------
    if not result.needsPromotion:
        send_discord_message("`No members are due for promotion.`")
        return

    # Short promotion lines, sorted by RSN
    promo_lines = [
        f"{p.rsn}: {p.currentRank} -> {p.expectedRank}"
        for p in sorted(result.needsPromotion, key=lambda x: x.rsn.lower())
    ]

    chunks = split_into_chunks(promo_lines)

    # Send each chunk wrapped in its own code block
    for chunk in chunks:
        send_discord_message(f"```\n{chunk}\n```")

# -------------------
# Main Endpoint
# -------------------
@app.post("/compare-clan", response_model=ComparisonResult)
def compare_clan(payload: ClanPayload):
    refresh_temple_members()
    temple_list = load_temple_list()

    clan_raw = [m.rsn for m in payload.clanMemberMaps]

    temple_set = {normalize_name(n) for n in temple_list}
    clan_set = {normalize_name(n) for n in clan_raw}

    clan_not = sorted([n for n in clan_raw if normalize_name(n) not in temple_set], key=str.lower)
    temple_not = sorted([n for n in temple_list if normalize_name(n) not in clan_set], key=str.lower)

    promotions = calculate_promotion_candidates(payload.clanMemberMaps)

    result = ComparisonResult(
        clanName=payload.clanName,
        clanNotInTemple=clan_not,
        templeNotInClan=temple_not,
        needsPromotion=promotions,
    )

    post_to_discord(result)

    return result

