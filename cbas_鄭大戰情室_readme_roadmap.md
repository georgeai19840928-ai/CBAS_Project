# CBAS 鄭大戰情室（Convertible Bond Analysis System）

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" />
  <img src="https://img.shields.io/badge/streamlit-app-success" />
  <img src="https://img.shields.io/badge/license-MIT-green" />
  <img src="https://img.shields.io/badge/status-active--development-orange" />
</p>

---

## 專案簡介

**CBAS（Convertible Bond Analysis System）** 是一套專為可轉債（CB）交易者設計的開源量化決策輔助系統。

本系統將「鄭大 CB 策略」中高度主觀、經驗導向的判斷流程，轉化為：

- 可量化（Quantifiable）
- 可重複（Reproducible）
- 可配置（Configurable）

的程式化分析流程，並進一步結合 AI，產出具體、可執行的戰術指令。

---

## 核心功能

- CB 報價表 Excel 匯入與清洗
- Selenium 自動補抓櫃買中心上市日期
- Yahoo Finance 即時抓取母股：
  - 價格、成交量、均線（60 / 87 / 284）
  - EPS、本益比
- R / P（Risk / Potential）量化評分模型
- Gemini AI 戰術分析（支援 Retry / Exponential Backoff）
- LINE Notify 即時戰報推播

---

## 系統架構概覽

本專案採用**分層式模組架構**，將資料、策略、服務與介面完全解耦，利於維護與擴充。

```text
n8n_project_cbas/
├── main.py                # 主程式入口（V1.2）
├── requirements.txt       # 套件清單
├── .env                   # API Key（不提交 Git）
├── CBAS報價表.xlsx         # 使用者 CB 報價表
├── strategy_config.json   # 交易參數（自動生成）
│
├── config/                # 配置層
│   └── settings.py        # JSON 參數讀寫
│
├── core/                  # 核心策略層
│   └── analyzer.py        # R/P 評分引擎
│
├── data/                  # 數據層
│   ├── loader.py          # Excel 處理
│   ├── crawler.py         # TPEX Selenium 爬蟲
│   └── market_data.py     # Yahoo Finance
│
├── services/              # 服務層
│   ├── ai_agent.py        # Gemini AI + Retry
│   └── notification.py   # LINE Notify
│
└── ui/                    # 介面層
    └── system_guide.py   # 系統說明 / 架構圖
```

---

## 快速開始（Quick Start）

以下為最小可執行流程：

```bash
# 1. Clone 專案
git clone https://github.com/your-org/n8n_project_cbas.git
cd n8n_project_cbas

# 2. 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安裝套件
pip install -r requirements.txt

# 4. 啟動系統
python main.py
```

---

## 環境設定

在專案根目錄建立 `.env` 檔案：

```env
GEMINI_API_KEY=your_gemini_api_key_here
LINE_ACCESS_TOKEN=your_line_access_token_here
```

- 未設定 Gemini API：僅停用 AI 分析，其餘功能正常
- 未設定 LINE Token：不影響本地分析

---

## Excel 報價表格式

必要欄位：

- 代號
- 名稱
- CB市價
- 溢/折價
- 餘額
- 轉換價值

系統會自動處理百分比、缺值與上市日補抓。

---

## 執行流程說明

1. 讀取 Excel 報價表
2. Selenium 抓取上市日
3. Yahoo Finance 補齊技術 / 基本面
4. 套用濾網與 R/P 評分
5. 呼叫 AI 產出戰術建議
6. （選用）推播 LINE 戰報

---

## Roadmap（摘要）

- V1.3：策略 Preset（保守 / 標準 / 激進）
- V1.4：歷史回測模組
- V2.0：Web UI / 多策略引擎

---

## Contributing

歡迎對可轉債、量化策略、資料工程有興趣的開發者參與：

1. Fork 本專案
2. 建立 feature branch
3. 提交 Pull Request

---

## License

本專案採用 **MIT License**。

---

## 免責聲明

本專案僅為研究與教育用途，不構成任何投資建議。
使用本系統進行交易所產生之任何損益，需由使用者自行承擔。

