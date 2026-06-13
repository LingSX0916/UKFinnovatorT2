Streamlit frontend — everything the judges see.

Files:
  app.py                      — entry point. Paste box, Scan button, single-advert result view,
                                and a batch triage tab for scanning multiple adverts at once.

  components/result_card.py   — renders the RED/AMBER/GREEN verdict card with per-rule rows,
                                quoted evidence, Warning List badge, and suggested rewrite.

  components/batch_view.py    — renders the supervisory triage table sorted by severity,
                                plus summary metrics (total scanned, % non-compliant, top breach).

  static/                     — images, CSS, logos used in the UI.

To run the frontend (start the backend API first):
  streamlit run frontend/app.py

The frontend calls the backend at http://localhost:5000/scan.
Make sure the Flask API is running before opening the Streamlit app.
