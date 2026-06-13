"""Flask blueprint for the KYB & UK Sanctions module.

Extends the existing Flask app (backend/api.py) with a namespaced /api surface so
it sits cleanly alongside the promotions /scan and /complaints routes. All
Companies House and Supabase access is server-side; no secret ever reaches the
client. Call register_kyb(app) once from the main app factory.

SECURITY — production gap (next step, not built for the hackathon demo): these
routes have no authentication, matching the rest of the demo app. Before any real
deployment, put an auth layer in front of the write routes (POST /screen, POST
/decision), derive the audit `actor`/`run_by` from the authenticated principal
(this module already prefers an `X-KYB-User` header over the request body), and
lock CORS to the known frontend origin. The company-number is validated against a
strict pattern (see before_request) to block SSRF / path traversal.
"""
from __future__ import annotations

import json
import os
import threading

from flask import Blueprint, jsonify, request, Response

from .companies_house import CompaniesHouseClient, valid_company_number
from . import screening
from . import store as kyb_store

kyb_bp = Blueprint("kyb", __name__)

_client: CompaniesHouseClient | None = None


@kyb_bp.before_request
def _validate_number():
    """Reject a malformed company number before it reaches a URL or filesystem path
    (SSRF / path-traversal guard). Applies to every /api/company/<number>/... route."""
    num = (request.view_args or {}).get("number")
    if num is not None and not valid_company_number(num):
        return jsonify({"error": "invalid company number"}), 400


def _actor(body: dict, *keys: str) -> str:
    """Derive the audit actor from an auth header if present, never trusting the
    request body alone. NOTE: production must put a real auth layer in front of
    these routes (see SECURITY note in api.py / README) — this is demo-grade."""
    hdr = request.headers.get("X-KYB-User")
    if hdr:
        return hdr
    for k in keys:
        if body.get(k):
            return str(body[k])
    return "anonymous"


def _get_client() -> CompaniesHouseClient:
    global _client
    if _client is None:
        _client = CompaniesHouseClient()
    return _client


@kyb_bp.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "companies_house": _get_client().mode,
        "sanctions_index": screening.index_info(),
        "persistence": kyb_store.enabled(),
    })


@kyb_bp.get("/api/company/search")
def company_search():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"items": [], "error": "q is required"}), 400
    return jsonify({"items": _get_client().search_companies(q)})


@kyb_bp.get("/api/company/<number>")
def company_dossier(number):
    dossier = screening.get_dossier(_get_client(), number)
    if "error" in dossier:
        return jsonify(dossier), 404
    return jsonify(dossier)


@kyb_bp.get("/api/company/<number>/officers")
def company_officers(number):
    return jsonify({"items": _get_client().get_officers(number)})


@kyb_bp.get("/api/company/<number>/psc")
def company_psc(number):
    return jsonify({"items": _get_client().get_pscs(number)})


@kyb_bp.get("/api/company/<number>/filing-history")
def company_filings(number):
    return jsonify({"items": _get_client().get_filing_history(number)})


@kyb_bp.get("/api/company/<number>/ownership-graph")
def company_graph(number):
    from .graph import build_ownership_graph
    return jsonify(screening.graph_public(build_ownership_graph(_get_client(), number)))


@kyb_bp.post("/api/company/<number>/screen")
def company_screen(number):
    body = request.get_json(silent=True) or {}
    run_by = _actor(body, "run_by")
    as_of = body.get("as_of")
    if as_of is not None and not isinstance(as_of, str):
        as_of = None
    result = screening.screen_company(
        _get_client(), number, run_by=run_by, as_of=as_of,
        store=kyb_store if kyb_store.enabled() else None)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


@kyb_bp.post("/api/screening/match/<match_id>/decision")
def match_decision(match_id):
    body = request.get_json(silent=True) or {}
    decision = (body.get("decision") or "").lower()
    if decision not in ("confirmed", "dismissed", "pending"):
        return jsonify({"error": "decision must be confirmed | dismissed | pending"}), 400
    note = str(body.get("note") or "")[:2000]
    reviewer = _actor(body, "reviewer")
    saved = False
    if kyb_store.enabled():
        try:
            kyb_store.record_decision(match_id, decision, note, reviewer)
            kyb_store.audit(reviewer, f"match.{decision}", "screening_match", match_id,
                            {"note": note})
            saved = True
        except Exception as exc:  # pragma: no cover
            from flask import current_app
            current_app.logger.warning("match_decision persistence failed: %s", exc)
            return jsonify({"saved": False, "error": "persistence error"}), 502
    return jsonify({"saved": saved, "persistence": kyb_store.enabled(),
                    "match_id": match_id, "decision": decision})


@kyb_bp.get("/api/company/<number>/export")
def company_export(number):
    fmt = (request.args.get("format") or "json").lower()
    result = screening.screen_company(_get_client(), number, run_by="export")
    if "error" in result:
        return jsonify(result), 404
    if fmt == "pdf":
        try:
            from .export_pdf import render_case_pdf
            pdf = render_case_pdf(result)
            return Response(pdf, mimetype="application/pdf", headers={
                "Content-Disposition": f"attachment; filename=KYB-{number}.pdf"})
        except Exception as exc:  # reportlab not installed, etc.
            from flask import current_app
            current_app.logger.warning("PDF export failed: %s", exc)
            return jsonify({"error": "PDF export unavailable; use format=json."}), 501
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    return Response(payload, mimetype="application/json", headers={
        "Content-Disposition": f"attachment; filename=KYB-{number}.json"})


def register_kyb(app, *, warm_index: bool = True) -> None:
    """Mount the KYB blueprint on the main Flask app and (optionally) warm the
    sanctions index in the background so the first /screen call is fast."""
    app.register_blueprint(kyb_bp)
    if warm_index and os.environ.get("KYB_WARM_INDEX", "1") != "0":
        threading.Thread(target=screening.get_index, daemon=True).start()
