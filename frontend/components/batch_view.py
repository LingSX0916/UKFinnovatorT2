import streamlit as st
import requests

_STATUS_EMOJI = {"RED": "🔴", "AMBER": "🟡", "GREEN": "🟢"}
_SORT_KEY = {"RED": 0, "AMBER": 1, "GREEN": 2, "ERROR": 3}
_API_URL = "http://localhost:5000/scan"


def _scan_one(advert: str) -> dict:
    try:
        r = requests.post(_API_URL, json={"advertText": advert}, timeout=30)
        result = r.json()
    except Exception as e:
        result = {"overall_status": "ERROR", "overall_summary": str(e), "rules": []}
    result["_snippet"] = advert[:100] + ("..." if len(advert) > 100 else "")
    return result


def render_batch_view(adverts: list[str]) -> None:
    if not adverts:
        st.info("No adverts to scan.")
        return

    results = []
    progress = st.progress(0, text="Scanning adverts...")
    for i, advert in enumerate(adverts):
        results.append(_scan_one(advert))
        progress.progress((i + 1) / len(adverts), text=f"Scanned {i + 1} of {len(adverts)}")
    progress.empty()

    results.sort(key=lambda r: _SORT_KEY.get(r.get("overall_status"), 9))

    total = len(results)
    red_count = sum(1 for r in results if r.get("overall_status") == "RED")
    amber_count = sum(1 for r in results if r.get("overall_status") == "AMBER")
    green_count = sum(1 for r in results if r.get("overall_status") == "GREEN")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total scanned", total)
    col2.metric("🔴 RED", red_count)
    col3.metric("🟡 AMBER", amber_count)
    col4.metric("🟢 GREEN", green_count)

    st.markdown("---")
    for r in results:
        status = r.get("overall_status", "UNKNOWN")
        emoji = _STATUS_EMOJI.get(status, "⚪")
        hits = r.get("warning_list_hits", [])
        warning_badge = "  🚨 **WARNING LIST HIT**" if hits else ""
        st.markdown(
            f"{emoji} **{status}**{warning_badge} — {r.get('overall_summary', '')}  \n"
            f"_{r.get('_snippet', '')}_"
        )
        st.divider()
