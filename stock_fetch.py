#!/usr/bin/env python3
import argparse
import datetime as dt
import sys
import urllib.request


TENCENT_QUOTE_API = "https://qt.gtimg.cn/q="


def normalize_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if not s:
        return s

    if s.endswith(".SS"):
        return f"sh{s[:-3]}"
    if s.endswith(".SZ"):
        return f"sz{s[:-3]}"
    if s.endswith(".HK"):
        numeric = "".join(ch for ch in s[:-3] if ch.isdigit())
        return f"hk{numeric.zfill(5)}"

    # Default US symbols.
    if s.startswith(("SH", "SZ", "HK", "US")):
        return s.lower()
    return f"us{s}"


def fetch_quotes(symbols: list[str]) -> list[dict]:
    api_symbols = [normalize_symbol(s) for s in symbols]
    url = f"{TENCENT_QUOTE_API}{','.join(api_symbols)}"
    req = urllib.request.Request(
        url=url,
        headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36",
            "Referer": "https://gu.qq.com/",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("gbk", errors="replace")

    results: list[dict] = []
    for line in raw.split(";"):
        line = line.strip()
        if not line or "=" not in line:
            continue
        left, right = line.split("=", 1)
        symbol = left.replace("v_", "", 1)
        quote_str = right.strip().strip('"')
        if not quote_str:
            continue
        parts = quote_str.split("~")
        if len(parts) < 4:
            continue

        name = parts[1] if len(parts) > 1 else "-"
        last_price_text = parts[3] if len(parts) > 3 else ""
        prev_close_text = parts[4] if len(parts) > 4 else ""
        timestamp = parts[30] if len(parts) > 30 else "-"
        currency = "-"
        for idx in (35, 75, 82):
            if len(parts) > idx and parts[idx].isalpha():
                currency = parts[idx]
                break

        try:
            price = float(last_price_text)
        except (TypeError, ValueError):
            price = None

        try:
            prev_close = float(prev_close_text)
        except (TypeError, ValueError):
            prev_close = None

        change_pct = None
        if price is not None and prev_close not in (None, 0):
            change_pct = ((price - prev_close) / prev_close) * 100

        results.append(
            {
                "symbol": symbol.upper(),
                "shortName": name,
                "regularMarketPrice": price,
                "regularMarketChangePercent": change_pct,
                "currency": currency,
                "marketState": timestamp,
            }
        )

    return results


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
    parser = argparse.ArgumentParser(description="获取股票实时行情（腾讯行情接口）")
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
