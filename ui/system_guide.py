import streamlit as st
import graphviz

def render_guide(config):
    """
    渲染系統說明書、架構圖與評分邏輯
    """
    st.markdown("### 📊 戰情室系統說明書 (System Guide)")

    with st.expander("📖 點此展開：系統架構、AI 原理與 R/P 評分邏輯", expanded=False):
        # 🔥 [V1.6 更新] 修改 Tab 名稱，提示這裡有日期定義
        tab_sys, tab_ai, tab_r, tab_p = st.tabs(["🔄 系統架構", "🧠 AI 原理", "🛡️ R值邏輯", "🚀 P值邏輯 (含日期定義)"])
        
        with tab_sys:
            st.markdown("#### 🌐 資料來源與處理流程")
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
            
            # 🔥 [V1.6 新增] 這裡補上了您原本缺失的「日期狀態定義表」
            st.markdown("#### 📅 日期狀態定義 (Time Status)")
            st.markdown(f"""
            | 狀態標籤 | 定義 (天數條件) | 💡 策略意義 |
            | :--- | :--- | :--- |
            | **✨ 上市滿一年** | 上市 `{config['pot_golden_min']}~{config['pot_golden_max']}` 天 | **【主力作帳】** 統計上，發行滿一年公司常有動作 (資產交換/除權息)，易出現異常報酬。 |
            | **💰 賣回前一年** | 距離賣回日 `< 365` 天 | **【保本拉抬】** 接近賣回日，主力為了避免投資人將債券賣回給公司(耗費現金)，有誘因拉抬股價促使轉換。 |
            | **👶 新債蜜月期** | 上市 `< 100` 天 | **【蜜月行情】** 剛上市籌碼乾淨，市場關注度高，易有短線行情。 |
            | **🐢 上市逾一年** | 上市 `> {config['pot_golden_max']}` 天 | **【沉澱期】** 超過作帳黃金期，且距離賣回還久，主力可能暫時休息。 |
            | **👀 觀察期** | 其他區間 | **【等待訊號】** 暫無明確時間優勢，需搭配技術面或籌碼面觀察。 |
            """)
            
            st.divider()
            
            st.markdown("#### 🚀 P值評分項目")
            st.markdown(f"""
            | 評分項目 | 條件區間 | 分數 | 💡 策略原理解析 |
            | :--- | :--- | :--- | :--- |
            | **時機窗** | 符合「上市滿一年」或「賣回前一年」 | **+3** | **【黃金期加分】** 處於上述兩個關鍵時間窗口。 |
            | **籌碼面** | `未轉餘額 > {config['pot_balance_high']}%` | **+2** | **【籌碼安定】** 餘額高代表主力還沒下車，或發行商尚未開始倒貨，後續才有「拉高出貨」的空間。 |
            | **甜蜜點** | `轉換價值 {config['pot_parity_min']}~{config['pot_parity_max']}%` | **+3** | **【Gamma 加速區】** 股價剛好在轉換價附近，此時 CB 價格對股價最敏感，隨時可能一根長紅突破。 |
            | **技術面** | `站上 87MA` | **+2** | **【主力成本線】** 87MA 常被視為中線主力成本，站上代表多頭趨勢確立。 |
            | **成交量** | `殭屍量 (<{config['pot_vol_zombie']}張)` | **-3** | **【流動性風險】** 沒量的股票，主力想拉也拉不動，且易產生滑價損失，應避開。 |
            """)