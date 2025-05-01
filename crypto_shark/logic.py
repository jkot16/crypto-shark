
import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import praw
import tweepy


BASE_DIR    = Path(__file__).resolve().parent.parent
CONFIG      = BASE_DIR / "config.json"
STATE_FILE  = BASE_DIR / "state.json"
CACHE_FILE  = BASE_DIR / "coins_cache.json"
LOG_FILE    = BASE_DIR / "logs.txt"


ALIASES = {
    "bitcoin":   ["bitcoin", "btc"],
    "ethereum":  ["ethereum", "eth"],
    "ripple":    ["ripple", "xrp"],
    "solana":    ["solana", "sol"],
    "chainlink": ["chainlink", "link"],

}

class CryptoWatcherLogic:
    def __init__(self):
        super().__init__()
        load_dotenv()

        cfg = self._load_json(CONFIG)
        th  = cfg.get("thresholds", {})
        self.th_pct  = th.get("pct", 3.0)
        self.th_sent = th.get("sentiment", 0.6)

        self.config_path = CONFIG
        self.state_path  = STATE_FILE
        self.state       = self._load_json(self.state_path) or {}

        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if not self.webhook_url:
            raise RuntimeError("DISCORD_WEBHOOK_URL not set")

        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT")
        )

        bearer = os.getenv("TWITTER_BEARER_TOKEN")
        if not bearer:
            raise RuntimeError("TWITTER_BEARER_TOKEN not set")
        self.twitter = tweepy.Client(bearer_token=bearer, wait_on_rate_limit=False)

        self._pipeline = None

    def _load_json(self, path: Path):
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def _save_json(self, data, path: Path):
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_prices_batch(self, coins):
        ids = ",".join(coins)
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": ids, "vs_currencies": "usd"},
            timeout=10
        )
        data = resp.json()
        return {c: data.get(c, {}).get("usd", 0.0) for c in coins}

    def get_comments(self, subreddit="CryptoCurrency", limit=200):
        return [c.body for c in self.reddit.subreddit(subreddit).comments(limit=limit)]

    def get_tweets(self, query: str, max_results: int = 50):
        try:
            resp = self.twitter.search_recent_tweets(
                query=query, tweet_fields=["lang"], max_results=max_results
            )
        except tweepy.TooManyRequests:
            print("RATE LIMIT HIT FOR TWITTER – skipping tweets this run")
            return []
        except Exception as e:
            print(f"Twitter error: {e} – skipping tweets this run")
            return []

        return [t.text for t in (resp.data or []) if t.lang == "en"]

    def analyze_sentiment(self, texts):

        texts = [t[:2000] for t in texts]

        if not self._pipeline:
            from transformers import pipeline as hf_pipeline
            self._pipeline = hf_pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                device=-1  # CPU
            )


        return self._pipeline(
            texts,
            batch_size=16,
            truncation=True,
            max_length=512
        )
    def send_discord_embed(self, coin, price, pct, pct_pos, pct_neg, count_msgs, image_url):
        if pct is None:
            color = 0x808080
        elif pct > 0:
            color = 0x2ecc71
        else:
            color = 0xe74c3c

        embed = {
            "title": f"🚨 ALERT {coin.upper()} 🚨",
            "thumbnail": {"url": image_url},
            "color": color,
            "fields": [
                {"name": "Price",      "value": f"${price:.2f}",   "inline": True},
                {"name": "Change",     "value": f"{pct:+.2f}%",     "inline": True},
                {"name": "% Positive", "value": f"{pct_pos:.0%}",   "inline": True},
                {"name": "% Negative", "value": f"{pct_neg:.0%}",   "inline": True},
                {"name": "Messages",   "value": str(count_msgs),    "inline": True},
            ],
            "footer": {"text": datetime.utcnow().strftime("Timestamp: %Y-%m-%d %H:%M:%S")}
        }
        payload = {"username": "CryptoWatcherBot", "embeds": [embed]}
        requests.post(self.webhook_url, json=payload, timeout=5).raise_for_status()

    def run_checks(self):
        cfg     = self._load_json(self.config_path) or {}
        tickers = cfg.get("tickers", [])
        messages = []

        reddit_texts  = self.get_comments(limit=1000)
        query         = " OR ".join(f"#{c}" for c in tickers) + " -is:retweet lang:en"
        twitter_texts = self.get_tweets(query=query, max_results=100)
        all_texts     = reddit_texts + twitter_texts

        try:
            prices = self.get_prices_batch(tickers)
        except Exception as e:
            return [f"Error fetching prices: {e}"]

        for coin in tickers:
            price = prices.get(coin, 0.0)
            prev  = self.state.get(coin, {}).get("last_price")
            pct   = ((price - prev) / prev * 100) if prev else None

            aliases    = ALIASES.get(coin, [coin])
            coin_texts = [t for t in all_texts if any(a.lower() in t.lower() for a in aliases)]
            count_msgs = len(coin_texts)

            if coin_texts:
                results  = self.analyze_sentiment(coin_texts)
                total    = len(results)
                pos_list = [r for r in results if r["label"] == "POSITIVE"]
                neg_list = [r for r in results if r["label"] == "NEGATIVE"]
                pct_pos  = len(pos_list)/total if total else 0.0
                pct_neg  = len(neg_list)/total if total else 0.0
            else:
                pct_pos = pct_neg = 0.0

            line = f"{coin.upper()}: ${price:.2f}"
            if pct is not None:
                line += f" ({pct:+.2f}%)"
            line += f" | POS {pct_pos:.0%} | NEG {pct_neg:.0%}"
            messages.append(line)

            cache = self._load_json(CACHE_FILE)
            obj   = next((c for c in cache if c["id"] == coin), {})
            img   = obj.get("image", "")

            alert_flag = 0
            if pct is not None and abs(pct) >= self.th_pct and pct_neg >= self.th_sent:
                self.send_discord_embed(coin, price, pct, pct_pos, pct_neg, count_msgs, img)
                messages.append(f"[ALERT SENT] {coin.upper()}")
                alert_flag = 1

            self.state[coin] = {"last_price": price}

            with LOG_FILE.open("a", encoding="utf-8") as lf:
                lf.write(
                    f"{datetime.utcnow().isoformat()}  "
                    f"{coin}  "
                    f"{price:.2f}  "
                    f"{pct or 0:+.2f}%  "
                    f"{pct_pos:.0%}  "
                    f"{pct_neg:.0%}  "
                    f"{alert_flag}\n"
                )

        self._save_json(self.state, self.state_path)
        return messages
