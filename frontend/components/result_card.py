import streamlit as st

_STATUS_EMOJI = {"RED": "🔴", "AMBER": "🟡", "GREEN": "🟢"}
_VERDICT_EMOJI = {"PASS": "✅", "FAIL": "❌", "FLAG": "⚠️"}
_STATUS_COLOUR = {"RED": "red", "AMBER": "orange", "GREEN": "green"}


def render_result_card(result: dict) -> None:
    status = result.get("overall_status", "UNKNOWN")
    emoji = _STATUS_EMOJI.get(status, "⚪")
    colour = _STATUS_COLOUR.get(status, "gray")

    st.markdown(
        f"<h2 style='color:{colour}'>{emoji} {status}</h2>",
        unsafe_allow_html=True,
    )
    st.write(result.get("overall_summary", ""))

    hits = result.get("warning_list_hits", [])
    if hits:
        st.error(f"⚠️ ON FCA WARNING LIST: {', '.join(hits)}")

    st.markdown("---")
    st.markdown("### Rule-by-rule analysis")

    for rule in result.get("rules", []):
        verdict = rule.get("verdict", "")
        pill = _VERDICT_EMOJI.get(verdict, "")
        label = f"{pill} {rule['id']} — {rule['name']}  `{rule.get('provision', '')}`"
        with st.expander(label, expanded=(verdict == "FAIL")):
            st.write(rule.get("reason", ""))
            evidence = rule.get("evidence", "")
            if evidence:
                st.markdown(f"> *\"{evidence}\"*")

    rewrite = result.get("suggested_rewrite")
    if rewrite:
        st.markdown("---")
        st.markdown("### Suggested compliant rewrite")
        st.info(rewrite)
