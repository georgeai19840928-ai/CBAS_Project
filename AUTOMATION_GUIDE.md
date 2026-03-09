# 🤖 CBAS 自動化排程指南 (CRON / n8n)

本系統已經內建一鍵執行所有分析流程的腳本 `cron_job.py`。
透過此腳本，您不需要打開瀏覽器也能讓系統在每天收盤後自動幫您篩選標的，並傳送 AI 戰報到您的 LINE。

## ⚙️ 先決條件
1. 確保您的專案目錄內有 `.env` 檔案，並且裡面有包含：
   - `GEMINI_API_KEY=your_gemini_key`
   - `LINE_ACCESS_TOKEN=your_line_notify_token`
   - (`LINE_ACCESS_TOKEN` 請至 [LINE Notify](https://notify-bot.line.me/) 官方網站申請)
2. 將每日最新的「CBAS 報價表 (Excel)」放置到指定資料夾，或覆寫根目錄的 `CBAS_0310.xlsx` 檔案。

## 📝 執行指令
您可以直接在終端機測試這行指令，確認系統能夠正常分析並推播到您的 LINE：
```bash
python cron_job.py <您的_Excel_絕對或相對路徑>
```
例如：
```bash
python cron_job.py ./CBAS_0310.xlsx
```

---

## 方法一：使用 Windows 工作排程器 (或 Linux Cron)

### 在 Windows 上設定：
1. 開啟 **「工作排程器 (Task Scheduler)」**。
2. 點選 **「建立基本工作...」**。
3. 名稱輸入 `CBAS 每日戰報分析`。
4. 觸發程序選擇 **「每天」**，時間設定在下午 14:30 或 15:00 (確保盤後報價表已經更新)。
5. 動作選擇 **「啟動程式」**：
   - **程式或指令碼**：填入您的 Python 執行檔路徑 (例如 `C:\Python310\python.exe` 或 Anaconda 的 python 路徑)
   - **新增引數**：填入 `cron_job.py ./CBAS_0310.xlsx` (或您實際存放的 Excel 檔名)
   - **開始位置**：填入目前的專案根目錄，例如 `D:\私人\CBAS_Project\`
6. 儲存後，系統每天就會在指定時間自動執行。

### 在 Linux / Mac 上設定 (Cron)：
打開終端機，輸入 `crontab -e`，然後新增以下內容 (每天下午 15:00 執行)：
```bash
0 15 * * 1-5 cd /path/to/CBAS_Project && /usr/bin/python3 cron_job.py ./CBAS_0310.xlsx >> cron.log 2>&1
```

---

## 方法二：結合外部自動化工具 (n8n / Make / Zapier)

若您希望達到**完全無人介入**的境界 (包含不用手動去抓 Excel)，建議可以使用 n8n 等工具建立以下流程：

1. **Trigger (觸發器)**：
   - 每天下午 14:30 觸發。
2. **Download File (下載檔案)**：
   - 透過 HTTP Request 或 Selenium 節點，自動登入券商網站並下載最新的 CBAS 報價 Excel 檔案。
3. **Execute Command (執行指令)**：
   - 使用 n8n 的 `Execute Command` 節點，執行 `python cron_job.py /tmp/downloaded_cbas.xlsx`。
4. **Done**：
   - Python 腳本執行完畢後，會自動把精選名單與 AI 分析結果送到您的 LINE！
