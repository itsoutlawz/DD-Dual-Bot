#!/usr/bin/env python3
"""
DamaDam Master Scraper v4.0 – FINAL WORKING VERSION
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
from datetime import datetime, timedelta, timezone

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound

# ============================= CONFIG =============================
USERNAME = os.getenv("DAMADAM_USERNAME")
PASSWORD = os.getenv("DAMADAM_PASSWORD")
HOME_URL = "https://damadam.pk/"
LOGIN_URL = "https://damadam.pk/login/"
ONLINE_URL = "https://damadam.pk/online_kon/"
COOKIE_FILE = "damadam_cookies.pkl"

SHEET_URL = os.getenv('GOOGLE_SHEET_URL')
GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')

# ============================= HELPERS =============================
def pkt_time():
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5)

def log(msg):
    print(f"[{pkt_time().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

# ============================= BROWSER & LOGIN =============================
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
        log("Cookies saved for future runs")
    except: pass

def load_cookies(driver):
    if not os.path.exists(COOKIE_FILE):
        return False
    try:
        driver.get(HOME_URL)
        with open(COOKIE_FILE, "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                if 'expiry' in cookie:
                    del cookie['expiry']
                try:
                    driver.add_cookie(cookie)
                except:
                    pass
        driver.refresh()
        time.sleep(6)
        if "logout" in driver.page_source.lower():
            log("Fast login via cookies!")
            return True
    except Exception as e:
        log(f"Cookie load failed: {e}")
    return False

def login(driver):
    if load_cookies(driver):
        driver.get(HOME_URL)
        time.sleep(5)
        if "logout" in driver.page_source.lower() or "online_kon" in driver.current_url:
            log("Logged in using saved cookies!")
            return True

    log("Logging in with super strong method (Target Bot style)...")
    driver.get(LOGIN_URL)
    time.sleep(10)

    # YEHI HAI ASLI JADU — DONO FORM KO PAKADTA HAI
    try:
        # Pehle purana form try (#nick or name='nick')
        nick_field = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#nick, input[name='nick'], input[name='username']"))
        )
        # Password field ko type=password se pakdo (hamesha kaam karta hai)
        pass_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        
        # Agar naya form hai to username/password use hoga
        nick_field.clear()
        nick_field.send_keys(USERNAME)
        time.sleep(1)
        
        pass_field.clear()
        pass_field.send_keys(PASSWORD)
        time.sleep(1)

        # Button ko multiple ways se click
        try:
            btn = driver.find_element(By.XPATH, "//button[contains(text(), 'LOGIN')]")
        except:
            btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        
        driver.execute_script("arguments[0].click();", btn)
        
        log("Login submitted, waiting for redirect...")
        time.sleep(12)

        # Success check (multiple conditions)
        current_url = driver.current_url.lower()
        page_source = driver.page_source.lower()

        if ("logout" in page_source or 
            "online_kon" in current_url or 
            "damadam.pk/" in current_url and "login" not in current_url):
            log("LOGIN 100% SUCCESSFUL (Target Bot Method)!")
            save_cookies(driver)
            return True
        else:
            log("Login failed - still on login page")
            driver.save_screenshot("login_failed_final.png")
            return False

    except Exception as e:
        log(f"Login critical error: {e}")
        driver.save_screenshot("login_critical_error.png")
        return False

# ============================= SHEETS =============================
class Sheets:
    def __init__(self):
        client = gspread.authorize(Credentials.from_service_account_info(
            json.loads(GOOGLE_CREDENTIALS_JSON),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        ))
        self.wb = client.open_by_url(SHEET_URL)
        self.profiles = self.ws("ProfilesData", ["IMAGE","NICK NAME","TAGS","LAST POST","LAST POST TIME","FRIEND","CITY","GENDER","MARRIED","AGE","JOINED","FOLLOWERS","STATUS","POSTS","PROFILE LINK","INTRO","SOURCE","DATETIME SCRAP"])
        self.runlist = self.ws("RunList", ["Nickname","Status","Note"])
        self.timing = self.ws("TimingLog", ["Nickname","Timestamp","Source","Run Number"])
        self.dash = self.ws("Dashboard", ["Metric","Value"])

    def ws(self, name, headers):
        try:
            ws = self.wb.worksheet(name)
            if ws.row_values(1) != headers:
                ws.update('A1', [headers])
        except WorksheetNotFound:
            ws = self.wb.add_worksheet(title=name, rows=5000, cols=len(headers))
            ws.append_row(headers)
        return ws

    def write_profile(self, data):
        ws = self.profiles
        nick = data["NICK NAME"].lower()
        rows = ws.get_all_values()
        row_num = next((i+2 for i, r in enumerate(rows[1:]) if len(r)>1 and r[1].lower()==nick), None)
        values = [data.get(c,"") for c in ws.row_values(1)]
        if row_num:
            ws.update(f"A{row_num}", [values])
        else:
            ws.append_row(values)
        time.sleep(0.8)

    def log_timing(self, nick, source, run):
        self.timing.append_row([nick, pkt_time().strftime("%d-%b-%y %I:%M %p"), source, run])

    def get_pending_sheet(self):
        rows = self.runlist.get_all_values()
        pending = []
        for i, row in enumerate(rows[1:], 2):
            if len(row)>0 and row[0].strip():
                status = row[1].strip().lower() if len(row)>1 else ""
                if status in ["", "pending"]:
                    pending.append({"nick": row[0].strip(), "row": i})
        return pending

# ============================= SCRAPING =============================
def get_online_users(driver):
    log("Fetching online users...")
    driver.get(ONLINE_URL)
    time.sleep(8)
    users = []
    for el in driver.find_elements(By.CSS_SELECTOR, "li.mbl.cl.sp b"):
        n = el.text.strip()
        if n and len(n)>=3 and any(c.isalpha() for c in n):
            users.append(n)
    log(f"Found {len(users)} online users")
    return users

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
        }
    except:
        return None

# ============================= MAIN =============================
def main():
    parser = argparse.ArgumentParser(description="DamaDam Master Scraper")
    parser.add_argument("--mode", choices=["online", "sheet"], default="online", help="online = live users, sheet = from RunList")
    parser.add_argument("--limit", type=int, default=0, help="Max profiles to scrape (0 = unlimited)")
    args = parser.parse_args()

    print("\n" + "═"*80)
    print(f"DAMADAM MASTER SCRAPER v4.0 → MODE: {args.mode.upper()} | LIMIT: {args.limit or 'UNLIMITED'}")
    print("═"*80 + "\n")

    driver = setup_browser()
    if not login(driver):
        driver.quit()
        sys.exit(1)

    sheets = Sheets()
    run_num = len(sheets.dash.get_all_values()) + 1

    if args.mode == "online":
        nicks = get_online_users(driver)
        source = "Online"
    else:
        targets = sheets.get_pending_sheet()
        if not targets:
            log("No pending nicknames in RunList sheet!")
            driver.quit()
            return
        nicks = [t["nick"] for t in targets]
        source = "Sheet"
        log(f"Found {len(nicks)} pending in RunList")

    processed = 0
    for i, nick in enumerate(nicks):
        if args.limit and processed >= args.limit:
            break
        profile = scrape_profile(driver, nick)
        if profile:
            profile["SOURCE"] = source
            sheets.write_profile(profile)
            sheets.log_timing(nick, source, run_num)
            processed += 1
            log(f"[{processed}] SAVED → {nick}")
        else:
            log(f"[{i+1}] FAILED → {nick}")
        time.sleep(random.uniform(1.8, 3.2))

    sheets.dash.append_row(["Last Run", pkt_time().strftime("%d-%b-%y %I:%M %p")])
    sheets.dash.append_row(["Mode", args.mode.title()])
    sheets.dash.append_row(["Processed", processed])
    sheets.dash.append_row(["Run Number", run_num])

    log("RUN COMPLETED SUCCESSFULLY!")
    driver.quit()

if __name__ == "__main__":
    main()
