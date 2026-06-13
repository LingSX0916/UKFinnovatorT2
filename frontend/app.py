import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import requests
from frontend.components.result_card import render_result_card
from frontend.components.batch_view import render_batch_view

st.set_page_config(
    page_title="FCA Promotions Triage Console",
    page_icon="⚖️",
    layout="wide",
)

st.title("⚖️ FCA Promotions Triage Console")
st.caption("Automated compliance screening · FG24/1 · COBS 4 · s21 FSMA · FCA Warning List")

API_URL = "http://localhost:5000/scan"

tab_single, tab_batch = st.tabs(["Single advert", "Batch triage"])

with tab_single:
    advert_text = st.text_area(
        "Paste a financial advert here",
        height=200,
        placeholder="Paste advert text and press Scan...",
    )
    if st.button("Scan", type="primary") and advert_text.strip():
        with st.spinner("Scanning against FCA rules..."):
            try:
                response = requests.post(
                    API_URL,
                    json={"advertText": advert_text},
                    timeout=30,
                )
                render_result_card(response.json())
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach the backend. Make sure the Flask API is running: python main.py")
            except Exception as e:
                st.error(f"Scan failed: {e}")

with tab_batch:
    st.markdown("Paste one advert per block, separated by `---`")
    batch_input = st.text_area(
        "Adverts (separated by ---)",
        height=300,
        placeholder="Advert one text...\n---\nAdvert two text...\n---\nAdvert three text...",
    )
    if st.button("Scan all", type="primary") and batch_input.strip():
        adverts = [a.strip() for a in batch_input.split("---") if a.strip()]
        render_batch_view(adverts)
