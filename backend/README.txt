Python backend — rules engine, FCA compliance logic, and API.

Files:
  rules_prompt.py         — the 8-rule system prompt (R1–R8) stored as a string constant.
                            This is the moat. The model is a commodity; the encoded regulatory
                            logic is not. Do not change this without testing all three demo adverts.

  scanner.py              — core scan function. Takes advert text, calls the Anthropic API with
                            the system prompt, returns the verdict as a parsed Python dict.

  warning_list_checker.py — loads data/warning_list.json and fuzzy-matches firm names from
                            scan results. Forces overall_status to RED on a hit.

  api.py                  — Flask app exposing POST /scan so the frontend can call it.
                            Also handles the Warning List cross-check after the LLM call.

  requirements.txt        — Python dependencies. Install with: pip install -r requirements.txt

To run the API server:
  python main.py
  (or from this folder: python api.py)

Requires .env at the project root with:
  ANTHROPIC_API_KEY=your_key_here
