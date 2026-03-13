import streamlit as st
import pandas as pd
import ta
import os
import requests
import json
import logging
import re
import time
from datetime import datetime
from dotenv import load_dotenv
import urllib3
import io
import subprocess


# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 📝 日誌設定
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# ==========================================
# 🔑 設定區 & API Client
# ==========================================
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")

if 'gemini_client' not in st.session_state:
    st.session_state.gemini_client = None
    if GEMINI_API_KEY:
        try:
            from google import genai
            logger.info("Initializing Gemini Client...")
            st.session_state.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            logger.info("Gemini Client initialized successfully.")
        except Exception as e:
            logger.error(f"Gemini Client initialization failed: {str(e)}")
            st.warning(f"⚠️ AI 功能啟動失敗: {str(e)}")
    else:
        logger.warning("GEMINI_API_KEY not found in environment.")

# ==========================================
# 💾 參數儲存系統 (Config System)
# ==========================================
from config.settings import DEFAULT_CONFIG, STRATEGY_PRESETS, ConfigManager
from core.analyzer import RPAnalyzer


config = ConfigManager.load()

# ==========================================
# 🛠️ 核心邏輯：R/P 量化評分模型
# ==========================================
# (Redundant function calculate_rp_strategy removed, using RPAnalyzer instead)


# ==========================================
# 🛠️ 工具函數 (🔥 修正版 AI 呼叫)
# ==========================================
def send_line_broadcast(msg):
    if not LINE_ACCESS_TOKEN: return
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"}
    try: requests.post(url, headers=headers, data=json.dumps({"messages": [{"type": "text", "text": msg}]}))
    except: pass

def ask_gemini(prompt):
    client = st.session_state.get('gemini_client')
    if not client: return "⚠️ API Key Error: Client not initialized"
    
    # 🔥 自動重試機制 (解決 429 錯誤)
    max_retries = 3
    base_delay = 10
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt
            )
            return response.text
        except Exception as e:
            error_str = str(e)
            # 判斷是否為限速錯誤
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < max_retries - 1:
                    wait_time = base_delay * (attempt + 1)
                    with st.empty():
                        for s in range(wait_time, 0, -1):
                            st.caption(f"⏳ 觸發 API 限速保護，冷卻中... {s} 秒 (第 {attempt+1} 次重試)")
                            time.sleep(1)
                    continue
                else:
                    return "❌ 分析失敗：API 請求過於頻繁，請稍後再試。"
            else:
                return f"AI Error: {error_str}"

from data.market_data import get_technical_data, get_bulk_technical_data

def parse_pasted_text(raw_text):
    parsed = {}
    if raw_text:
        for line in raw_text.split('\n'):
            match = re.search(r'(\d{4}).*?(\d{3}/\d{2}/\d{2})', line)
            if match:
                c, d = match.group(1), match.group(2)
                p = d.split('/')
                parsed[c] = f"{int(p[0])+1911}-{p[1]}-{p[2]}"
    return parsed

# ==========================================
# 🚀 主程式 UI 
# ==========================================
st.set_page_config(page_title="CBAS 鄭大戰情室 (v23)", layout="wide", page_icon="💎")
st.title("💎 CBAS 鄭大戰情室 (單一主控版) v2.1.2-Master-Fundamentals-Fixed")

@st.cache_data(ttl=300)
def get_git_commit():
    try:
        commit = subprocess.check_output(['git', 'log', '-1', '--format="%h - %s"']).decode('utf-8').strip().strip('"')
        return commit
    except Exception:
        return "Unknown Version"

st.info(f"📌 **目前系統版本 / 部署狀態:** `{get_git_commit()}`")

# --- 側邊欄 ---
st.sidebar.header("📂 系統狀態")
st.sidebar.success("✅ 100% 全自動即時報價連線中 (免上傳 Excel)")

st.sidebar.header("🎯 策略快速套用 (Presets)")
col1, col2, col3 = st.sidebar.columns(3)
if col1.button("🛡️ 保守"):
    config.update(STRATEGY_PRESETS["保守 (Conservative)"])
    ConfigManager.save(config)
    st.rerun()
if col2.button("⚖️ 標準"):
    config.update(STRATEGY_PRESETS["標準 (Standard)"])
    ConfigManager.save(config)
    st.rerun()
if col3.button("🔥 激進"):
    config.update(STRATEGY_PRESETS["激進 (Aggressive)"])
    ConfigManager.save(config)
    st.rerun()



@st.cache_data(ttl=3600)
def get_cbas_live_data():
    url = 'https://cbas16889.pscnet.com.tw/api/MiDownloadExcel/GetExcel_IssuedCB'
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
    }
    try:
        from io import BytesIO
        res = requests.get(url, headers=headers, verify=False, timeout=15)
        if res.status_code == 200:
            df_api = pd.read_excel(BytesIO(res.content))
            
            col_map = {
                '債券代號': '代號',
                '標的債券': '名稱',
                '可轉債市價': 'CB市價',
                '溢(折)價率': '溢/折價',
                '餘額比例': '餘額',
                '轉換價值': '轉換價值',
                'TCRI': 'TCRI',
                '最新賣回日': '賣回日',
                '發行日期': '上市日'
            }
            df_api = df_api.rename(columns=col_map)
            
            if '代號' in df_api.columns:
                df_api['代號'] = df_api['代號'].astype(str).str.replace(' ', '')
                df_api = df_api[df_api['代號'].notna() & (df_api['代號'] != 'nan') & (df_api['代號'] != '')]
                df_api['股票代號'] = df_api['代號'].apply(lambda x: x[:4])
            
            for c in ['CB市價', '溢/折價', '餘額', '轉換價值', 'TCRI']:
                if c in df_api.columns: 
                    df_api[c] = pd.to_numeric(df_api[c], errors='coerce')
            
            # 修正某些欄位如果單位過小的情形 (如 API 給小數)
            for c in ['轉換價值', '溢/折價', '餘額']:
                if c in df_api.columns:
                    # 如果仍有特別小的小數，則乘100 (防呆)
                    if df_api[c].median() < 10 and df_api[c].median() > 0: 
                        df_api[c] *= 100
            
            for c in ['賣回日', '上市日']:
                if c in df_api.columns: 
                    df_api[c] = pd.to_datetime(df_api[c], errors='coerce')
                    if c == '賣回日': 
                        df_api['距離賣回日(天)'] = (df_api[c] - today).dt.days
                    if c == '上市日': 
                        df_api['上市天數'] = (today - df_api['上市日']).dt.days.apply(lambda x: max(0, int(x)) if pd.notna(x) else 0)
            
            return df_api
    except Exception as e:
        logger.error(f"CBAS API Error: {e}")
    return pd.DataFrame()

today = datetime.now()

with st.spinner("🔄 正在從官方金庫同步最新可轉債即時報價..."):
    df = get_cbas_live_data()

if df.empty:
    st.error("⚠️ 無法從官方 API 取得資料，請稍後重試。")
    st.stop()

# --- 側邊欄：濾網 ---
st.sidebar.markdown("---")
st.sidebar.header("🔍 篩選濾網 (可儲存)")
price_range = st.sidebar.slider("1. CB 市價", 80, 200, 
                                (config.get('filter_price_min', 110), config.get('filter_price_max', 120)))
prem_range = st.sidebar.slider("2. 溢價率", -10, 50, 
                               (config.get('filter_prem_min', 5), config.get('filter_prem_max', 15)))
ratio_min = st.sidebar.slider("3. 未轉換餘額 > (%)", 0, 100, config.get('filter_ratio_min', 90))
parity_range = st.sidebar.slider("4. 股價靠近轉換價 (%)", 50, 150, 
                                 (config.get('filter_parity_min', 90), config.get('filter_parity_max', 110)))
min_vol_avg = st.sidebar.number_input("5. 五日均量 > (張)", value=config.get('filter_vol_min', 1000), step=100)

if st.sidebar.button("💾 儲存濾網與評分設定 (Save Config)"):
    config['filter_price_min'] = price_range[0]
    config['filter_price_max'] = price_range[1]
    config['filter_prem_min'] = prem_range[0]
    config['filter_prem_max'] = prem_range[1]
    config['filter_ratio_min'] = ratio_min
    config['filter_parity_min'] = parity_range[0]
    config['filter_parity_max'] = parity_range[1]
    config['filter_vol_min'] = min_vol_avg
    ConfigManager.save(config)
    st.sidebar.success("✅ 設定已儲存成功！下次開啟將自動載入。")

# --- 側邊欄：評分參數 ---
with st.sidebar.expander("⚙️ 專家評分參數 (Scoring)", expanded=False):
    new_cfg = config.copy()
    st.caption("🛡️ Risk (R值)")
    c1, c2 = st.columns(2)
    new_cfg['risk_price_safe'] = c1.number_input("安全價 <", value=config['risk_price_safe'])
    new_cfg['risk_price_mid'] = c2.number_input("舒適價 <", value=config['risk_price_mid'])
    new_cfg['risk_price_high'] = st.number_input("警戒價 >", value=config['risk_price_high'])
    c3, c4 = st.columns(2)
    new_cfg['risk_prem_safe'] = c3.number_input("安全溢價 <", value=config['risk_prem_safe'])
    new_cfg['risk_prem_high'] = c4.number_input("危險溢價 >", value=config['risk_prem_high'])

    st.caption("🚀 Potential (P值)")
    new_cfg['pot_balance_high'] = st.number_input("籌碼安定%", value=config['pot_balance_high'])
    new_cfg['pot_vol_zombie'] = st.number_input("殭屍量<", value=config['pot_vol_zombie'])
    new_cfg['pot_vol_active'] = st.number_input("活絡量>", value=config['pot_vol_active'])
    c5, c6 = st.columns(2)
    new_cfg['pot_parity_min'] = c5.number_input("甜蜜點下限", value=config['pot_parity_min'])
    new_cfg['pot_parity_max'] = c6.number_input("甜蜜點上限", value=config['pot_parity_max'])
    
    if st.button("💾 儲存評分參數"):
        ConfigManager.save(new_cfg)
        config = new_cfg
        st.sidebar.success("評分參數已更新！")

# --- 執行篩選 ---
mask = (df['CB市價'].between(price_range[0], price_range[1])) & \
       (df['溢/折價'].between(prem_range[0], prem_range[1])) & \
       (df['餘額'] >= ratio_min) & \
       (df['轉換價值'].between(parity_range[0], parity_range[1]))
candidates_pre = df[mask].copy()

final_results = []
if not candidates_pre.empty:
    with st.spinner("🚀 正在聯網批次抓取技術面、基本面數據並進行 R/P 量化評分..."):
        unique_codes = candidates_pre['股票代號'].unique().tolist()
        bulk_tech_data = get_bulk_technical_data(unique_codes, fetch_fundamentals=True)

        for _, row in candidates_pre.iterrows():
            tech = bulk_tech_data.get(row['股票代號'])
            if tech and tech['vol_avg_sheets'] < min_vol_avg: continue
            
            # 統一評分邏輯
            r, p, lbl, gold = RPAnalyzer.calculate_score(row, tech, row['上市天數'], config)

            
            # 🔥 狀態顯示邏輯 (與 main.py 一致)
            listing_days = row['上市天數']
            # 注意: app.py 撈取的 API 欄位中可能叫 '距離賣回日(天)'
            days_put = row.get('距離賣回日(天)', 9999)
            
            if config.get('pot_golden_min', 365) <= listing_days <= config.get('pot_golden_max', 730):
                gp_status = "✨上市滿一年"
            elif 0 < days_put < 365:
                gp_status = "💰賣回前一年"
            elif 0 < listing_days < 100:
                gp_status = "👶新債蜜月期"
            elif listing_days > config.get('pot_golden_max', 730):
                gp_status = "🐢上市逾一年"
            else:
                gp_status = "👀觀察期"
            
            res = row.to_dict()
            res.update({
                'R值': r, 'P值': p, '策略標籤': lbl,
                '黃金期': gp_status,
                '母股價': float(tech['price']) if tech and tech.get('price') is not None else None,
                '均量': int(tech['vol_avg_sheets']) if tech and tech.get('vol_avg_sheets') is not None else None,
                '60MA': round(float(tech['ma60']), 2) if tech and tech.get('ma60') is not None else None,
                '87MA': round(float(tech['ma87']), 2) if tech and tech.get('ma87') is not None else None,
                'EPS': float(tech['fundamentals'].get('eps', 0)) if tech and 'fundamentals' in tech else 0,
                'PE': round(float(tech['fundamentals'].get('pe', 0)), 1) if tech and 'fundamentals' in tech else 0,
                '上市日期顯示': row['上市日'].strftime('%Y-%m-%d') if pd.notna(row.get('上市日')) else '未知'
            })
            final_results.append(res)

candidates = pd.DataFrame(final_results)

# ==========================================
# 📊 主畫面：系統說明書
# ==========================================
st.markdown("### 📊 戰情室系統說明書 (System Guide)")

with st.expander("📖 點此展開：系統架構、AI 原理與 R/P 評分邏輯", expanded=False):
    tab_sys, tab_ai, tab_r, tab_p = st.tabs(["🔄 系統架構", "🧠 AI 原理", "🛡️ R值邏輯", "🚀 P值邏輯"])
    
    with tab_sys:
        st.markdown("#### 🌐 資料來源與處理流程")
        # 防呆機制：如果沒有 graphviz，改用文字顯示
        try:
            st.graphviz_chart("""
            digraph G {
                rankdir=LR;
                node [shape=box, style=filled, fillcolor="#f9f9f9"];
                
                subgraph cluster_input {
                    label = "資料輸入源 (Data Sources)";
                    style=dashed;
                    Excel [label="📂 用戶上傳 Excel\n(價格/溢價/餘額)", fillcolor="#e1f5fe"];
                    TPEX [label="🏛️ 櫃買中心 (TPEX)\n(上市日/發行資料)", fillcolor="#fff9c4"];
                    Yahoo [label="📈 Yahoo Finance\n(技術面/籌碼/基本面)", fillcolor="#e0f2f1"];
                }
                
                Process [label="⚙️ Python 量化引擎\n(R/P 評分演算法)", shape=component, fillcolor="#ffe0b2"];
                
                subgraph cluster_output {
                    label = "決策輸出 (Outputs)";
                    style=dashed;
                    Table [label="📊 戰情儀表板\n(篩選後清單)"];
                    AI_Agent [label="🤖 AI 首席分析師\n(Gemini 2.0)", shape=ellipse, fillcolor="#e1bee7"];
                    LINE [label="📱 LINE 廣播\n(即時通知)", fillcolor="#c8e6c9"];
                }
                
                Excel -> Process;
                TPEX -> Process [label="Selenium"];
                Yahoo -> Process [label="API"];
                Process -> Table;
                Table -> AI_Agent [label="傳送評分數據"];
                AI_Agent -> LINE [label="生成投資報告"];
            }
            """)
        except:
            st.info("⚠️ 您的環境未安裝 Graphviz，僅顯示文字流程：")
            st.text("[Excel/TPEX/Yahoo] --> (Python量化引擎) --> [戰情儀表板] --> (AI 分析師) --> [LINE 廣播]")

        st.info("""
        **資料來源細節：**
        1. **Excel 報表**：提供基礎報價、溢價率、未轉換餘額。
        2. **櫃買中心 (TPEX)**：透過自動化爬蟲 (Selenium) 抓取精確的「上市日期」，用於判斷「黃金期」。
        3. **Yahoo Finance**：即時抓取母股股價、成交量、均線 (60MA/87MA)、財報數據 (EPS/PE) 與技術指標 (RSI)。
        """)

    with tab_ai:
        st.markdown("#### 🧠 AI 大腦揭密 (The Brain)")
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("""
            **核心模型：**
            > **Google Gemini 2.0 Flash Lite**
            
            **選擇理由：**
            * **速度快**：適合即時分析。
            * **邏輯強**：能理解複雜的 R/P 矩陣。
            """)
        with c2:
            st.markdown("**🔍 AI Prompt Design:**")
            st.code("""
# Role (角色設定): 
你是一位精通「鄭大 CB 策略」的首席分析師。

# Context (提供數據):
- R值: 3分 (低風險)
- P值: 8分 (高潛力)
- 狀態: 上市滿一年 (黃金期)
- 基本面: EPS成長、本益比合理

# Task (任務指令):
請忽略一般股價波動，專注於「可轉債特性」。
根據 R/P 分數，判斷是否為「不對稱機會」(下檔有限/上檔無限)。
最後給出明確操作建議 (買進/觀望)。
            """, language="yaml")

    with tab_r:
        st.markdown(f"""
        **核心概念：尋找「不對稱風險」 (Asymmetric Risk)**
        * 我們希望找到「跌無可跌 (有債底保護)」，但「漲無止盡」的標的。
        * **R值越低 (0~3分)**：代表接近債券本質，保本能力強。
        """)
        st.markdown(f"""
        | 評分項目 | 條件區間 | 分數 | 💡 策略原理解析 |
        | :--- | :--- | :--- | :--- |
        | **CB 市價** | `< {config['risk_price_safe']} 元` | **+1** | **【絕對債底】** 接近票面價 100 元，下檔有限，卻擁有股票看漲期權。 |
        | | `{config['risk_price_safe']} ~ {config['risk_price_mid']} 元` | **+3** | **【安全氣囊】** 雖然稍微漲上來，但距離百元保本價不遠，心態可穩健。 |
        | | `{config['risk_price_mid']} ~ {config['risk_price_high']} 元` | **+6** | **【股性增強】** 價格已脫離債底，此時波動會與股票同步，抗跌性變弱。 |
        | | `> {config['risk_price_high']} 元` | **+9** | **【風險懲罰】** 價格過高，這時買 CB 跟買股票風險一樣大，卻少了股息，**毫無優勢，禁止追價**。 |
        | **溢價率** | `< 0%` (折價) | **-1** | **【套利空間】** CB 比轉換後的股票還便宜，除了連動性 100%，還有補漲歸零的動力。 |
        | | `> 20%` | **+5** | **【虛胖阻力】** 溢價太高，股價上漲時 CB 往往不動 (在消化溢價)，資金效率極差。 |
        """)

    with tab_p:
        st.markdown(f"""
        **核心概念：捕捉「發行人心態」與「Gamma 加速」**
        * 我們希望找到「主力不得不拉抬」或「技術面剛好進入加速區」的時間點。
        * **P值越高**：代表主力作價的動機越強。
        """)
        st.markdown(f"""
        | 評分項目 | 條件區間 | 分數 | 💡 策略原理解析 |
        | :--- | :--- | :--- | :--- |
        | **時機窗** | `上市 {config['pot_golden_min']}~{config['pot_golden_max']} 天` | **+3** | **【作帳黃金期】** 統計上，發行滿一年時公司常有動作 (資產交換/除權息)，易出現異常報酬。 |
        | **籌碼面** | `未轉餘額 > {config['pot_balance_high']}%` | **+2** | **【籌碼安定】** 餘額高代表主力還沒下車，或發行商尚未開始倒貨，後續才有「拉高出貨」的空間。 |
        | **甜蜜點** | `轉換價值 {config['pot_parity_min']}~{config['pot_parity_max']}%` | **+3** | **【Gamma 加速區】** 股價剛好在轉換價附近，此時 CB 價格對股價最敏感，隨時可能一根長紅突破。 |
        | **技術面** | `站上 87MA` | **+2** | **【主力成本線】** 87MA 常被視為中線主力成本，站上代表多頭趨勢確立。 |
        | **成交量** | `殭屍量 (<{config['pot_vol_zombie']}張)` | **-3** | **【流動性風險】** 沒量的股票，主力想拉也拉不動，且易產生滑價損失，應避開。 |
        """)

if candidates.empty:
    st.warning("⚠️ 篩選無結果，請放寬側邊欄條件。")
    st.stop()

# ==========================================
# 🔄 工作流
# ==========================================
tab1, tab2 = st.tabs(["🏆 Step 1: 戰情總覽與 AI 掃描", "🚀 Step 2: 單檔深度戰情"])

with tab1:
    st.write(f"篩選出 **{len(candidates)}** 檔標的。")
    display_cols = [
        '代號', '名稱', '策略標籤', 'Risk', 'Potential', '黃金期',
        'CB市價', '溢/折價', '轉換價值', '餘額', 
        '母股價', '60MA', '87MA', '均量', 'EPS', 'PE', '上市日期顯示'
    ]
    # 重新映射 R/P 為顯示名稱以免衝突
    candidates = candidates.rename(columns={'R值': 'Risk', 'P值': 'Potential'})
    
    st.dataframe(
        candidates[display_cols],
        column_config={
            "Risk": st.column_config.ProgressColumn("Risk", min_value=0, max_value=10, format="%d"),
            "Potential": st.column_config.ProgressColumn("Potential", min_value=0, max_value=10, format="%d"),
            "溢/折價": st.column_config.NumberColumn(format="%.1f%%"),
            "轉換價值": st.column_config.NumberColumn(format="%.1f%%"),
            "餘額": st.column_config.NumberColumn(format="%.1f%%"),
            "均量": st.column_config.NumberColumn(format="%d 張"),
            "母股價": st.column_config.NumberColumn(format="%.2f"),
            "EPS": st.column_config.NumberColumn(format="%.2f"),
            "上市日期顯示": st.column_config.TextColumn("上市日期")
        }, hide_index=True
    )
    
    elite = candidates[(candidates['Risk'] <= 5) & (candidates['Potential'] >= 5)]
    st.markdown(f"### 🤖 AI 批量掃描 (精選 {len(elite)} 檔)")
    
    if st.button("🚀 啟動 AI 批量簡評"):
        if elite.empty:
            st.warning("無符合 R≤5 & P≥5 的標的。")
        else:
            targets_info = ""
            for i, (idx, row) in enumerate(elite.iterrows()):
                days_lbl = row.get('黃金期', '觀察期')
                targets_info += f"[{i+1}] 標的: {row['名稱']}({row['代號']}) | Risk: {row['Risk']} | Potential: {row['Potential']} | 市價: {row['CB市價']} | 溢價: {row['溢/折價']:.1f}% | 狀態: {days_lbl}\n"
                
            prompt = f"""
            # Role: 鄭大 CB 策略操盤手 (風格: 穩健、重視風險報酬比、有憑有據)
            
            # Input Data (多檔標的):
            {targets_info}
            
            # Decision Rules (嚴格執行):
            1. **風險檢核**: 若 Risk>5 或 溢價>20%，指令必須是【暫時觀望】或【嚴設停損】，並明確指出「追高風險」。
            2. **價格邏輯**: 若建議買進，必須說明「理由」。(例如：因為「貼近110債底保護」或「低溢價具補漲空間」)。
            3. **拒絕廢話**: 不要說「建議投資人留意」，直接說「買」或「不買」。
            
            # Output Format (每檔約 50-60 字):
            請為每一檔標的輸出建議，格式如下：
            ⭐ [名稱] (R[Risk值]/P[Potential值])
            【指令】操作建議與價位。(理由：針對價格與風險的具體解釋)
            """
            
            with st.spinner("🚀 AI 批量分析進行中..."):
                comment = ask_gemini(prompt)
                clean_comment = comment.replace("**", "")
                
            full_msg = "🏆 鄭大精選掃描報告 (深度指令版) 🏆\n\n" + clean_comment
            st.text_area("AI 報告預覽", full_msg, height=400) # 高度稍微加大
            send_line_broadcast(full_msg)
            st.success("深度指令報告已發送至 LINE！")

with tab2:
    col1, col2 = st.columns([2,1])
    target_str = col1.selectbox("選擇標的", candidates['代號'] + " " + candidates['名稱'])
    manual_date = col2.date_input("校正上市日", value=None)
    
    if st.button("啟動全方位戰情分析"):
        row = candidates[candidates['代號'] == target_str.split()[0]].iloc[0]
        with st.spinner("正在聯網抓取產業與財報數據..."):
            tech_detail = get_technical_data(row['股票代號'], fetch_fundamentals=True)
        
        fund = tech_detail['fundamentals']
        ind = tech_detail['indicators']
        days = row['上市天數']
        if manual_date: days = (today.date() - manual_date).days
        
        prompt = f"""
# Role: 鄭大 CB 策略首席分析師
# Task: 綜合量化分數、基本面與技術面，給出深度投資建議。

# 1. 核心量化數據 (R/P Model):
- **標的**: {row['名稱']} ({row['代號']}) - **{row['策略標籤']}**
- **Risk (風險)**: {row['Risk']} (評分: 價格<{config['risk_price_safe']}加分, 溢價>20扣分)
- **Potential (潛力)**: {row['Potential']} (評分: 籌碼>90%加分, 轉換價值90-110%加分)
- **時機窗**: 上市 {int(days)} 天 ({row['黃金期']})

# 2. 籌碼與位置 (關鍵):
- **轉換價值**: {row['轉換價值']:.2f}% (是否在 90-110 甜蜜點?)
- **未轉餘額**: {row['餘額']:.2f}% (籌碼是否安定?)
- **溢價率**: {row['溢/折價']:.2f}%

# 3. 產業與基本面:
- 產業: {fund.get('sector')} - {fund.get('industry')}
- 估值: PE {row.get('PE', 0):.1f}, EPS {row.get('EPS', 0):.2f}
- 成長: 營收成長 {fund.get('rev_growth', 0)*100:.1f}%

# 4. 技術面詳解:
- 趨勢: 股價 {row['母股價']:.2f} vs 87MA {row['87MA']:.2f}
- 動能: 5日均量 {row['均量']} 張
- 指標: RSI={ind.get('rsi', 0):.1f}

# 5. 鄭大操作指引 (Action):
請給出最終建議：[操作]: 積極買進 / 分批佈局 / 觀望 / 停利。
理由需整合：時機窗、甜蜜點位置、籌碼優勢與基本面。
"""
        with st.spinner("AI 撰寫中..."):
            reply = ask_gemini(prompt)
            st.markdown(reply)
            send_line_broadcast(f"🔥 {row['名稱']} 全方位報告\n\n{reply}")