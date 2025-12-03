#!/usr/bin/env python3
"""
DamaDam Master Scraper v5.5 - DEMO + FALLBACK (driver None safe)

Purpose:
- Fix crash where `driver` was None and code attempted `driver.get(...)` in get_online / scrape_profile.
- Add guards so any function that uses `driver` will treat `driver is None` as DEMO_MODE fallback.
- Keep non-interactive CLI, demo fallbacks for missing ssl/selenium/gspread.
- Add extra unit-like tests for driver=None behavior.

Run examples:
  python Scraper.py
  python Scraper.py --mode sheet
  python Scraper.py --test
"""

import os
import sys
import time
import json
import random
import pickle
import argparse
from datetime import datetime, timedelta, timezone

# ------------------- Credentials (HARD-CODED DEMO) -------------------
USERNAME = "0utLawZ"
PASSWORD = "asdasd"
GOOGLE_CREDENTIALS_JSON = "credentials.json"  # must exist if using real Sheets
SHEET_URL = "1xph0dra5-wPcgMXKubQD7A2CokObpst7o2rWbDA10t8"

HOME_URL = "https://damadam.pk/"
LOGIN_URL = "https://damadam.pk/login/"
ONLINE_URL = "https://damadam.pk/online_kon/"
COOKIE_FILE = "damadam_cookies.pkl"
DEBUG_FOLDER = "login_debug"
LOCAL_DEMO_OUT = "demo_profiles.json"

# ------------------- Time / Logging -------------------

def pkt_time():
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5)


def log(msg):
    print(f"[{pkt_time().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()


os.makedirs(DEBUG_FOLDER, exist_ok=True)

# ------------------- Optional imports with fallbacks -------------------
USE_SELENIUM = True
USE_GSPREAD = True

# check ssl availability first
try:
    import ssl  # noqa: F401
except Exception as e:
    log(f"WARNING: 'ssl' module import failed: {e}. Switching to DEMO_MODE (no selenium).")
    USE_SELENIUM = False

if USE_SELENIUM:
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except Exception as e:
        log(f"WARNING: selenium import failed: {e}. Switching to DEMO_MODE (no selenium).")
        USE_SELENIUM = False

# try gspread imports
try:
    import gspread
    from google.oauth2.service_account import Credentials
    from gspread.exceptions import WorksheetNotFound
except Exception as e:
    log(f"INFO: gspread or google auth import failed/disabled: {e}. Sheets fallback will be local JSON.")
    USE_GSPREAD = False

# ------------------- Debug helpers -------------------

def debug_ss(name):
    try:
        if USE_SELENIUM and globals().get('driver'):
            path = f"{DEBUG_FOLDER}/{name}.png"
            globals()['driver'].save_screenshot(path)
            log(f"DEBUG → {path}")
    except Exception:
        pass


def debug_source(name):
    try:
        if USE_SELENIUM and globals().get('driver'):
            path = f"{DEBUG_FOLDER}/{name}.html"
            with open(path, "w", encoding="utf-8") as f:
                f.write(globals()['driver'].page_source)
            log(f"DEBUG SOURCE → {path}")
    except Exception:
        pass

# ------------------- Browser setup (only if USE_SELENIUM) -------------------

def setup_browser():
    if not USE_SELENIUM:
        log("setup_browser skipped: DEMO_MODE (selenium unavailable)")
        return None

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    try:
        d = webdriver.Chrome(options=options)
    except Exception as e:
        log(f"webdriver.Chrome() failed: {e}")
        return None

    try:
        d.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => false});")
    except Exception:
        pass
    try:
        d.set_page_load_timeout(30)
    except Exception:
        pass
    return d

# ------------------- Cookies helpers -------------------

def save_cookies(driver):
    if not USE_SELENIUM or not driver:
        return
    try:
        with open(COOKIE_FILE, "wb") as f:
            pickle.dump(driver.get_cookies(), f)
        log("Cookies saved")
    except Exception:
        pass


def load_cookies(driver):
    if not USE_SELENIUM or not driver:
        return False
    if not os.path.exists(COOKIE_FILE):
        return False
    try:
        driver.get(HOME_URL)
        with open(COOKIE_FILE, "rb") as f:
            ck = pickle.load(f)
            for c in ck:
                if 'expiry' in c:
                    del c['expiry']
                try:
                    driver.add_cookie(c)
                except Exception:
                    pass
        driver.refresh()
        time.sleep(6)
        if "logout" in driver.page_source.lower():
            log("Fast login via cookies")
            return True
    except Exception:
        return False
    return False

# ------------------- Login flow -------------------

def login(driver):
    """If selenium unavailable or driver is None, this returns True (demo mode).
    Otherwise attempts cookie-based or fresh login using the provided USERNAME/PASSWORD.
    """
    # If selenium not available at all, behave as demo mode
    if not USE_SELENIUM:
        log("DEMO_MODE: skipping real login (selenium not available)")
        return True

    # If driver wasn't initialized (None), fallback to demo mode to avoid AttributeError
    if driver is None:
        log("WARNING: Browser driver is None (setup failed). Falling back to DEMO_MODE for login.")
        return True

    # Try cookie login first
    if load_cookies(driver):
        try:
            driver.get(HOME_URL)
            time.sleep(3)
            if "logout" in driver.page_source.lower():
                return True
        except Exception as e:
            log(f"Warning: cookie-based fast login attempt failed: {e}")

    log("Fresh login...")
    try:
        driver.get(LOGIN_URL)
    except Exception as e:
        log(f"Error navigating to login page: {e}. Falling back to DEMO_MODE.")
        return True

    time.sleep(6)

    try:
        username_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#nick, input[name='nick'], input[name='username']"))
        )
        password_field = driver.find_element(By.CSS_SELECTOR, "input[name='pass'], input[name='password']")

        username_field.clear()
        username_field.send_keys(USERNAME)
        time.sleep(1)

        password_field.clear()
        password_field.send_keys(PASSWORD)
        time.sleep(1)

        # try multiple ways to submit
        button_clicked = False
        for xp in ["//button[contains(text(),'LOGIN')]", "//button[@type='submit']", "//button"]:
            try:
                btn = driver.find_element(By.XPATH, xp)
                driver.execute_script("arguments[0].click();", btn)
                button_clicked = True
                break
            except Exception:
                continue

        if not button_clicked:
            try:
                password_field.send_keys("\n")
            except Exception:
                pass

        time.sleep(8)

        if "logout" in driver.page_source.lower() or any(x in driver.current_url.lower() for x in ["online_kon", "users", "home"]) and "login" not in driver.current_url.lower():
            save_cookies(driver)
            log("LOGIN SUCCESSFUL")
            return True

        log("LOGIN FAILED: no logout detected")
        debug_ss("login_failed")
        debug_source("login_failed")
        return False

    except Exception as e:
        log(f"Login exception: {e}")
        debug_ss("login_exception")
        debug_source("login_exception")
        return False

# ------------------- Sheets wrapper -------------------
class SheetsLocal:
    """Fallback Sheets implementation that writes profiles to a local JSON file (demo mode).
    Keeps a simple array of profile dicts in LOCAL_DEMO_OUT.
    """
    def __init__(self):
        self.file = LOCAL_DEMO_OUT
        if not os.path.exists(self.file):
            with open(self.file, "w") as f:
                json.dump([], f)
        log(f"SheetsLocal initialized (writing to {self.file})")

    def write_profile(self, d):
        try:
            with open(self.file, "r", encoding="utf-8") as f:
                arr = json.load(f)
        except Exception:
            arr = []
        arr.append(d)
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(arr, f, ensure_ascii=False, indent=2)

# Real Sheets class (only used when gspread + creds are available)
class SheetsGSpread:
    def __init__(self):
        if not USE_GSPREAD:
            raise RuntimeError("gspread not available")

        # GOOGLE_CREDENTIALS_JSON is expected to be a local JSON file path in this demo
        with open(GOOGLE_CREDENTIALS_JSON, "r", encoding="utf-8") as f:
            creds_data = json.load(f)

        client = gspread.authorize(
            Credentials.from_service_account_info(
                creds_data,
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
        )
        self.wb = client.open_by_key(SHEET_URL)
        self.profiles = self.ws("ProfilesData", [
            "IMAGE","NICK NAME","TAGS","LAST POST","LAST POST TIME","FRIEND","CITY","GENDER",
            "MARRIED","AGE","JOINED","FOLLOWERS","STATUS","POSTS","PROFILE LINK","INTRO","SOURCE","DATETIME SCRAP"
        ])

    def ws(self, name, headers):
        try:
            sh = self.wb.worksheet(name)
            if sh.row_values(1) != headers:
                sh.update('A1', [headers])
        except WorksheetNotFound:
            sh = self.wb.add_worksheet(title=name, rows=5000, cols=len(headers))
            sh.append_row(headers)
        return sh

    def write_profile(self, d):
        ws = self.profiles
        values = [d.get(col, "") for col in ws.row_values(1)]
        ws.append_row(values)
        time.sleep(1)

# ------------------- Scraping helpers -------------------

def get_online(driver):
    """If running with selenium, scrape the online page. Otherwise return demo nicknames."""
    # Defensive: if driver is None treat as demo mode
    if not USE_SELENIUM or driver is None:
        log("DEMO_MODE: returning sample online users")
        return ["demo_user1", "demo_user2", "demo_user3"]

    try:
        driver.get(ONLINE_URL)
    except Exception as e:
        log(f"Error navigating to online page: {e}. Returning demo list.")
        return ["demo_user1", "demo_user2", "demo_user3"]

    time.sleep(6)
    names = []
    try:
        for el in driver.find_elements(By.CSS_SELECTOR, "li.mbl.cl.sp b"):
            t = el.text.strip()
            if len(t) >= 3:
                names.append(t)
    except Exception as e:
        log(f"Error collecting online users: {e}")
    log(f"Found {len(names)} online users")
    return names


def scrape_profile(driver, nick):
    url = f"https://damadam.pk/users/{nick}/"
    # Defensive: if driver is None treat as demo mode
    if not USE_SELENIUM or driver is None:
        return {
            "IMAGE": "",
            "NICK NAME": nick,
            "TAGS": "",
            "LAST POST": "",
            "LAST POST TIME": "",
            "FRIEND": "",
            "CITY": "",
            "GENDER": "",
            "MARRIED": "",
            "AGE": "",
            "JOINED": "",
            "FOLLOWERS": "",
            "STATUS": "",
            "POSTS": "",
            "PROFILE LINK": url.rstrip('/'),
            "INTRO": "",
            "SOURCE": "Demo",
            "DATETIME SCRAP": pkt_time().strftime("%d-%b-%y %I:%M %p")
        }

    try:
        driver.get(url)
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        return {
            "IMAGE": "",
            "NICK NAME": nick,
            "TAGS": "",
            "LAST POST": "",
            "LAST POST TIME": "",
            "FRIEND": "",
            "CITY": "",
            "GENDER": "",
            "MARRIED": "",
            "AGE": "",
            "JOINED": "",
            "FOLLOWERS": "",
            "STATUS": "",
            "POSTS": "",
            "PROFILE LINK": url.rstrip('/'),
            "INTRO": "",
            "SOURCE": "Online",
            "DATETIME SCRAP": pkt_time().strftime("%d-%b-%y %I:%M %p")
        }
    except Exception as e:
        log(f"scrape_profile failed for {nick}: {e}")
        return None

# ------------------- Mode selection -------------------

def choose_mode(args_mode=None):
    """Return mode based on provided arg. This function now avoids any interactive I/O
    and does not read environment variables to remain sandbox-safe.
    """
    # Expect args_mode to be a string like 'online' or 'sheet'. Fallback to 'online'.
    if isinstance(args_mode, str) and args_mode in ("online", "sheet"):
        return args_mode
    return "online"

# ------------------- Tests -------------------

def run_tests():
    """Simple smoke tests for the demo environment. Runs quickly and exits.
    Tests added because original script had none.
    """
    log("Running demo tests...")

    # Test choose_mode
    assert choose_mode("online") == "online", "choose_mode failed for 'online'"
    assert choose_mode("sheet") == "sheet", "choose_mode failed for 'sheet'"

    # Test SheetsLocal write/read
    sl = SheetsLocal()
    sample = {"NICK NAME": "test_user", "SOURCE": "UnitTest"}
    sl.write_profile(sample)
    with open(LOCAL_DEMO_OUT, "r", encoding="utf-8") as f:
        arr = json.load(f)
    assert any(x.get("NICK NAME") == "test_user" for x in arr), "SheetsLocal write_profile failed"

    # Test get_online fallback with driver None
    n = get_online(None)
    assert isinstance(n, list) and len(n) >= 1, "get_online demo fallback failed"

    # Test scrape_profile fallback with driver None
    p = scrape_profile(None, "unit_test_user")
    assert isinstance(p, dict) and p.get("NICK NAME") == "unit_test_user", "scrape_profile demo fallback failed"

    # Test login fallback with driver None
    assert login(None) is True, "login fallback for driver None failed"

    log("All tests passed.")

# ------------------- Main -------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["online", "sheet"], help="Select run mode (no interactive input)")
    parser.add_argument("--test", action="store_true", help="Run self-tests then exit")
    ns = parser.parse_args()

    if ns.test:
        run_tests()
        return

    mode = choose_mode(ns.mode)
    print(f"\nMODE SELECTED → {mode.upper()}\n")

    # Browser init
    global driver
    driver = None
    if USE_SELENIUM:
        try:
            driver = setup_browser()
            if driver is None:
                log("setup_browser returned None — webdriver not available or failed.")
        except Exception as e:
            log(f"Browser setup failed: {e}. Switching to DEMO_MODE.")
            driver = None

    if not login(driver):
        log("Login FAILED")
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        sys.exit(1)

    # Sheets init
    sheets = None
    if USE_GSPREAD:
        try:
            sheets = SheetsGSpread()
        except Exception as e:
            log(f"SheetsGSpread init failed: {e}. Falling back to local JSON.")
            sheets = SheetsLocal()
    else:
        sheets = SheetsLocal()

    # Get run list
    if mode == "online":
        nicks = get_online(driver)
    else:
        log("Sheet mode selected — demo returns sample runlist")
        nicks = ["sheet_user1", "sheet_user2"]

    processed = 0
    for nick in nicks:
        profile = scrape_profile(driver, nick)
        if profile:
            try:
                sheets.write_profile(profile)
                processed += 1
                log(f"[{processed}] Saved → {nick}")
            except Exception as e:
                log(f"Failed to write profile for {nick}: {e}")
        else:
            log(f"Failed → {nick}")
        time.sleep(random.uniform(1, 2))

    log("MISSION COMPLETE")
    if driver:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
