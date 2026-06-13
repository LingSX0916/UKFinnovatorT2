Drop financial adverts here for scanning.

Each file should be a plain .txt containing the full text of one advert or promotion.
The scanner reads any file from this folder and runs it through the FCA rules in FCA.md.

The API will return RED, AMBER, or GREEN based on its own reasoning against those rules.
No pre-labelling needed — just paste the raw advert text and scan.

Example usage (from project root):
  python main.py                      # start Flask API on port 5000
  streamlit run frontend/app.py       # start UI on port 8501
  Then paste the advert text into the UI, or POST to http://localhost:5000/scan
