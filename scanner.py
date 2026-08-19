import json
import os
import time
import requests

# Configurable Parameters
SERPER_API_KEY = "9bdb4ece0450248797f50895f3f6260dac6370e7"
TELEGRAM_BOT_TOKEN = "8736846922:AAHACwyCow6FoBTnaCkVWOJSS0W6jpzTxJw "
TELEGRAM_CHAT_ID = "1879174304"

SEEN_POSTS_FILE = "seen_posts.json"

# Search queries targeting LinkedIn posts in Israel
SEARCH_QUERIES = [
    'site:linkedin.com/posts "junior" "israel" ("full stack" OR "software" OR "AI")',
    'site:linkedin.com/posts "ג\'וניור" "ישראל" ("מגייסים" OR "פיתוח" OR "תוכנה")',
]

# Keywords for precise filtering
REQUIRED_TECH = [
    "full stack",
    "fullstack",
    "software",
    "ai",
    "developer",
    "engineer",
    "python",
    "backend",
    "frontend",
    "llm",
    "machine learning",
    "ג'וניור",
    "גוניור",
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


def load_seen_posts():
  if os.path.exists(SEEN_POSTS_FILE):
    with open(SEEN_POSTS_FILE, "r", encoding="utf-8") as f:
      return set(json.load(f))
  return set()


def save_seen_posts(seen_posts):
  with open(SEEN_POSTS_FILE, "w", encoding="utf-8") as f:
    json.dump(list(seen_posts), f, ensure_ascii=False, indent=2)


def send_telegram_message(text):
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
  try:
    requests.post(url, json=payload, timeout=10)
  except Exception as e:
    print(f"Failed to send Telegram message: {e}")


def is_relevant(title, snippet):
  text = f"{title} {snippet}".lower()

  # 1. Exclude irrelevant industries or self-posts
  if any(bad in text for bad in EXCLUDE_WORDS):
    return False

  # 2. Must explicitly mention Junior
  if "junior" not in text and "ג'וניור" not in text and "גוניור" not in text:
    return False

  # 3. Must match tech keywords
  if any(tech in text for tech in REQUIRED_TECH):
    return True

  return False


def fetch_google_results(query):
  url = "https://google.serper.dev/search"
  payload = json.dumps({"q": query, "gl": "il", "hl": "en", "num": 10})
  headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}

  try:
    response = requests.post(url, headers=headers, data=payload, timeout=10)
    return response.json().get("organic", [])
  except Exception as e:
    print(f"Error fetching search results: {e}")
    return []


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
            f"*Title:* {title}\n"
            f"*Snippet:* {snippet}\n\n"
            f"🔗 [Open Post]({link})"
        )
        send_telegram_message(message)

  save_seen_posts(seen_posts)
  print(f"Scan completed. Found {new_count} new relevant post(s).")


if __name__ == "__main__":
  run_scanner()