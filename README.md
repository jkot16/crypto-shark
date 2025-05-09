## CryptoShark

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

![CryptoShark GUI Preview](https://github.com/user-attachments/assets/dc58565b-148c-40a8-bd33-23d460fc651f)

---

## Table of Contents

1. [🔎 Project Overview](#1-project-overview)  
2. [🛠️ Features](#2-features)  
3. [⚙️ Tech Stack](#3-tech-stack)  
4. [📦 Installation & Usage](#4-installation--usage)  
5. [📈 Monitoring & Alerts](#5-monitoring--alerts)  
6. [🗺️ Roadmap](#6-roadmap)

---

## 1. Project Overview

**CryptoShark** is a smart, AI-powered crypto tracker that goes beyond just prices.  
It watches real-time market data, analyzes hundreds of Reddit and Twitter posts using a powerful AI language model from Hugging Face, and sends alerts to Discord when it detects real market momentum.

Whether you're a trader, analyst, or just crypto-curious – CryptoShark helps you catch the moves that matter by combining price action with actual community sentiment.

> 🧠 Powered by `distilbert-base-uncased-finetuned-sst-2-english` – a transformer model for real-time crypto mood detection.

---

## 2. Features

- **Live price tracking** via CoinGecko  
- **Sentiment analysis** with Hugging Face Transformers  
- **Reddit + Twitter integration** via PRAW & Tweepy  
- **Discord alerts** with rich embeds when price and sentiment thresholds are hit  
- **Stylish GUI** built with PySide6 + QSS (dark theme)  
- **Watchlist management** with top-100 coin support, logos & dominance stats  
- **Log history viewer** with sortable table of past checks  
- **Local state, caching & logs** in JSON  
- **Cron-based background checks** via CLI & shell
  
![CryptoShark GUI Add](https://github.com/user-attachments/assets/1aab7e50-81ee-4027-8b06-9e9040eb2d7b)
---

## 3. Tech Stack

| Component         | Technology                                  |
|------------------|---------------------------------------------|
| Language          | Python 3.8+                                 |
| GUI               | PySide6 (Qt6)                               |
| APIs              | CoinGecko, Reddit (PRAW), Twitter (Tweepy)  |
| AI/NLP            | HuggingFace Transformers (DistilBERT)       |
| Sentiment Model   | `distilbert-base-uncased-finetuned-sst-2-english` |
| Config            | `.env` + `dotenv`                           |
| Scheduling        | Bash + cron                                 |
| Persistence       | JSON files (`state.json`, `config.json`)    |
| Alerts            | Discord Webhooks                            |

---

## 4. Installation & Usage

```bash
git clone https://github.com/jkot16/crypto-shark.git
cd crypto-shark

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

🔐 Environment Configuration (.env)

Before using the app, create a .env file in the project root and add your API keys:
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

TWITTER_BEARER_TOKEN=YOUR_TWITTER_BEARER_TOKEN

REDDIT_CLIENT_ID=YOUR_REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET=YOUR_REDDIT_CLIENT_SECRET
REDDIT_USER_AGENT=crypto-watcher
```
⚠️ This file is required to fetch data and send alerts.

Run GUI mode:
```bash
python -m crypto_shark.gui
```

Run background check (no GUI):
```bash
python check_crypto.py
```

Schedule checks (eg., every 10 minutes)
```bash
bash setup_cron.sh 10
```

⚙️ config.json & Generated Files

When you run CryptoShark for the first time, it auto-creates:

- config.json – coins to track and alert thresholds
  - pct → minimum % price change to trigger alert
  - sentiment → minimum % of negative mood in posts to trigger alert
- state.json – stores last known prices
- coins_cache.json – top-100 coins (CoinGecko)
- logs.txt – alert history
- Example config.json:
```json
{
  "tickers": ["bitcoin", "ethereum"],
  "thresholds": {
    "pct": 3.0,
    "sentiment": 0.6
  }
}

```
Set both thresholds to 0.0 to get notified on every scan.

--- 
## 5. Monitoring & Alerts
CryptoShark performs scheduled scans using CoinGecko + NLP pipeline.

What happens:
- Fetch current prices
- Scrape Reddit comments + recent tweets for watched coins
- Use Hugging Face sentiment model to classify messages
- Trigger Discord alert when:
  - Price change ≥ configured %
  - AND negative sentiment ≥ threshold
- Logs saved to logs.txt and viewable in the GUI.


![CryptoShark GUI Discord](https://github.com/user-attachments/assets/7940a5fa-72ed-4e40-9a6e-bd9d3dfb6164)
![CryptoShark GUI Logs](https://github.com/user-attachments/assets/ef366870-fbaa-4883-9d6c-8cedc1288756)

## 6. Roadmap
For more upcoming features and tracked improvements, see:

👉 [GitHub Issues for CryptoShark](https://github.com/jkot16/crypto-shark/issues)  
