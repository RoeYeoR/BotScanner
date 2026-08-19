import json
import os
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 1. Load Environment Variables
# ---------------------------------------------------------------------------
load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SEEN_POSTS_FILE = "seen_posts.json"

# ---------------------------------------------------------------------------
# 2. Refined Search Queries (Focused on Hiring & Employers)
# ---------------------------------------------------------------------------
SEARCH_QUERIES = [
    # English queries targeting job posts
    'site:linkedin.com/posts "junior" "israel" ("hiring" OR "we are hiring" OR "looking for a") ("full stack" OR "fullstack" OR "software" OR "AI")',
    # Hebrew queries targeting recruiters/employers
    'site:linkedin.com/posts ("ג\'וניור" OR "גוניור") "ישראל" ("מגייסים" OR "דרוש" OR "דרושה" OR "משרה") ("פולסטאק" OR "פול סטאק" OR "פיתוח")',
]

# ---------------------------------------------------------------------------
# 3. Enhanced Filtering Lists
# ---------------------------------------------------------------------------
REQUIRED_TECH = [
    "full stack",
    "fullstack",
    "full-stack",
    "פול סטאק",
    "פולסטאק",
    "software",
    "ai",
    "developer",
    "engineer",
    "python",
    "backend",
    "frontend",
]

# Words indicating someone is HIRING (Must contain at least one)
HIRING_INDICATORS = [
    "hiring",
    "we're hiring",
    "we are hiring",
    "join our team",
    "looking for a",
    "open position",
    "מגייסים",
    "דרוש",
    "דרושה",
    "מחפשים",
    "משרה",
    "להגשת מועמדות",
    "קורות חיים",
    "cv",
]

# Strict exclusion list to discard job seekers, lawyers, courses, etc.
EXCLUDE_WORDS = [
    # Job seekers' phrases (Hebrew & English)
    "מחפש עבודה",
    "מחפשת עבודה",
    "מחפש את המשרה",
    "מחפשת את המשרה",
    "looking for my first",
    "open to work",
    "סיימתי קורס",
    "האקריו",
    "hackeru",
    "תיק עבודות",
    "אשמח לעזרתכם",
    "לייק קטן",
    "תגובה מגניבה",
    "looking for a junior role",
    "looking for a full-stack",
    # Irrelevant professions
    "lawyer",
    "legal",
    "עורך דין",
    "משפטים",
    "marketing",
]

# ---------------------------------------------------------------------------
# 4. Helper Functions
# ---------------------------------------------------------------------------


def load_seen_posts():
  if os.path.exists(SEEN_POSTS_FILE):
    try:
      with open(SEEN_POSTS_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f))
    except Exception as e:
      print(f"Warning: Could not read {SEEN_POSTS_FILE}: {e}")
      return set()
  return set()


def save_seen_posts(seen_posts):
  with open(SEEN_POSTS_FILE, "w", encoding="utf-8") as f:
    json.dump(list(seen_posts), f, ensure_ascii=False, indent=2)


def send_telegram_message(text):
  if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("Error: Missing Telegram credentials.")
    return

  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = {
      "chat_id": TELEGRAM_CHAT_ID,
      "text": text,
      "parse_mode": "Markdown",
      "disable_web_page_preview": False,
  }
  try:
    response = requests.post(url, json=payload, timeout=10)
    if not response.ok:
      print(f"Telegram API Error: {response.text}")
  except Exception as e:
    print(f"Failed to send Telegram message: {e}")


def is_relevant(title, snippet):
  text = f"{title} {snippet}".lower()

  # 1. Immediately reject job seekers or irrelevant posts
  if any(bad in text for bad in EXCLUDE_WORDS):
    return False

  # 2. Must explicitly mention "Junior"
  if "junior" not in text and "ג'וניור" not in text and "גוניור" not in text:
    return False

  # 3. Must contain at least one HIRING indicator (Employer focus)
  if not any(hiring in text for hiring in HIRING_INDICATORS):
    return False

  # 4. Must match relevant tech keywords
  if any(tech in text for tech in REQUIRED_TECH):
    return True

  return False


def fetch_google_results(query):
  if not SERPER_API_KEY:
    print("Error: Missing SERPER_API_KEY environment variable.")
    return []

  url = "https://google.serper.dev/search"

  # 'tbs': 'qdr:w' restricts Google Search results strictly to the PAST WEEK
  payload = json.dumps(
      {"q": query, "gl": "il", "hl": "en", "num": 10, "tbs": "qdr:w"}
  )

  headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}

  try:
    response = requests.post(url, headers=headers, data=payload, timeout=10)
    return response.json().get("organic", [])
  except Exception as e:
    print(f"Error fetching search results for query '{query}': {e}")
    return []


# ---------------------------------------------------------------------------
# 5. Main Execution Loop
# ---------------------------------------------------------------------------


def run_scanner():
  seen_posts = load_seen_posts()
  new_count = 0

  for query in SEARCH_QUERIES:
    results = fetch_google_results(query)
    for item in results:
      link = item.get("link", "")
      title = item.get("title", "")
      snippet = item.get("snippet", "")

      if link in seen_posts:
        continue

      if is_relevant(title, snippet):
        seen_posts.add(link)
        new_count += 1

        message = (
            f"🚀 *New Junior Job Post Found!*\n\n"
            f"📌 *Title:* {title}\n"
            f"📝 *Snippet:* {snippet}\n\n"
            f"🔗 [Click here to view LinkedIn Post]({link})"
        )
        send_telegram_message(message)

  save_seen_posts(seen_posts)
  print(f"Scan completed. Found {new_count} new relevant post(s).")


if __name__ == "__main__":
  run_scanner()