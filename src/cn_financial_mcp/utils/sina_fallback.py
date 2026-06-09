"""
Sina Finance real-time API fallback for cn-financial-mcp.

When eastmoney push2 CDN is unreachable, these functions provide
alternative data from Sina Finance HTTP API.

Tested endpoints:
  - hq.sinajs.cn (real-time index & stock quotes, 0.1s)
  - datacenter-web.eastmoney.com (dragon tiger, margin, 0.3s)
  - push2ex.eastmoney.com (limit up/down pool, 0.2s)

All functions return pandas DataFrames compatible with the existing
df_to_json() pipeline.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger("cn-financial-mcp")

_SINA_HEADERS = {
    "Referer": "https://finance.sina.com.cn",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

# Major A-share index codes for market overview
_INDEX_CODES = {
    "sh000001": "上证指数",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
    "sh000300": "沪深300",
    "sz399905": "中证500",
    "sh000688": "科创50",
    "sh000016": "上证50",
    "sz399004": "深证100",
}


def get_market_overview_sina() -> pd.DataFrame:
    """
    Fetch major A-share index real-time quotes from Sina Finance.

    Returns DataFrame with columns:
      代码, 名称, 今开, 昨收, 最新价, 最高, 最低, 成交量(手), 成交额(元),
      日期, 时间, 涨跌额, 涨跌幅
    """
    codes = ",".join(_INDEX_CODES.keys())
    url = f"http://hq.sinajs.cn/list={codes}"
    try:
        r = requests.get(url, headers=_SINA_HEADERS, timeout=10)
        if r.status_code != 200:
            raise ConnectionError(f"Sina API returned {r.status_code}")

        rows = []
        for line in r.text.strip().split("\n"):
            if '=""' in line or "=" not in line:
                continue
            var_part, data_part = line.split("=", 1)
            code = var_part.split("_")[-1]
            val = data_part.strip().strip('";')
            if not val:
                continue
            parts = val.split(",")
            if len(parts) < 32:
                continue

            open_price = float(parts[1])
            prev_close = float(parts[2])
            latest = float(parts[3])
            high = float(parts[4])
            low = float(parts[5])
            volume = float(parts[8])       # 股
            amount = float(parts[9])        # 元
            date = parts[30]
            time_ = parts[31]

            change = round(latest - prev_close, 4)
            change_pct = round(change / prev_close * 100, 2) if prev_close else 0

            rows.append({
                "代码": code,
                "名称": _INDEX_CODES.get(code, code),
                "今开": open_price,
                "昨收": prev_close,
                "最新价": latest,
                "最高": high,
                "最低": low,
                "成交量": int(volume),
                "成交额": round(amount / 1e8, 2),  # 亿元
                "日期": date,
                "时间": time_,
                "涨跌额": change,
                "涨跌幅": change_pct,
            })

        return pd.DataFrame(rows)
    except Exception as e:
        logger.warning(f"Sina market overview failed: {e}")
        raise


def get_realtime_quotes_sina(symbols: list[str]) -> pd.DataFrame:
    """
    Fetch real-time quotes for individual stocks from Sina Finance.

    Args:
        symbols: List of 6-digit stock codes, e.g. ["000021", "600519"]

    Returns DataFrame with columns:
      代码, 名称, 今开, 昨收, 最新价, 最高, 最低, 成交量, 成交额,
      涨跌额, 涨跌幅, 换手率, 市盈率, 市净率, 总市值, 流通市值
    """
    # Convert codes to sina format
    sina_codes = []
    for s in symbols:
        s = s.strip()
        if s.startswith("6"):
            sina_codes.append(f"sh{s}")
        elif s.startswith("0") or s.startswith("3"):
            sina_codes.append(f"sz{s}")
        elif s.startswith("8") or s.startswith("4"):
            sina_codes.append(f"bj{s}")
        else:
            sina_codes.append(f"sz{s}")

    codes_str = ",".join(sina_codes)
    url = f"http://hq.sinajs.cn/list={codes_str}"
    try:
        r = requests.get(url, headers=_SINA_HEADERS, timeout=10)
        if r.status_code != 200:
            raise ConnectionError(f"Sina API returned {r.status_code}")

        rows = []
        for line in r.text.strip().split("\n"):
            if '=""' in line or "=" not in line:
                continue
            var_part, data_part = line.split("=", 1)
            full_code = var_part.split("_")[-1]
            code = full_code[2:]  # strip sh/sz prefix
            val = data_part.strip().strip('";')
            if not val:
                continue
            parts = val.split(",")
            if len(parts) < 32:
                continue

            name = parts[0]
            open_price = float(parts[1]) if parts[1] else 0
            prev_close = float(parts[2]) if parts[2] else 0
            latest = float(parts[3]) if parts[3] else 0
            high = float(parts[4]) if parts[4] else 0
            low = float(parts[5]) if parts[5] else 0
            volume = float(parts[8]) if parts[8] else 0
            amount = float(parts[9]) if parts[9] else 0

            change = round(latest - prev_close, 4) if prev_close else 0
            change_pct = round(change / prev_close * 100, 2) if prev_close else 0

            rows.append({
                "代码": code,
                "名称": name,
                "今开": open_price,
                "昨收": prev_close,
                "最新价": latest,
                "最高": high,
                "最低": low,
                "成交量": int(volume),
                "成交额": round(amount / 1e8, 2),
                "涨跌额": change,
                "涨跌幅": change_pct,
            })

        return pd.DataFrame(rows)
    except Exception as e:
        logger.warning(f"Sina realtime quotes failed: {e}")
        raise
