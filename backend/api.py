from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from backend.scanner import scan_advert
from backend.warning_list_checker import check_warning_list

app = Flask(__name__)
CORS(app)


@app.route("/scan", methods=["POST"])
def scan():
    data = request.get_json(force=True)
    advert_text = data.get("advertText", "").strip()
    if not advert_text:
        return jsonify({"error": "advertText is required"}), 400

    result = scan_advert(advert_text)

    warning_hits = check_warning_list(
        result.get("named_firms", []),
        result.get("named_people", []),
    )
    if warning_hits:
        result["warning_list_hits"] = warning_hits
        result["overall_status"] = "RED"

    return jsonify(result)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
