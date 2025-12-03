#!/usr/bin/env python3
"""
DamaDam Master Scraper v5.0 - FINAL BULLETPROOF VERSION
→ python Scraper.py --mode online --limit 0
→ python Scraper.py --mode sheet --limit 50
"""

import os
import sys
import time
import json
import random
import argparse
import pickle
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
from gspread.exceptions import WorksheetNotFound

# ============================= CONFIG =============================
USERNAME = os.getenv("DAMADAM_USERNAME")
PASSWORD = os.getenv("DAMADAM_PASSWORD")
# ============================= CONFIG =============================
USERNAME = os.getenv("DAMADAM_USERNAME")
PASSWORD = os.getenv("DAMADAM_PASSWORD")
HOME_URL = "https://damadam.pk/"
LOGIN_URL = "https://damadam.pk/login/"
LOGIN_URL = "https://damadam.pk/login/"
ONLINE_URL = "https://damadam.pk/online_kon/"
COOKIE_FILE = "damadam_cookies.pkl"
DEBUG_FOLDER = "login_debug"
SHEET_URL = os.getenv('GOOGLE_SHEET_URL')
GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')

# ============================= HELPERS =============================
def pkt_time():
# ============================= HELPERS =============================
def pkt_time():
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5)

def log(msg):
    print(f"[{pkt_time().strftime('%H:%M:%S')}] {msg}")
def log(msg):
    print(f"[{pkt_time().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

os.makedirs(DEBUG_FOLDER, exist_ok=True)
def debug_ss(name):
    path = f"{DEBUG_FOLDER}/{name}.png"
    try:
        driver.save_screenshot(path)
        log(f"DEBUG → {path}")
    except: pass

def debug_source(name):
    path = f"{DEBUG_FOLDER}/{name}.html"
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        log(f"DEBUG SOURCE → {path}")
    except: pass

# ============================= BROWSER =============================
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
    driver.set_page_load_timeout(30)
    return driver

def save_cookies(driver):
    try:
        with open(COOKIE_FILE, "wb") as f:
            pickle.dump(driver.get_cookies(), f)
        log("Cookies saved!")
    except: pass

def load_cookies(driver):
    if not os.path.exists(COOKIE_FILE): return False
    try:
        driver.get(HOME_URL)
        with open(COOKIE_FILE, "rb") as f:
            for cookie in pickle.load(f):
                if 'expiry' in cookie: del cookie['expiry']
                try: driver.add_cookie(cookie)
                except: pass
        driver.refresh()
        time.sleep(6)
        if "logout" in driver.page_source.lower():
            log("Fast login via cookies!")
            return True
    except: pass
    return False

# ============================= ULTIMATE LOGIN (TARGET BOT STYLE) =============================
def login(driver):
    global driver  # for debug_ss to work

    if load_cookies(driver):
        driver.get(HOME_URL)
        time.sleep(5)
        debug_ss("01_after_cookies")
        if "logout" in driver.page_source.lower():
            return True

    log("Fresh login shuru...")
    driver.get(LOGIN_URL)
    time.sleep(12)
    debug_ss("02_login_page")
    debug_source("02_login_page")

    try:
        # SABSE ZYADA POSSIBLE FIELDS TRY KARO
        username_selectors = "#nick, input[name='nick'], input[name='username'], input[type='text']:first-of-type"
        password_selectors = "input[name='pass'], input[name='password'], input[type='password']"

        username_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, username_selectors))
        )
        password_field = driver.find_element(By.CSS_SELECTOR, password_selectors)

        username_field.clear()
        username_field.send_keys(USERNAME)
        time.sleep(2)
        debug_ss("03_username_filled")

        password_field.clear()
        password_field.send_keys(PASSWORD)
        time.sleep(2)
        debug_ss("04_password_filled")

        # BUTTON CLICK – MULTIPLE WAYS
        button_clicked = False
        for xpath in ["//button[contains(text(),'LOGIN')]", "//button[@type='submit']", "//button"]:
            try:
                btn = driver.find_element(By.XPATH, xpath)
                driver.execute_script("arguments[0].click();", btn)
                log(f"Login button clicked → {xpath}")
                button_clicked = True
                break
            except: continue

        if not button_clicked:
            log("NO BUTTON FOUND!")
            debug_ss("ERROR_no_button")
            return False

        debug_ss("05_submitted")
        time.sleep(15)
        debug_ss("06_after_submit")
        debug_source("06_after_submit")

        if any(x in driver.current_url.lower() for x in ["online_kon", "users", "home"]) and "login" not in driver.current_url.lower():
            log("LOGIN SUCCESSFUL HO GAYA BHAI!")
            save_cookies(driver)
            debug_ss("07_FINAL_SUCCESS")
            return True
        else:
            log("LOGIN FAILED")
            debug_ss("08_FINAL_FAILED")
            return False


    except Exception as e:
        log(f"Login error: {e}")
        debug_ss("09_CRITICAL_ERROR")
        return False

# ============================= SHEETS =============================
# ============================= SHEETS =============================
class Sheets:
    def __init__(self):
        client = gspread.authorize(Credentials.from_service_account_info(
            json.loads(GOOGLE_CREDENTIALS_JSON),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        ))
    def __init__(self):
        client = gspread.authorize(Credentials.from_service_account_info(
            json.loads(GOOGLE_CREDENTIALS_JSON),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        ))
        self.wb = client.open_by_url(SHEET_URL)
        self.profiles = self.ws("ProfilesData", ["IMAGE","NICK NAME","TAGS","LAST POST","LAST POST TIME","FRIEND","CITY","GENDER","MARRIED","AGE","JOINED","FOLLOWERS","STATUS","POSTS","PROFILE LINK","INTRO","SOURCE","DATETIME SCRAP"])
        self.runlist = self.ws("RunList", ["Nickname","Status"])
        self.timing = self.ws("TimingLog", ["Nickname","Timestamp","Source","Run Number"])
        self.dash = self.ws("Dashboard", ["Metric","Value"])

    def ws(self, name, headers):
    def ws(self, name, headers):
        try:
            ws = self.wb.worksheet(name)
            if ws.row_values(1) != headers:
                ws.update('A1', [headers])
            if ws.row_values(1) != headers:
                ws.update('A1', [headers])
        except WorksheetNotFound:
            ws = self.wb.add_worksheet(title=name, rows=5000, cols=len(headers))
            ws = self.wb.add_worksheet(title=name, rows=5000, cols=len(headers))
            ws.append_row(headers)
        return ws

    def write_profile(self, data):
    def write_profile(self, data):
        ws = self.profiles
        nick = data["NICK NAME"].lower()
        rows = ws.get_all_values()
        row_num = next((i+2 for i, r in enumerate(rows[1:]) if len(r)>1 and r[1].lower()==nick), None)
        values = [data.get(c,"") for c in ws.row_values(1)]
        nick = data["NICK NAME"].lower()
        rows = ws.get_all_values()
        row_num = next((i+2 for i, r in enumerate(rows[1:]) if len(r)>1 and r[1].lower()==nick), None)
        values = [data.get(c,"") for c in ws.row_values(1)]
        if row_num:
            ws.update(f"A{row_num}", [values])
            ws.update(f"A{row_num}", [values])
        else:
            ws.append_row(values)
        time.sleep(0.8)
            ws.append_row(values)
        time.sleep(0.8)

    def log_timing(self, nick, source, run):
        self.timing.append_row([nick, pkt_time().strftime("%d-%b-%y %I:%M %p"), source, run])

    def get_pending(self):
        rows = self.runlist.get_all_values()
        return [row[0].strip() for row in rows[1:] if row and row[0].strip() and (len(row)<2 or "pending" in row[1].lower() or "⚡" in row[1])]

# ============================= SCRAPING =============================
def get_online_users(driver):
    log("Online users nikaal rahe hain...")
    driver.get(ONLINE_URL)
    time.sleep(10)
    users = []
    for el in driver.find_elements(By.CSS_SELECTOR, "li.mbl.cl.sp b"):
        n = el.text.strip()
        if n and len(n)>=3: users.append(n)
    log(f"Found {len(users)} online users")
    return users

def scrape_profile(driver, nick):
    url = f"https://damadam.pk/users/{nick}/"
    driver.get(url)
    try:
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        return {
            "IMAGE": "", "NICK NAME": nick, "TAGS": "", "LAST POST": "", "LAST POST TIME": "",
def scrape_profile(driver, nick):
    url = f"https://damadam.pk/users/{nick}/"
    driver.get(url)
    try:
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        return {
            "IMAGE": "", "NICK NAME": nick, "TAGS": "", "LAST POST": "", "LAST POST TIME": "",
            "FRIEND": "", "CITY": "", "GENDER": "", "MARRIED": "", "AGE": "", "JOINED": "",
            "FOLLOWERS": "", "STATUS": "", "POSTS": "", "PROFILE LINK": url.rstrip("/"),
            "INTRO": "", "SOURCE": "Online", "DATETIME SCRAP": pkt_time().strftime("%d-%b-%y %I:%M %p")
            "FOLLOWERS": "", "STATUS": "", "POSTS": "", "PROFILE LINK": url.rstrip("/"),
            "INTRO": "", "SOURCE": "Online", "DATETIME SCRAP": pkt_time().strftime("%d-%b-%y %I:%M %p")
        }
    except: return None

# ============================= MAIN =============================
# ============================= MAIN =============================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["online", "sheet"], default="online")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    print("\n" + "═"*80)
    print(f"DAMADAM MASTER SCRAPER v5.0 → MODE: {args.mode.upper()} | LIMIT: {args.limit or 'UNLIMITED'}")
    print("═"*80 + "\n")

    global driver
    driver = setup_browser()
    if not login(driver):
    if not login(driver):
        driver.quit()
        sys.exit(1)

    sheets = Sheets()
    run_num = len(sheets.dash.get_all_values()) + 1

    if args.mode == "online":
        nicks = get_online_users(driver)
        source = "Online"
    else:
        nicks = sheets.get_pending()
        source = "Sheet"
        if not nicks:
            log("RunList mein koi pending nahi!")
            driver.quit()
            return

    processed = 0
    for i, nick in enumerate(nicks):
        if args.limit and processed >= args.limit: break
        profile = scrape_profile(driver, nick)
        if profile:
            profile["SOURCE"] = source
            profile["SOURCE"] = source
            sheets.write_profile(profile)
            sheets.log_timing(nick, source, run_num)
            sheets.log_timing(nick, source, run_num)
            processed += 1
            log(f"[{processed}] Saved → {nick}")
        else:
            log(f"Failed → {nick}")
        time.sleep(random.uniform(2, 4))

    log("MISSION COMPLETE!")
    driver.quit()

if __name__ == "__main__":
    main()
