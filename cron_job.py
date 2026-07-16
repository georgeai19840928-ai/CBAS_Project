import argparse
import logging
import os
import sys
import warnings
from datetime import datetime
from io import BytesIO

import pandas as pd
import requests
import urllib3
from dotenv import load_dotenv

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

logging.getLogger("streamlit").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.caching.cache_data_api").disabled = True
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").disabled = True
warnings.filterwarnings("ignore", message="Workbook contains no default style")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import ConfigManager
from core.analyzer import RPAnalyzer
from data.market_data import get_bulk_technical_data
from services.ai_agent import AIAgent
from services.notification import send_telegram_message

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CBAS_EXCEL_URL = "https://cbas16889.pscnet.com.tw/api/MiDownloadExcel/GetExcel_IssuedCB"


def log(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)


def fetch_cbas_live_data():
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0",
    }
    response = requests.get(CBAS_EXCEL_URL, headers=headers, verify=False, timeout=20)
    response.raise_for_status()
    return pd.read_excel(BytesIO(response.content))


def normalize_cbas_data(df_api, today=None):
    today = today or datetime.now()
    col_map = {
        "債券代號": "代號",
        "標的債券": "名稱",
        "債券簡稱": "名稱",
        "簡稱": "名稱",
        "可轉債市價": "CB市價",
        "溢(折)價率": "溢/折價",
        "餘額比例": "餘額",
        "流通餘額(張數)": "餘額張數",
        "轉換價值": "轉換價值",
        "TCRI": "TCRI",
        "最新賣回日": "賣回日",
        "發行日期": "上市日",
    }
    df = df_api.rename(columns={k: v for k, v in col_map.items() if k in df_api.columns}).copy()

    required_cols = ["代號", "CB市價", "溢/折價", "餘額", "轉換價值"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"官方報表缺少必要欄位: {', '.join(missing)}")

    df["代號"] = df["代號"].astype(str).str.replace(" ", "", regex=False)
    df = df[df["代號"].notna() & (df["代號"] != "nan") & (df["代號"] != "")]
    df["股票代號"] = df["代號"].apply(lambda value: value[:4])

    if "名稱" not in df.columns:
        df["名稱"] = df["代號"]

    for col in ["CB市價", "溢/折價", "餘額", "轉換價值", "TCRI"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["轉換價值", "溢/折價", "餘額"]:
        if col in df.columns and 0 < df[col].median() < 10:
            df[col] *= 100

    for col in ["賣回日", "上市日"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            if col == "賣回日":
                df["距離賣回日(天)"] = (df[col] - today).dt.days
            if col == "上市日":
                df["上市天數"] = (today - df[col]).dt.days.apply(
                    lambda value: max(0, int(value)) if pd.notna(value) else 0
                )

    if "距離賣回日(天)" not in df.columns:
        df["距離賣回日(天)"] = 9999
    if "上市天數" not in df.columns:
        df["上市天數"] = 0

    return df


def filter_candidates(df, config):
    mask = (
        df["CB市價"].between(config.get("filter_price_min", 110), config.get("filter_price_max", 120))
        & df["溢/折價"].between(config.get("filter_prem_min", 5), config.get("filter_prem_max", 15))
        & (df["餘額"] >= config.get("filter_ratio_min", 90))
        & df["轉換價值"].between(config.get("filter_parity_min", 90), config.get("filter_parity_max", 110))
    )
    return df[mask].copy()


def score_candidates(candidates_pre, config):
    if candidates_pre.empty:
        return pd.DataFrame()

    stock_codes = candidates_pre["股票代號"].dropna().unique().tolist()
    bulk_tech_data = get_bulk_technical_data(stock_codes, fetch_fundamentals=True)

    final_results = []
    min_vol = config.get("filter_vol_min", 1000)
    for _, row in candidates_pre.iterrows():
        tech = bulk_tech_data.get(row["股票代號"])
        vol_avg = tech.get("vol_avg_sheets", 0) if tech else 0
        if min_vol > 0 and vol_avg < min_vol:
            continue

        r_score, p_score, label, is_golden, warnings, details = RPAnalyzer.calculate_score(
            row,
            tech,
            row.get("上市天數", 0),
            config,
        )

        result = row.to_dict()
        result.update(
            {
                "R值": r_score,
                "P值": p_score,
                "策略標籤": label,
                "黃金期": is_golden,
                "警示": "、".join(warnings),
                "均量": int(vol_avg) if pd.notna(vol_avg) else 0,
                "母股價": tech.get("price") if tech else None,
                "87MA": tech.get("ma87") if tech else None,
                "EPS": tech.get("fundamentals", {}).get("eps", 0) if tech else 0,
                "PE": round(tech.get("fundamentals", {}).get("pe", 0), 1) if tech else 0,
                "R_details": details.get("R", []),
                "P_details": details.get("P", []),
            }
        )
        final_results.append(result)

    if not final_results:
        return pd.DataFrame()

    return pd.DataFrame(final_results).sort_values(by=["P值", "R值"], ascending=[False, True])


def build_fallback_report(candidates, limit=10):
    if candidates.empty:
        return "本次篩選沒有符合條件的可轉債標的。"

    lines = ["今日 CBAS 自動掃描摘要", ""]
    for idx, (_, row) in enumerate(candidates.head(limit).iterrows(), start=1):
        warning = f" | 警示: {row['警示']}" if row.get("警示") else ""
        lines.append(
            f"{idx}. {row.get('名稱', '')}({row.get('代號', '')}) "
            f"R{row.get('R值')} / P{row.get('P值')} | {row.get('策略標籤')} | "
            f"CB {row.get('CB市價')} | 溢價 {row.get('溢/折價'):.1f}% | "
            f"轉換價值 {row.get('轉換價值'):.1f}% | 餘額 {row.get('餘額'):.1f}%{warning}"
        )
    lines.extend(["", "提醒：本訊息為量化篩選與研究參考，不構成投資建議。"])
    return "\n".join(lines)


def run_daily_job(dry_run=False, no_ai=False):
    load_dotenv()
    today = datetime.now()
    config = ConfigManager.load()

    log("開始執行 CBAS 全自動每日結算腳本")
    log("正在從官方金庫同步最新可轉債即時報價")
    df_api = fetch_cbas_live_data()
    df = normalize_cbas_data(df_api, today=today)
    log(f"官方報表載入完成，共 {len(df)} 檔")

    candidates_pre = filter_candidates(df, config)
    log(f"初步濾網篩選出 {len(candidates_pre)} 檔")
    if candidates_pre.empty:
        report = "今日 CBAS 自動掃描：依目前濾網設定，沒有符合條件的可轉債標的。"
    else:
        log("開始抓取母股行情並計算 R/P 分數")
        candidates = score_candidates(candidates_pre, config)
        log(f"R/P 評分後保留 {len(candidates)} 檔")
        report = build_fallback_report(candidates)

        if not no_ai and not candidates.empty:
            ai_agent = AIAgent(os.getenv("GEMINI_API_KEY"))
            ai_report = ai_agent.analyze_batch_summary(candidates)
            if ai_report and not ai_report.startswith("⚠️ API Key Error") and not ai_report.startswith("AI Error"):
                report = ai_report
            else:
                report = f"{report}\n\nAI 分析未完成：{ai_report}"

    full_msg = f"CBAS 戰情室每日結算 ({today.strftime('%Y-%m-%d')})\n\n{report}"

    if dry_run:
        log("Dry run 模式，不推播 Telegram。以下為訊息預覽：")
        print(full_msg)
        return True

    ok, message = send_telegram_message(
        os.getenv("TELEGRAM_BOT_TOKEN"),
        os.getenv("TELEGRAM_CHAT_ID"),
        full_msg,
    )
    if ok:
        log("Telegram 推播完成")
        return True

    log(f"Telegram 推播失敗：{message}")
    return False


def run_test_notification():
    load_dotenv()
    msg = f"CBAS Telegram 測試推播成功 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
    ok, message = send_telegram_message(
        os.getenv("TELEGRAM_BOT_TOKEN"),
        os.getenv("TELEGRAM_CHAT_ID"),
        msg,
    )
    if ok:
        log("Telegram 測試推播完成")
        return True
    log(f"Telegram 測試推播失敗：{message}")
    return False


def parse_args():
    parser = argparse.ArgumentParser(description="Run CBAS scheduled daily scan and Telegram broadcast.")
    parser.add_argument("--dry-run", action="store_true", help="Print the report without sending Telegram broadcast.")
    parser.add_argument("--no-ai", action="store_true", help="Skip Gemini and use deterministic summary only.")
    parser.add_argument("--test-notification", action="store_true", help="Send a short Telegram test message only.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.test_notification:
        success = run_test_notification()
    else:
        success = run_daily_job(dry_run=args.dry_run, no_ai=args.no_ai)
    raise SystemExit(0 if success else 1)
