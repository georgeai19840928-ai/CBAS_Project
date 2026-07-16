# CBAS 鄭大戰情室

CBAS 是一個台股可轉換公司債投資研究 App，透過官方可轉債報價、母股行情、R/P 量化評分、Gemini 分析與 Telegram 推播，協助建立每日追蹤清單。

## 主要功能

- Streamlit 戰情室：即時篩選可轉債、查看 R/P 評分、單檔 AI 分析。
- 自動每日掃描：`cron_job.py` 可自動抓官方報價、計算分數並推播 Telegram。
- 歷史回測：讀取 `data/historical_data` 的歷史報價表，模擬進出場與績效。
- 參數最佳化：使用網格搜尋比較不同濾網與風控設定。

## 安裝

```bash
pip install -r requirements.txt
```

建立 `.env`：

```env
GEMINI_API_KEY=your_gemini_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

## 啟動 Web App

```bash
streamlit run app.py
```

## 執行每日自動戰報

測試資料抓取與固定格式摘要：

```bash
python cron_job.py --dry-run --no-ai
```

測試 Telegram 推播：

```bash
python cron_job.py --test-notification
```

正式推播：

```bash
python cron_job.py
```

排程設定請看 [AUTOMATION_GUIDE.md](AUTOMATION_GUIDE.md)。

## 免責聲明

本專案僅供投資研究與教育用途，不構成任何投資建議。使用者需自行承擔交易風險。
