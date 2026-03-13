import os
import sys

# This is a proxy file to ensure Zeabur can still boot if it's looking for main.py.
# All logic has been consolidated into app.py.

if __name__ == "__main__":
    # Path to the actual app
    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    
    # Check if we are running via streamlit
    if "streamlit" in sys.modules or os.environ.get("STREAMLIT_SERVER_PORT"):
        # If already in streamlit environment, just execute app.py
        with open(app_path, "r", encoding="utf-8") as f:
            exec(f.read(), globals())
    else:
        # Otherwise, launch it
        os.system(f"streamlit run {app_path}")
