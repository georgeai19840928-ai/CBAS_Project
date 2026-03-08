from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import traceback
import logging
import io  # <--- 新增這個，用來解決 FutureWarning

# 設定 logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_tpex_with_selenium():
    issuer_map = {}
    driver = None
    try:
        logger.info("🕷️ 爬蟲啟動：準備連接櫃買中心...")
        
        chrome_options = Options()
        chrome_options.add_argument("--headless") 
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # 偽裝 User-Agent
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        url = "https://www.tpex.org.tw/zh-tw/bond/issue/cbond/listed.html"
        driver.get(url)
        
        time.sleep(5)
        html = driver.page_source
        
        if len(html) < 1000:
            logger.error("❌ 爬蟲失敗：抓回來的 HTML 太短，可能被 IP 封鎖。")
            driver.quit()
            return {}

        # 🔥 修正 FutureWarning: 使用 io.StringIO 包裝 HTML 字串
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
        else:
            logger.error("❌ 找不到關鍵欄位 (代碼/日期)。")

    except Exception:
        logger.error("❌ 爬蟲發生嚴重錯誤:")
        logger.error(traceback.format_exc())
        return {}
        
    finally:
        if driver:
            driver.quit()
            
    return issuer_map