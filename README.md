# DamaDam Master Scraper v6

Yeh scraper Damadam.pk ka Online Users aur Profiles scrape karta hai.
Google Sheets par data save kar sakta hai. Windows + GitHub Codespace
dono per fully compatible hai.

## Run on Windows
python Scraper.py --mode online

## Run inside GitHub Codespace
python3 Scraper.py --mode online

## Modes
--mode online  → Online page se users scrap
--mode sheet   → Sheet se users scrap

## Requirements Install
pip install -r requirements.txt

## Automation (GitHub Actions)
Workflow har 1 ghanta Scraper.py ko run karega.
