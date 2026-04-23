#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import sys
import urllib.parse
import urllib.request


YAHOO_QUOTE_API = "https://query1.finance.yahoo.com/v7/finance/quote"


def fetch_quotes(symbols: list[str]) -> list[dict]:
    params = urllib.parse.urlencode({"symbols": ",".join(symbols)})
    url = f"{YAHOO_QUOTE_API}?{params}"
    req = urllib.request.Request(
        url=url,
        headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36",
            "Accept": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("quoteResponse", {}).get("result", [])


def pretty_print_quotes(quotes: list[dict]) -> None:
    now = dt.datetime.now().isoformat(timespec="seconds")
    print(f"获取时间: {now}")
    print("-" * 88)
    print(
        f"{'代码':<14} {'名称':<24} {'价格':>12} {'涨跌幅%':>10} {'货币':>8} {'状态':>8}"
    )
    print("-" * 88)
    for quote in quotes:
        symbol = str(quote.get("symbol", "-"))[:14]
        name = str(quote.get("shortName", "-"))[:24]
        price = quote.get("regularMarketPrice")
        change_pct = quote.get("regularMarketChangePercent")
        currency = str(quote.get("currency", "-"))[:8]
        state = str(quote.get("marketState", "-"))[:8]
        price_text = f"{price:.4f}" if isinstance(price, (float, int)) else "-"
        change_text = (
            f"{change_pct:+.2f}" if isinstance(change_pct, (float, int)) else "-"
        )
        print(
            f"{symbol:<14} {name:<24} {price_text:>12} {change_text:>10} {currency:>8} {state:>8}"
        )
    print("-" * 88)


def main() -> int:
    parser = argparse.ArgumentParser(description="获取股票实时行情（Yahoo Finance）")
    parser.add_argument(
        "--symbols",
        default="AAPL,MSFT,TSLA",
        help="股票代码，逗号分隔。例如: AAPL,MSFT,0700.HK,600519.SS",
    )
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        print("错误: 请输入至少一个股票代码。", file=sys.stderr)
        return 2

    try:
        quotes = fetch_quotes(symbols)
    except Exception as exc:
        print(f"请求失败: {exc}", file=sys.stderr)
        return 1

    if not quotes:
        print("未获取到任何行情数据，请检查股票代码或网络。", file=sys.stderr)
        return 1

    pretty_print_quotes(quotes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
