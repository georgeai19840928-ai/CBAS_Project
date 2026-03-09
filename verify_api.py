import os
from dotenv import load_dotenv
from google import genai

load_dotenv(override=True)
api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key config length: {len(api_key) if api_key else 0}")

client = genai.Client(api_key=api_key)

try:
    print("Testing gemini-2.5-flash...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say 'OK'"
    )
    print("gemini-2.5-flash result:", response.text)
except Exception as e:
    print("gemini-2.5-flash error:", e)

try:
    print("Testing gemini-2.0-flash-lite-001...")
    response = client.models.generate_content(
        model="gemini-2.0-flash-lite-001",
        contents="Say 'OK'"
    )
    print("gemini-2.0-flash-lite-001 result:", response.text)
except Exception as e:
    print("gemini-2.0-flash-lite-001 error:", e)

try:
    print("Testing gemini-2.0-flash-lite-preview-02-05...")
    response = client.models.generate_content(
        model="gemini-2.0-flash-lite-preview-02-05",
        contents="Say 'OK'"
    )
    print("gemini-2.0-flash-lite-preview-02-05 result:", response.text)
except Exception as e:
    print("gemini-2.0-flash-lite-preview-02-05 error:", e)
