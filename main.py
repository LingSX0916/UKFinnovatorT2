from dotenv import load_dotenv
load_dotenv()

from backend.api import app

if __name__ == "__main__":
    print("Starting FCA Promotions Triage Console API on http://localhost:5000")
    print("Then run:  streamlit run frontend/app.py")
    app.run(debug=True, port=5000)
