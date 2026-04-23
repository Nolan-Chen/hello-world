#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import json
import sys
import urllib.parse
import urllib.request


TENCENT_QUOTE_API = "https://qt.gtimg.cn/q="
EASTMONEY_LIST_API = "https://push2.eastmoney.com/api/qt/clist/get"


def normalize_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if not s:
        return s

    if s.endswith(".SS"):
        return f"sh{s[:-3]}"
    if s.endswith(".SZ"):
        return f"sz{s[:-3]}"
    if s.endswith(".BJ"):
        return f"bj{s[:-3]}"
    if s.endswith(".HK"):
        numeric = "".join(ch for ch in s[:-3] if ch.isdigit())
        return f"hk{numeric.zfill(5)}"

    if s.startswith(("SH", "SZ", "BJ", "HK", "US")):
        return s.lower()
    return f"us{s}"


def to_a_share_symbols(code: str) -> tuple[str, str] | None:
    if code.startswith(("6", "5", "9")):
        return f"sh{code}", f"{code}.SS"
    if code.startswith(("0", "3")):
        return f"sz{code}", f"{code}.SZ"
    if code.startswith(("4", "8")):
        return f"bj{code}", f"{code}.BJ"
    return None


def split_chunks(items: list[str], chunk_size: int) -> list[list[str]]:
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def parse_tencent_payload(raw: str) -> list[dict]:
    results: list[dict] = []
    for line in raw.split(";"):
        line = line.strip()
        if not line or "=" not in line:
            continue
        left, right = line.split("=", 1)
        api_symbol = left.replace("v_", "", 1).lower()
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
                "apiSymbol": api_symbol,
                "symbol": api_symbol.upper(),
                "shortName": name,
                "regularMarketPrice": price,
                "regularMarketChangePercent": change_pct,
                "currency": currency,
                "marketState": timestamp,
            }
        )
    return results


def fetch_quotes_by_api_symbols(api_symbols: list[str], batch_size: int) -> list[dict]:
    all_results: list[dict] = []
    for chunk in split_chunks(api_symbols, batch_size):
        url = f"{TENCENT_QUOTE_API}{','.join(chunk)}"
        req = urllib.request.Request(
            url=url,
            headers={
                "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36",
                "Referer": "https://gu.qq.com/",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("gbk", errors="replace")
        all_results.extend(parse_tencent_payload(raw))
    return all_results


def fetch_quotes(symbols: list[str], batch_size: int) -> list[dict]:
    api_symbols = [normalize_symbol(s) for s in symbols]
    display_map = {normalize_symbol(s): s.strip().upper() for s in symbols}
    results = fetch_quotes_by_api_symbols(api_symbols, batch_size)
    for quote in results:
        quote["symbol"] = display_map.get(quote["apiSymbol"], quote["symbol"])
    return results


def fetch_all_a_share_meta(include_bj: bool) -> list[dict]:
    fs = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
    if include_bj:
        fs = f"{fs},m:0+t:81,m:1+t:81"

    page = 1
    page_size = 500
    metas: list[dict] = []
    total = None

    while total is None or len(metas) < total:
        params = {
            "pn": str(page),
            "pz": str(page_size),
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": fs,
            "fields": "f12,f14",
        }
        url = f"{EASTMONEY_LIST_API}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        data = payload.get("data") or {}
        if total is None:
            total = int(data.get("total") or 0)
        diff = data.get("diff") or []
        if not diff:
            break

        for item in diff:
            code = str(item.get("f12") or "").strip()
            name = str(item.get("f14") or "-").strip() or "-"
            converted = to_a_share_symbols(code)
            if not converted:
                continue
            api_symbol, display_symbol = converted
            metas.append(
                {
                    "apiSymbol": api_symbol,
                    "symbol": display_symbol,
                    "shortName": name,
                }
            )
        page += 1

    return metas


def write_csv(path: str, quotes: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "name", "price", "change_pct", "currency", "state"])
        for q in quotes:
            writer.writerow(
                [
                    q.get("symbol", "-"),
                    q.get("shortName", "-"),
                    q.get("regularMarketPrice", ""),
                    q.get("regularMarketChangePercent", ""),
                    q.get("currency", "-"),
                    q.get("marketState", "-"),
                ]
            )


def write_json(path: str, quotes: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(quotes, f, ensure_ascii=False, indent=2)


def pretty_print_quotes(quotes: list[dict], limit: int = 0) -> None:
    now = dt.datetime.now().isoformat(timespec="seconds")
    print(f"获取时间: {now}")
    print(f"行情数量: {len(quotes)}")

    to_show = quotes if limit <= 0 else quotes[:limit]
    print("-" * 106)
    print(
        f"{'代码':<14} {'名称':<24} {'价格':>12} {'涨跌幅%':>10} {'货币':>8} {'状态':>19}"
    )
    print("-" * 106)
    for quote in to_show:
        symbol = str(quote.get("symbol", "-"))[:14]
        name = str(quote.get("shortName", "-"))[:24]
        price = quote.get("regularMarketPrice")
        change_pct = quote.get("regularMarketChangePercent")
        currency = str(quote.get("currency", "-"))[:8]
        state = str(quote.get("marketState", "-"))[:19]
        price_text = f"{price:.4f}" if isinstance(price, (float, int)) else "-"
        change_text = (
            f"{change_pct:+.2f}" if isinstance(change_pct, (float, int)) else "-"
        )
        print(
            f"{symbol:<14} {name:<24} {price_text:>12} {change_text:>10} {currency:>8} {state:>19}"
        )
    print("-" * 106)
    if limit > 0 and len(quotes) > limit:
        print(f"仅展示前 {limit} 条；可通过 --sample 调整。")


def main() -> int:
    parser = argparse.ArgumentParser(description="获取股票实时行情（腾讯行情接口）")
    parser.add_argument(
        "--symbols",
        default="AAPL,MSFT,TSLA",
        help="股票代码，逗号分隔。例如: AAPL,MSFT,0700.HK,600519.SS",
    )
    parser.add_argument(
        "--all-a-share",
        action="store_true",
        help="抓取全市场 A 股（默认沪深；配合 --include-bj 可含北交所）",
    )
    parser.add_argument(
        "--include-bj",
        action="store_true",
        help="在 --all-a-share 模式下加入北交所股票",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=80,
        help="分批请求数量，默认 80",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=20,
        help="终端展示条数（0 表示全部展示），默认 20",
    )
    parser.add_argument(
        "--output-csv",
        default="",
        help="输出 CSV 文件路径，例如 a_share_quotes.csv",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="输出 JSON 文件路径，例如 a_share_quotes.json",
    )
    args = parser.parse_args()

    if args.batch_size <= 0:
        print("错误: --batch-size 必须大于 0。", file=sys.stderr)
        return 2

    try:
        if args.all_a_share:
            print("正在拉取全市场 A 股代码列表...")
            metas = fetch_all_a_share_meta(include_bj=args.include_bj)
            if not metas:
                print("未拉取到 A 股代码列表。", file=sys.stderr)
                return 1

            api_symbols = [m["apiSymbol"] for m in metas]
            print(f"共获取股票代码: {len(api_symbols)}，正在分批拉取行情...")
            raw_quotes = fetch_quotes_by_api_symbols(api_symbols, args.batch_size)

            quote_map = {q["apiSymbol"]: q for q in raw_quotes}
            quotes: list[dict] = []
            for meta in metas:
                quote = quote_map.get(meta["apiSymbol"])
                if not quote:
                    continue
                quote["symbol"] = meta["symbol"]
                if quote.get("shortName") in ("", "-", None):
                    quote["shortName"] = meta["shortName"]
                quotes.append(quote)
        else:
            symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
            if not symbols:
                print("错误: 请输入至少一个股票代码。", file=sys.stderr)
                return 2
            quotes = fetch_quotes(symbols, args.batch_size)
    except Exception as exc:
        print(f"请求失败: {exc}", file=sys.stderr)
        return 1

    if not quotes:
        print("未获取到任何行情数据，请检查股票代码或网络。", file=sys.stderr)
        return 1

    pretty_print_quotes(quotes, limit=args.sample)

    if args.output_csv:
        write_csv(args.output_csv, quotes)
        print(f"已写入 CSV: {args.output_csv}")

    if args.output_json:
        write_json(args.output_json, quotes)
        print(f"已写入 JSON: {args.output_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
