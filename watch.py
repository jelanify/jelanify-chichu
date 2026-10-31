"""Chichu ticket watcher: pings your phone (via ntfy) when a ticket page changes."""
import json, os, re, sys
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright

# Pages to watch. Add more lines in the same format if you like
# (e.g. the Teshima 18th page to catch an earlier slot).
PAGES = {
    "Chichu Tue 17 Nov": "https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/ticket/245856?ticketLargeCategoryId=20638&ticketMiddleCategoryId=105231",
    "Chichu Wed 18 Nov": "https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/ticket/245856?ticketLargeCategoryId=20638&ticketMiddleCategoryId=105232",
    "Teshima Wed 18 Nov": "https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/ticket/245856?ticketLargeCategoryId=20641&ticketMiddleCategoryId=105302",
}

TOPIC = os.environ["NTFY_TOPIC"]
STATE = Path("state.json")
HOPEFUL = ["○", "◯", "△", "残りわずか", "空きあり"]  # symbols/words that usually mean "available"


def notify(title, message, url, priority="high"):
    requests.post(
        f"https://ntfy.sh/{TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title, "Click": url, "Priority": priority, "Tags": "ticket"},
        timeout=30,
    )


def read_page(browser, url):
    page = browser.new_page(locale="en-US")
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(4000)        # let the booking widget finish drawing
    page.keyboard.press("Escape")      # close any popover
    text = page.inner_text("body")
    page.close()
    return re.sub(r"\s+", " ", text).strip()


def main():
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, url in PAGES.items():
            try:
                text = read_page(browser, url)
            except Exception as e:
                print(f"{name}: failed to load ({e}), will retry next run")
                continue
            if len(text) < 40:
                print(f"{name}: page looked empty, skipping this run")
                continue

            print(f"--- {name} ---\n{text[:1500]}\n")
            old = state.get(name)
            if old is None:
                notify(f"Watcher started: {name}",
                       "Setup works. You'll get a ping if this page changes.\n\n" + text[:300],
                       url, priority="default")
            elif text != old:
                hint = " Looks like something opened up!" if any(h in text for h in HOPEFUL) else ""
                notify(f"Change on {name}", f"The page changed.{hint} Tap to check now.", url)
            state[name] = text
        browser.close()
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
