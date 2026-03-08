import os
from dotenv import load_dotenv
from google import genai

# 1. 載入金鑰
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ 錯誤：找不到 API Key，請檢查 .env")
    exit()

print(f"🔍 正在使用金鑰：{api_key[:10]}... 連線查詢可用模型列表...")

# 2. 建立客戶端
client = genai.Client(api_key=api_key)

# 3. 列出所有模型 (最簡化版)
try:
    print("\n📋 您的帳號可使用的模型如下：")
    print("-" * 30)
    
    # 呼叫 list 方法
    pager = client.models.list()
    
    for model in pager:
        # 直接印出名字，不做任何過濾，避免錯誤
        # 通常格式會是 models/gemini-1.5-flash
        print(f"✅ {model.name}")
            
    print("-" * 30)
    print("💡 請從上面選一個名字 (建議選含有 'flash' 的)，")
    print("   並將 'models/' 去掉，填入 app.py 中。")
    print("   例如：看到 'models/gemini-1.5-flash-001' -> 就填 'gemini-1.5-flash-001'")

except Exception as e:
    print(f"❌ 查詢失敗: {e}")