#!/usr/bin/env python3
"""
DamaDam Master Bot v2.0 - FINAL VERSION (Username + Password Login)
- No cookies.txt, no pickle, no Cloudflare issues
- Real login like your working message bot
- Auto saves cookies for faster future runs
"""

import os
import sys
import time
import json
import random
import argparse
import pickle
from datetime import datetime, timedelta, timezone

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound

# ============================================================================
# CONFIG
# ============================================================================

USERNAME = os.getenv("DAMADAM_USERNAME")
PASSWORD = os.getenv("DAMADAM_PASSWORD")
HOME_URL = "https://damadam.pk/"
LOGIN_URL = "https://damadam.pk/login/"
ONLINE_URL = "https://damadam.pk/online_kon/"
COOKIE_FILE = "damadam_cookies.pkl"

SHEET_URL = os.getenv('GOOGLE_SHEET_URL')
GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')

MAX_PROFILES_PER_RUN = int(os.getenv('MAX_PROFILES_PER_RUN', '0'))

# Sheets
PROFILES_SHEET = "ProfilesData"
TIMING_LOG_SHEET = "TimingLog"
DASHBOARD_SHEET = "Dashboard"

COLUMN_ORDER = [
    "IMAGE", "NICK NAME", "TAGS", "LAST POST", "LAST POST TIME", "FRIEND", "CITY",
    "GENDER", "MARRIED", "AGE", "JOINED", "FOLLOWERS", "STATUS",
    "POSTS", "PROFILE LINK", "INTRO", "SOURCE", "DATETIME SCRAP"
]

# ============================================================================
# HELPERS
# ============================================================================

def pkt_time():
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5)

def log(msg):
    print(f"[{pkt_time().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

# ============================================================================
# BROWSER
# ============================================================================

def setup_browser():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => false});")
    driver.set_page_load_timeout(30)
    return driver

def save_cookies(driver):
    try:
        with open(COOKIE_FILE, "wb") as f:
            pickle.dump(driver.get_cookies(), f)
        log("Cookies saved for next run")
    except: pass

def load_cookies(driver):
    if not os.path.exists(COOKIE_FILE):
        return False
    try:
        driver.get(HOME_URL)
        with open(COOKIE_FILE, "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                driver.add_cookie(cookie)
        driver.refresh()
        time.sleep(4)
        if "logout" in driver.page_source.lower():
            log("Logged in via saved cookies!")
            return True
    except: pass
    return False

def login(driver):
    if load_cookies(driver):
        return True

    log("Opening login page...")
    driver.get(LOGIN_URL)
    time.sleep(10)

    try:
        # Wait for username field (new name="username")
        username = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.NAME, "username"))
        )
        password = driver.find_element(By.NAME, "password")

        username.clear()
        username.send_keys(USERNAME)
        time.sleep(1.5)
        password.clear()
        password.send_keys(PASSWORD)
        time.sleep(1.5)

        # Click the pink LOGIN button
        btn = driver.find_element(By.XPATH, "//button[contains(text(), 'LOGIN')]")
        driver.execute_script("arguments[0].click();", btn)

        log("Login button clicked, waiting for redirect...")
        time.sleep(12)

        if any(x in driver.current_url for x in ["/home/", "/online_kon/", "/users/"]):
            log("LOGIN 100% SUCCESSFUL!")
            save_cookies(driver)
            return True
        else:
            log("Still not logged in - checking page source...")
            if "login" in driver.current_url:
                log("Still on login page - wrong password or blocked")
            driver.save_screenshot("login_debug.png")
            return False

    except Exception as e:
        log(f"Critical login error: {e}")
        driver.save_screenshot("login_critical.png")
        return False

# ============================================================================
# SHEETS + FORMATTING (from your example bot)
# ============================================================================

def get_client():
    creds = Credentials.from_service_account_info(json.loads(GOOGLE_CREDENTIALS_JSON),
                scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds)

class Sheets:
    def __init__(self):
        self.wb = get_client().open_by_url(SHEET_URL)
        self.profiles = self.ws(PROFILES_SHEET, COLUMN_ORDER)
        self.timing = self.ws(TIMING_LOG_SHEET, ["Nickname", "Timestamp", "Source", "Run Number"])
        self.dash = self.ws(DASHBOARD_SHEET, ["Metric", "Value"])

    def ws(self, name, headers):
        try:
            ws = self.wb.worksheet(name)
        except WorksheetNotFound:
            ws = self.wb.add_worksheet(title=name, rows=5000, cols=len(headers))
            ws.append_row(headers)
        return ws

    def write(self, profile):
        ws = self.profiles
        nick = profile["NICK NAME"].lower()
        rows = ws.get_all_values()
        row_num = next((i+2 for i, r in enumerate(rows[1:]) if len(r) > 1 and r[1].lower() == nick), None)

        values = [profile.get(col, "") for col in COLUMN_ORDER]
        if row_num:
            ws.update(f"A{row_num}", [values])
        else:
            ws.append_row(values)
        time.sleep(1)

    def log_time(self, nick, src, run):
        self.timing.append_row([nick, pkt_time().strftime("%d-%b-%y %I:%M %p"), src, run])

    def update_dash(self, data):
        ws = self.dash
        existing = {r[0]: i+1 for i, r in enumerate(ws.get_all_values()) if r}
        for k, v in data.items():
            if k in existing:
                ws.update_cell(existing[k], 2, v)
            else:
                ws.append_row([k, v])

# ============================================================================
# SCRAPING
# ============================================================================

def get_online_users(driver):
    log("Fetching online users...")
    driver.get(ONLINE_URL)
    time.sleep(6)
    users = []
    for el in driver.find_elements(By.CSS_SELECTOR, "li.mbl.cl.sp b"):
        nick = el.text.strip()
        if nick and len(nick) >= 3:
            users.append(nick)
    log(f"Found {len(users)} online users")
    return users

def scrape_profile(driver, nick):
    url = f"https://damadam.pk/users/{nick}/"
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        return {
            "IMAGE": "", "NICK NAME": nick, "TAGS": "", "LAST POST": "", "LAST POST TIME": "",
            "FRIEND": "", "CITY": "", "GENDER": "", "MARRIED": "", "AGE": "", "JOINED": "",
            "FOLLOWERS": "", "STATUS": "", "POSTS": "", "PROFILE LINK": url.rstrip("/"),
            "INTRO": "", "SOURCE": "Online", "DATETIME SCRAP": pkt_time().strftime("%d-%b-%y %I:%M %p")
        }
    except:
        return None

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    limit = args.limit or MAX_PROFILES_PER_RUN

    print("\n" + "="*80)
    print("DAMADAM MASTER BOT v2.0 - USERNAME/PASSWORD LOGIN")
    print("="*80 + "\n")

    driver = setup_browser()
    if not login(driver):
        driver.quit()
        sys.exit(1)

    sheets = Sheets()
    run_num = len(sheets.dash.get_all_values())
    users = get_online_users(driver)

    saved = 0
    for i, nick in enumerate(users):
        if limit and saved >= limit:
            break
        profile = scrape_profile(driver, nick)
        if profile:
            sheets.write(profile)
            sheets.log_time(nick, "Online", run_num)
            saved += 1
            log(f"[{i+1}] Saved → {nick}")
        time.sleep(random.uniform(1.5, 3))

    sheets.update_dash({
        "Last Run": pkt_time().strftime("%d-%b-%y %I:%M %p"),
        "Profiles Processed": saved,
        "Run Number": run_num + 1
    })

    log("ALL DONE!")
    driver.quit()

if __name__ == "__main__":
    main()
