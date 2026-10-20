import logging
import re

from app.integrations.mcp_client import explore_application as fetch_application_snapshot

logging.basicConfig(level = logging.INFO)

IGNORED_WORD = {"field", "element", "input", "button", "link", "the", "a", "an", "for"}
ROLE_PATTERN = re.compile(r"\b(textbox|button|link|checkbox|radio|combobox|listbox|option|img|image)\b", re.IGNORECASE)
REF_PATTERN = re.compile(r"\[ref=([^\]]+)\]")
QUOTED_TEXT_PATTERN = re.compile(r'"([^"]+)"')

def tokenization(value: str) -> set[str]:
    words = set(re.findall(r"[a-z0-9]+", value.lower()))
    return words - IGNORED_WORD

def extract_label(line: str) -> str:
    quoted = QUOTED_TEXT_PATTERN.search(line)
    if quoted:
        return quoted.group(1)
    if ":" in line:
        return line.split(":", 1)[1].strip()
    return ""

def find_element_match(name:str, purpose:str, snapshot:str) -> dict:
    lines = snapshot.splitlines()
    name_words = tokenization(name)
    purpose_words = tokenization(purpose)

    if not name_words:
        return {"required_name": name, "match_status": "not_found", "evidence": "No meaningful name tokens were provided."} 

    candidates = []