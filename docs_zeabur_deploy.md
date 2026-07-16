# 🚀 CBAS 戰情室 —— Zeabur 雲端佈署全攻略

為了解決您本地端有大量的歷史 Excel 報價表，同時又希望能讓系統 24 小時在雲端完美運作，我已經幫您將專案底層設定好了「Zeabur 專屬架構」。

您只需要跟著以下 **3 個步驟**，就能讓這台量化戰車正式升空！

---

## 🛠️ Step 1：解除封印，上傳 Excel 資料庫
原本您的系統中設定了「忽略上傳所有的 Excel 檔案 (`.gitignore` 裡面的 `*.xlsx`)」，這會導致您推送到雲端時，歷史回測的資料庫全部消失，使得回測系統報錯。

**✅ 我剛剛已經幫您修改完畢：**
我已經幫您把 `.gitignore` 裡面的 `.xlsx` 限制全部拿掉了！
請您現在透過 GitHub Desktop 或是 VSCode 的原始碼控制，將整個專案（包含 `data/historical_data` 裡面那 50 幾個 Excel 檔）**全部 Commit 並 Push 到您的 GitHub 儲存庫**。

*(不用擔心容量，我剛剛檢查過，您那 50 幾個檔加起來才約 10 MB，對 GitHub 來說連塞牙縫都不夠，非常安全！)*

---

## ⚙️ Step 2：Zeabur 環境變量設定 (Environment Variables)
在 Zeabur 雲端上，**不會讀取您本地的 `.env` 檔案**（為了安全）。
所以當您把專案綁定到 Zeabur 後，專案一開始可能會閃退或拿不到資料。請您立刻前往 Zeabur 的該專案 **[設定 (Settings)] -> [環境變數 (Environment Variables)]**，手動新增以下環境變數：

1. **`GEMINI_API_KEY`** = `您的 Google Gemini 憑證` (讓 AI 掃描可以運作)
2. **`TELEGRAM_BOT_TOKEN`** = `您的 Telegram Bot Token`
3. **`TELEGRAM_CHAT_ID`** = `您的 Telegram 聊天室、群組或頻道 ID`

*(這些鑰匙在您本地端的 `.env` 裡面找得到)*

---

## 🖥️ Step 3：套用修改過的 `zeabur.toml` 啟動儀表板
原本您的 Zeabur 設定 (`zeabur.toml`) 裡面寫的是 `python -m streamlit run main.py`，這會跑去啟動每天定時發送 Telegram 的微服務。

**✅ 我剛剛也已經幫您修改完畢：**
我已經將啟動指令無縫切換為了 `app.py`。
Zeabur 抓到您的 GitHub 更新後，就會自動安裝背後強大的 `chromium` 瀏覽器爬蟲引擎，並且準確啟動您最愛的那精美的 **Streamlit 戰略儀表板**！

---

### 🎉 佈署流程總複習 (3 分鐘搞定)
1. 在本地端：把所有剛改好的程式碼和 Excel 檔 **『Push 到 GitHub』**。
2. 在網頁端：登入 **Zeabur 管理介面** -> 點擊 **Create Service (建立服務)** -> **Deploy from GitHub (從 GitHub 佈署)** -> 選擇您的 CBAS 儲存庫。
3. Zeabur 會自動開始跑圈圈建置。
4. 去 Settings 裡面把 `.env` 的環境變數貼上。
5. 去 Domains 裡面點擊 **「Generate Domain (產生網域)」**。
6. 點擊那個網址，您的專屬戰情室就在雲端華麗誕生了！
