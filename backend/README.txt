Python backend — rules engine, FCA compliance logic, and API.

Files:
  scanner.py              — core scan function. Takes advert text, sends it to the OpenAI API
                            with FCA.md as the system prompt, returns the verdict as a parsed dict.
                            Rules live in FCA.md at the project root — edit there, not here.

  warning_list_checker.py — loads data/warning_list.json and fuzzy-matches firm names from
                            scan results. Forces overall_status to RED on a hit.

  api.py                  — Flask app exposing POST /scan so the frontend can call it.
                            Also handles the Warning List cross-check after the LLM call.

  requirements.txt        — Python dependencies. Install with: pip install -r requirements.txt

To run the API server:
  python main.py

Requires .env at the project root with:
  OPENAI_API_KEY=your_key_here
