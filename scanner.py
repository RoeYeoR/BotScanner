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
# 2. Tightened Search Queries
# ---------------------------------------------------------------------------
SEARCH_QUERIES = [
    # English: Strict employer phrases for target roles in Israel
    'site:linkedin.com/posts "junior" "israel" ("we are hiring" OR "we\'re hiring" OR "hiring a junior") ("full stack" OR "fullstack" OR "software engineer" OR "AI engineer" OR "AI developer")',
    # Hebrew: Specific recruiter/company hiring terms
    'site:linkedin.com/posts ("ג\'וניור" OR "גוניור") "ישראל" ("אנחנו מגייסים" OR "דרוש/ה" OR "מגייסים ג\'וניור") ("פולסטאק" OR "פול סטאק" OR "פיתוח" OR "אינטליגנציה מלאכותית")',
]

# ---------------------------------------------------------------------------
# 3. Targeted Role & Filtering Definitions
# ---------------------------------------------------------------------------
TARGET_ROLES = [
    "ai engineer",
    "ai developer",
    "full stack",
    "fullstack",
    "full-stack",
    "software engineer",
    "software developer",
    "backend",
    "frontend",
    "פול סטאק",
    "פולסטאק",
    "מהנדס תוכנה",
    "מפתח תוכנה",
    "מפתח/ת",
    "מהנדס/ת",
]

# Actionable employer-side phrases indicating a real job opening
HIRING_INDICATORS = [
    "we are hiring",
    "we're hiring",
    "join our team",
    "hiring a junior",
    "looking for a junior",
    "open position",
    "אנחנו מגייסים",
    "דרוש/ה",
    "מגייסים ג'וניור",
    "מגייסים גוניור",
    "מגייסת",
    "שלחו קורות חיים",
    "להגשת מועמדות",
    "send your cv",
    "apply at",
    "apply here",
    "send cv to",
]

# Strict exclusions: Filters out job seekers, career tips, webinars & articles
EXCLUDE_WORDS = [
    # Job seekers
    "מחפש עבודה",
    "מחפשת עבודה",
    "מחפש את המשרה",
    "מחפשת את המשרה",
    " מחפש ",
    " מחפשת ",
    "open to work",
    "looking for my first",
    "looking for a junior role",
    "seeking a position",
    "excited to share",
    "אשמח לעזרתכם",
    "סיימתי קורס",
    "האקריו",
    "hackeru",
    # Thought leadership, articles, podcasts, webinars & tips
    "futureofwork",
    "webinar",
    "podcast",
    "newsletter",
    "tips for",
    "career advice",
    "thought leadership",
    "how to",
    "השתתפתי",
    "הרצאה",
    "וובינר",
    "טיפים",
    "תכנית",
    "קורס",
    "מחזור",
    "סדנא",
    "מנטור",
    # Irrelevant professions
    "lawyer",
    "legal",
    "עורך דין",
    "משפטים",
    "marketing",
    "sales",
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

  # 1. Reject articles, job seekers, and advice posts
  if any(bad in text for bad in EXCLUDE_WORDS):
    return False

  # 2. Must explicitly mention "Junior"
  if not any(j in text for j in ["junior", "ג'וניור", "גוניור"]):
    return False

  # 3. Must contain clear employer hiring intent
  if not any(hiring in text for hiring in HIRING_INDICATORS):
    return False

  # 4. Must match target software / AI developer roles
  if not any(role in text for role in TARGET_ROLES):
    return False

  return True


def fetch_google_results(query):
  if not SERPER_API_KEY:
    print("Error: Missing SERPER_API_KEY environment variable.")
    return []

  url = "https://google.serper.dev/search"
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
