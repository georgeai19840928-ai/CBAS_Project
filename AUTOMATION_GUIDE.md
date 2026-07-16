# CBAS 自動抓資料與定期推播指南

本專案已內建排程腳本 `cron_job.py`，可在不開啟 Streamlit 介面的情況下：

1. 自動下載官方 CBAS 可轉債即時報價。
2. 套用 `strategy_config.json` 的濾網。
3. 抓取母股行情與技術/基本面資料。
4. 計算 R/P 分數。
5. 產生每日戰報並推播到 Telegram。

## 環境變數

請在專案根目錄建立 `.env`：

```env
GEMINI_API_KEY=your_gemini_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

也可以先複製 `.env.example` 再填入自己的 key/token。

若暫時沒有 Gemini key，仍可使用 `--no-ai` 產生固定格式量化摘要。

## 本機測試

先測試資料抓取與篩選，不推播、不呼叫 AI：

```bash
python cron_job.py --dry-run --no-ai
```

測試含 Gemini 報告，但不推播：

```bash
python cron_job.py --dry-run
```

測試 Telegram 推播設定：

```bash
python cron_job.py --test-notification
```

正式推播：

```bash
python cron_job.py
```

## Windows 工作排程器

建議設定在台股收盤後，例如每個交易日 15:10。

- 程式或指令碼：填入 Python 執行檔路徑，例如 `C:\Python311\python.exe`
- 新增引數：`cron_job.py`
- 開始位置：專案根目錄，例如 `C:\Users\...\CBAS_Project`

若想先上線固定格式摘要、暫不使用 AI，可把新增引數改成：

```text
cron_job.py --no-ai
```

## Linux / Mac Cron

每週一到週五 15:10 執行：

```bash
10 15 * * 1-5 cd /path/to/CBAS_Project && /usr/bin/python3 cron_job.py >> cron.log 2>&1
```

固定格式摘要、不呼叫 AI：

```bash
10 15 * * 1-5 cd /path/to/CBAS_Project && /usr/bin/python3 cron_job.py --no-ai >> cron.log 2>&1
```

## GitHub Actions 排程

專案已提供 `.github/workflows/cbas-daily.yml`，預設會在台北時間週一到週五 15:10 執行。

設定步驟：

1. 將專案推到 GitHub。
2. 到 Repository `Settings` -> `Secrets and variables` -> `Actions`。
3. 新增三個 repository secrets：
   - `GEMINI_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. 到 `Actions` 頁面確認 `CBAS Daily Report` workflow 已啟用。

若想手動測試，可到該 workflow 點選 `Run workflow`。手動執行時可選 `no_ai=true`，先測試固定格式摘要與 Telegram 推播。

## 部署平台注意事項

目前 `zeabur.toml` 只負責啟動 Streamlit Web App。若部署平台支援 Cron Job，請另外建立排程命令：

```bash
python cron_job.py
```

必要環境變數同樣要在平台後台設定：

- `GEMINI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Telegram 權杖說明

程式使用 Telegram Bot API 的 `sendMessage` endpoint：

```text
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/sendMessage
```

設定方式：

1. 在 Telegram 找 `@BotFather` 建立 bot，取得 `TELEGRAM_BOT_TOKEN`。
2. 將 bot 加入你的個人聊天室、群組或頻道。
3. 取得 `TELEGRAM_CHAT_ID` 後填入 `.env` 或 GitHub/Zeabur secrets。
4. 執行 `python cron_job.py --test-notification` 確認可收到測試訊息。

## 故障排除

- `官方報表缺少必要欄位`：官方 Excel 欄位名稱可能變動，需要更新 `cron_job.py` 的 `col_map`。
- `Telegram 推播失敗`：確認 bot token、chat id 是否正確，且 bot 已加入該聊天室/群組/頻道。
- `AI 分析未完成`：確認 `GEMINI_API_KEY` 是否存在，或先使用 `--no-ai`。
- 篩選結果為 0：檢查 `strategy_config.json` 的市價、溢價、餘額、轉換價值與均量門檻是否過嚴。
