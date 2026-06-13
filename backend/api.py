from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from backend.scanner import scan_advert
from backend.warning_list_checker import find_warning_list_matches

_ROOT = Path(__file__).parent.parent
_WEB_DIR = _ROOT / "web"

# Serve the Triage web frontend from the same origin as the API → no CORS,
# one process, one `python main.py` to run the whole thing.
app = Flask(__name__, static_folder=str(_WEB_DIR), static_url_path="")
CORS(app)


@app.route("/")
def index():
    return send_from_directory(_WEB_DIR, "Triage.html")


@app.route("/FCA.md")
def rulebook():
    # The same rulebook the model is grounded in; the frontend fetches it
    # only to display the rule count on the board.
    return send_from_directory(_ROOT, "FCA.md", mimetype="text/markdown")


@app.route("/scan", methods=["POST"])
def scan():
    data = request.get_json(force=True) or {}
    advert = (data.get("advert") or data.get("advertText") or "").strip()
    if not advert:
        return jsonify({"error": "advert text is required"}), 400

    promoter = (data.get("promoter") or "").strip()
    context = (data.get("context") or "").strip()

    try:
        result = scan_advert(advert, promoter=promoter, context=context)
    except Exception as exc:  # missing/invalid key, model/parse error, etc.
        # Return clean JSON so the frontend falls back to its local heuristic
        # instead of choking on a 500 HTML page.
        app.logger.warning("scan failed: %s", exc)
        return jsonify({"error": f"triage model call failed: {exc}"}), 502

    # Authoritatively cross-reference the advert + promoter against the local
    # FCA Warning List. A hit forces RED regardless of the model's own verdict.
    warning_hits = find_warning_list_matches(advert, promoter)
    result["warning_list_hits"] = warning_hits
    if warning_hits:
        result["warning_list_hit"] = True
        result["overall_verdict"] = "RED"
        result["overall_status"] = "RED"  # legacy key, kept in sync

    return jsonify(result)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    import os
    app.run(debug=True, port=int(os.environ.get("PORT", "5050")))
