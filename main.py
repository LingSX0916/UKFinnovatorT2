import os

from dotenv import load_dotenv
load_dotenv()

from backend.api import app

if __name__ == "__main__":
    # Default 5050: on macOS, port 5000 is taken by AirPlay/Control Center.
    # Override with PORT=... if needed.
    port = int(os.environ.get("PORT", "5050"))
    print("FCA Promotions Triage Console")
    print(f"  Web UI + API:  http://localhost:{port}")
    print("  (Streamlit UI still available via:  streamlit run frontend/app.py)")
    app.run(debug=True, port=port)
