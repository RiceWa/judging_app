import streamlit as st
from db import get_competitors, replace_scores_for_judge, get_scores_for_judge, get_judge_by_id

def show():
    user = st.session_state.get("user")
    if not user or user.get("role") != "judge":
        st.error("Judge access required to enter scores.")
        st.stop()

    st.header("Enter Scores")

    # Load judges and competitors
    competitors = get_competitors()

    judge_id = user.get("judge_id")
    judge = get_judge_by_id(judge_id) if judge_id else None
    if not judge:
        st.error("Judge account is missing a profile.")
        return
    if not competitors:
        st.warning("Add competitors first.")
        return

    # Fetch this judge's existing scores
    existing_scores = get_scores_for_judge(judge_id)

    st.write("---")
    st.write(f"Enter scores for each competitor as **{judge['name']}**:")

    scores = {}

    # Form to submit all scores at once
    with st.form("score_form"):
        for c in competitors:
            col1, col2 = st.columns([2, 1])

            # Competitor info
            with col1:
                st.write(f"**{c['name']}**")

            # Score input, pre-filled with existing score if available
            with col2:
                value = st.number_input(
                    f"Score (ID {c['id']})",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.5,
                    value=float(existing_scores.get(c["id"], 0.0)),
                    # key includes judge_id so each judge gets independent widgets
                    key=f"score_{judge_id}_{c['id']}"
                )
                scores[c["id"]] = value

        submitted = st.form_submit_button("Save scores")

        if submitted:
            # Only save non-zero scores
            cleaned = {cid: val for cid, val in scores.items() if val > 0}
            replace_scores_for_judge(judge_id, cleaned)
            st.success("Scores saved!")
