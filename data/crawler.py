from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import os
import json
import traceback
import logging
from datetime import datetime
import io
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設定 logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_FILE = "tpex_listing_cache.json"

def get_cached_tpex_data():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            cache_date = cache_data.get("cache_date")
            today = datetime.now().strftime("%Y-%m-%d")
            if cache_date == today:
                logger.info(f"⚡ 使用本地快取資料 ({CACHE_FILE})")
                return cache_data.get("data")
            else:
                logger.info("⚡ 本地快取已過期，準備重新抓取")
    except Exception as e:
        logger.warning(f"⚠️ 讀出快取失敗: {e}")
    return None

def save_tpex_data_to_cache(data):
    try:
        cache_content = {
            "cache_date": datetime.now().strftime("%Y-%m-%d"),
            "data": data
        }
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_content, f, ensure_ascii=False, indent=4)
        logger.info(f"💾 成功儲存資料至本地快取 ({CACHE_FILE})")
    except Exception as e:
        logger.warning(f"⚠️ 寫入快取失敗: {e}")

def fetch_tpex_with_selenium():
    '''
    V1.6: 增加本地快取機制。因為 TPEX 網頁被高度 JS 化，所以仍需依賴 Selenium 模擬瀏覽器抓取。
    但透過快取機制，一天只會啟動一次無頭瀏覽器，後續呼叫速度極快。
    '''
    cached_data = get_cached_tpex_data()
    if cached_data:
        return cached_data

    issuer_map = {}
    driver = None
    try:
        logger.info("🕷️ 爬蟲啟動：準備連接櫃買中心...")
        
        chrome_options = Options()
        chrome_options.add_argument("--headless") 
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")
        
        chrome_bin = os.environ.get("CHROME_BIN")
        if chrome_bin:
            chrome_options.binary_location = chrome_bin
            
        chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
        if chromedriver_path:
            service = Service(executable_path=chromedriver_path)
        else:
            service = Service(ChromeDriverManager().install())
            
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        url = "https://www.tpex.org.tw/zh-tw/bond/issue/cbond/listed.html"
        driver.get(url)
        
        # 等待 JS 渲染表格
        time.sleep(5)
        html = driver.page_source
        
        if len(html) < 1000:
            logger.error("❌ 爬蟲失敗：抓回來的 HTML 太短，可能被 IP 封鎖。")
            driver.quit()
            return {}

        dfs = pd.read_html(io.StringIO(html))
        
        if not dfs:
            logger.warning("⚠️ 警告：網頁中找不到任何表格 (Table)。")
            driver.quit()
            return {}
            
        df_table = dfs[0]
        logger.info(f"✅ 成功抓取表格，共 {len(df_table)} 筆資料")
        
        col_c = next((c for c in df_table.columns if '代碼' in str(c)), None)
        col_d = next((c for c in df_table.columns if '日期' in str(c)), None)
        col_n = next((c for c in df_table.columns if '名稱' in str(c)), None)
            
        if col_c and col_d:
            count = 0
            for _, row in df_table.iterrows():
                try:
                    c = str(row[col_c]).strip()
                    n = str(row[col_n]).strip() if col_n else ""
                    d = str(row[col_d]).strip()
                    
                    if '/' in d:
                        p = d.split('/')
                        if len(p) == 3:
                            year = int(p[0]) + 1911
                            fd = f"{year}-{p[1]}-{p[2]}"
                            if c not in issuer_map: issuer_map[c] = []
                            issuer_map[c].append({'full_name': n, 'date': fd})
                            count += 1
                except Exception: continue
            logger.info(f"🎉 解析完成，有效資料: {count} 筆")
            
            # 寫入快取
            if issuer_map:
                save_tpex_data_to_cache(issuer_map)
                
        else:
            logger.error("❌ 找不到關鍵欄位 (代碼/日期)。")

    except Exception:
        logger.error("❌ 爬蟲發生嚴重錯誤:")
        logger.error(traceback.format_exc())
    finally:
        if driver:
            driver.quit()
            
    return issuer_map