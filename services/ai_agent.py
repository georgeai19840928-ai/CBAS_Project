import time
import streamlit as st
try:
    from google import genai
except ImportError:
    pass

class AIAgent:
    def __init__(self, api_key):
        self.client = None
        self.init_error = None
        if not api_key:
            self.init_error = "GEMINI_API_KEY 環境變數未設定或為空值"
        else:
            try:
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                self.init_error = f"Client 初始化失敗: {e}"

    def ask(self, prompt, max_retries=3, base_delay=10):
        if not self.client:
            return f"⚠️ API Key Error: Client not initialized. 詳細錯誤: {self.init_error}"
        
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash", 
                    contents=prompt
                )
                return response.text
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = base_delay * (attempt + 1)
                        with st.empty():
                            for s in range(wait_time, 0, -1):
                                st.caption(f"⏳ 觸發 API 限速保護，冷卻中... {s} 秒")
                                time.sleep(1)
                        continue
                    else:
                        return "❌ 分析失敗：API 請求過於頻繁，請稍後再試。"
                else:
                    return f"AI Error: {error_str}"

    def analyze_batch_summary(self, candidates, max_rows=12):
        if candidates is None or candidates.empty:
            return "本次篩選沒有符合條件的可轉債標的。"

        rows = candidates.sort_values(
            by=["P值", "R值"],
            ascending=[False, True],
        ).head(max_rows)

        targets_info = []
        for idx, (_, row) in enumerate(rows.iterrows(), start=1):
            get = row.get
            targets_info.append(
                f"[{idx}] {get('名稱', '')}({get('代號', '')}) | "
                f"R={get('R值', '')} P={get('P值', '')} | "
                f"市價={get('CB市價', '')} | 溢價={get('溢/折價', '')}% | "
                f"轉換價值={get('轉換價值', '')}% | 餘額={get('餘額', '')}% | "
                f"均量={get('均量', '')}張 | 標籤={get('策略標籤', '')}"
            )

        prompt = f"""
# Role
你是一位精通台股可轉債與「鄭大 CB 策略」的投資研究助理。

# Input
以下是 CBAS 系統依照濾網與 R/P 模型選出的標的：
{chr(10).join(targets_info)}

# Decision Rules
1. R 值越低代表風險越低，P 值越高代表潛力越高。
2. 若 R 值偏高、溢價過高或價格遠離債底，必須明確提醒追高風險。
3. 不要給保證獲利語氣，輸出應定位為投資研究參考。
4. 優先指出 3 到 5 檔最值得追蹤的標的，並說明原因。

# Output
請用繁體中文輸出：
- 今日總結
- 精選追蹤名單
- 風險提醒
- 明日/下次追蹤重點
"""
        return self.ask(prompt)
