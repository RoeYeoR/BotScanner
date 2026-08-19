import json
import os
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 1. Load Environment Variables (.env locally, GitHub Secrets on GitHub Actions)
# ---------------------------------------------------------------------------
load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SEEN_POSTS_FILE = "seen_posts.json"

# ---------------------------------------------------------------------------
# 2. Search Queries targeting LinkedIn posts in Israel
# ---------------------------------------------------------------------------
SEARCH_QUERIES = [
    'site:linkedin.com/posts "junior" "israel" ("full stack" OR "fullstack" OR "software" OR "AI")',
    'site:linkedin.com/posts "ג\'וניור" "ישראל" ("פולסטאק" OR "פול סטאק" OR "פיתוח" OR "תוכנה")',
]

# ---------------------------------------------------------------------------
# 3. Filtering Keywords
# ---------------------------------------------------------------------------
REQUIRED_TECH = [
    # Full Stack
    "full stack",
    "fullstack",
    "full-stack",
    "פול סטאק",
    "פולסטאק",
    # AI & General Engineering
    "software",
    "ai",
    "developer",
    "engineer",
    "python",
    "backend",
    "frontend",
    "llm",
    "machine learning",
    # Junior Terminology
    "ג'וניור",
    "גוניור",
    "junior",
]

EXCLUDE_WORDS = [
    "lawyer",
    "legal",
    "עורך דין",
    "משפטים",
    "marketing",
    "מחפש עבודה",
    "looking for my first",
    "open to work",
]

# ---------------------------------------------------------------------------
# 4. Helper Functions
# ---------------------------------------------------------------------------


def load_seen_posts():
  """Loads previously recorded post URLs to avoid duplicates."""
  if os.path.exists(SEEN_POSTS_FILE):
    try:
      with open(SEEN_POSTS_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f))
    except Exception as e:
      print(f"Warning: Could not read {SEEN_POSTS_FILE}: {e}")
      return set()
  return set()


def save_seen_posts(seen_posts):
  """Saves updated post URLs back to JSON file."""
  with open(SEEN_POSTS_FILE, "w", encoding="utf-8") as f:
    json.dump(list(seen_posts), f, ensure_ascii=False, indent=2)


def send_telegram_message(text):
  """Sends an alert to your Telegram bot."""
  if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("Error: Missing Telegram credentials.")
    return

  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
  try:
    response = requests.post(url, json=payload, timeout=10)
    if not response.ok:
      print(f"Telegram API Error: {response.text}")
  except Exception as e:
    print(f"Failed to send Telegram message: {e}")


def is_relevant(title, snippet):
  """Filters out non-tech roles, lawyers, and job seekers."""
  text = f"{title} {snippet}".lower()

  # 1. Exclude non-tech or self-seeking posts
  if any(bad in text for bad in EXCLUDE_WORDS):
    return False

  # 2. Must explicitly mention Junior
  if "junior" not in text and "ג'וניור" not in text and "גוניור" not in text:
    return False

  # 3. Must match relevant engineering/tech terms
  if any(tech in text for tech in REQUIRED_TECH):
    return True

  return False


def fetch_google_results(query):
  """Queries Serper API for LinkedIn posts indexed by Google."""
  if not SERPER_API_KEY:
    print("Error: Missing SERPER_API_KEY environment variable.")
    return []

  url = "https://google.serper.dev/search"
  payload = json.dumps({"q": query, "gl": "il", "hl": "en", "num": 10})
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

      # Skip if link was already alerted previously
      if link in seen_posts:
        continue

      if is_relevant(title, snippet):
        seen_posts.add(link)
        new_count += 1

        message = (
            f"🚀 *New Junior Job Post Found!*\n\n"
            f"*Title:* {title}\n"
            f"*Snippet:* {snippet}\n\n"
            f"🔗 [Open Post]({link})"
        )
        send_telegram_message(message)

  save_seen_posts(seen_posts)
  print(f"Scan completed. Found {new_count} new relevant post(s).")


if __name__ == "__main__":
  run_scanner()