#!/usr/bin/env python3
"""
宝可梦卡价追踪器 —— GitHub Actions 版

由 .github/workflows/update.yml 每天自动运行：
  读取 watchlist.json → 从 Pokémon TCG API 抓取价格 → 追加到 docs/data.json（网页读取它）
  触发提醒时写出 alerts.md，工作流会据此创建一个 GitHub Issue 通知你。

也可以手动运行：
  python tracker.py update
  python tracker.py add base1-4 [跌到多少提醒] [涨到多少提醒]
  python tracker.py remove base1-4
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
WATCH_PATH = os.path.join(ROOT, "watchlist.json")
DATA_PATH = os.path.join(ROOT, "docs", "data.json")
ALERT_PATH = os.path.join(ROOT, "alerts.md")
API_BASE = "https://api.pokemontcg.io/v2"
VARIANT_ORDER = ["1stEditionHolofoil", "holofoil", "1stEdition", "unlimitedHolofoil",
                 "reverseHolofoil", "normal", "unlimited", "1stEditionNormal"]


def api_get(path, retries=4):
    headers = {"User-Agent": "pokeprice-tracker/2.0"}
    if os.environ.get("POKEMONTCG_API_KEY"):
        headers["X-Api-Key"] = os.environ["POKEMONTCG_API_KEY"]
    url = f"{API_BASE}/{path}"
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"{url}: {e}")
            time.sleep(3 * (attempt + 1))


def fetch_card(card_id):
    return api_get("cards/" + urllib.parse.quote(card_id))["data"]


def extract_prices(card):
    """返回 {系列名: (价格, 货币)}；TCGplayer 按版本分开，Cardmarket 取趋势价。"""
    out = {}
    for variant, p in ((card.get("tcgplayer") or {}).get("prices") or {}).items():
        v = p.get("market") or p.get("mid")
        if v is not None:
            out[variant] = (round(v, 2), "USD")
    cm = (card.get("cardmarket") or {}).get("prices") or {}
    if cm.get("trendPrice") is not None:
        out["Cardmarket"] = (round(cm["trendPrice"], 2), "EUR")
    return out


def main_key(series):
    for v in VARIANT_ORDER:
        if v in series:
            return v
    keys = [k for k in series if k != "Cardmarket"]
    return keys[0] if keys else ("Cardmarket" if "Cardmarket" in series else None)


def money(v, cur):
    return f"{'€' if cur == 'EUR' else '$'}{v:,.2f}"


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def num(s):
    s = (s or "").strip()
    return float(s) if s else None


def update(watch, data):
    today = date.today().isoformat()
    alerts, errors = [], []
    for w in watch:
        cid = w["card_id"]
        try:
            card = fetch_card(cid)
        except RuntimeError as e:
            errors.append(f"{cid}: {e}")
            print("获取失败", cid, e)
            continue
        entry = data["cards"].setdefault(cid, {"series": {}})
        entry.update(name=card["name"], set_name=card["set"]["name"], number=card["number"],
                     image=(card.get("images") or {}).get("small"),
                     url=(card.get("tcgplayer") or {}).get("url"))
        for key, (price, cur) in extract_prices(card).items():
            s = entry["series"].setdefault(key, {"currency": cur, "points": []})
            pts = [p for p in s["points"] if p[0] != today]  # 同一天重复运行只保留最新
            pts.append([today, price])
            s["points"] = sorted(pts)
        k = main_key(entry["series"])
        entry["main"] = k
        if k:
            price, cur = entry["series"][k]["points"][-1][1], entry["series"][k]["currency"]
            print(f"{card['name']:<28}{k:<20}{money(price, cur)}")
            if w.get("below") is not None and price <= w["below"]:
                alerts.append(f"- 📉 **{card['name']}**（{card['set']['name']} #{card['number']}）跌到 {money(price, cur)}，提醒线 ≤ {w['below']}")
            if w.get("above") is not None and price >= w["above"]:
                alerts.append(f"- 📈 **{card['name']}**（{card['set']['name']} #{card['number']}）涨到 {money(price, cur)}，提醒线 ≥ {w['above']}")
        time.sleep(0.3)
    data["updated"] = datetime.now(timezone.utc).isoformat(timespec="minutes")
    data["errors"] = errors
    return alerts


def main():
    args = sys.argv[1:]
    # 在 GitHub Actions 里通过环境变量传入（来自"手动运行"表单）
    action = os.environ.get("ACTION", "").strip()
    if not args and action:
        mapping = {"更新价格": "update", "关注卡牌": "add", "取消关注": "remove"}
        args = [mapping.get(action, "update")]
        if args[0] != "update":
            args += [os.environ.get("CARD_ID", ""), os.environ.get("BELOW", ""), os.environ.get("ABOVE", "")]
    cmd = args[0] if args else "update"

    watch = load(WATCH_PATH, [])
    data = load(DATA_PATH, {"cards": {}})
    data.setdefault("cards", {})
    if os.environ.get("GITHUB_REPOSITORY"):
        data["repo"] = os.environ["GITHUB_REPOSITORY"]

    if cmd in ("add", "remove"):
        cid = (args[1] if len(args) > 1 else "").strip()
        if not cid:
            sys.exit("请填写卡牌 ID，例如 base1-4")
        watch = [w for w in watch if w["card_id"] != cid]
        if cmd == "add":
            watch.append({"card_id": cid,
                          "below": num(args[2]) if len(args) > 2 else None,
                          "above": num(args[3]) if len(args) > 3 else None})
            print("已关注", cid)
        else:
            print("已取消关注", cid)
        save(WATCH_PATH, watch)

    alerts = update(watch, data) if watch else []
    data["watchlist"] = watch
    save(DATA_PATH, data)

    if os.path.exists(ALERT_PATH):
        os.remove(ALERT_PATH)
    if alerts:
        with open(ALERT_PATH, "w", encoding="utf-8") as f:
            f.write("今天有卡价触发了你设置的提醒：\n\n" + "\n".join(alerts) + "\n")
        print("\n".join(alerts))


if __name__ == "__main__":
    main()
