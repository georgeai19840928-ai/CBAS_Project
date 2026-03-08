import time
import streamlit as st
try:
    from google import genai
except ImportError:
    pass

class AIAgent:
    def __init__(self, api_key):
        self.client = None
        if api_key:
            try:
                self.client = genai.Client(api_key=api_key)
            except Exception:
                pass

    def ask(self, prompt, max_retries=3, base_delay=10):
        if not self.client:
            return "⚠️ API Key Error: Client not initialized"
        
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash-lite-001", 
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