import streamlit as st
from db import (
    get_competitors,
    get_judge_by_id,
    get_questions,
    get_answers_for_judge_competitor,
    save_answers_for_judge,
)

def show():
    user = st.session_state.get("user")
    if not user or user.get("role") != "judge":
        st.error("Judge access required to enter scores.")
        st.stop()

    st.header("Enter Scores")

    # Show success toast if flagged from previous save
    if st.session_state.pop("score_saved", False):
        st.toast("Scores saved.", icon="✅")

    # Load competitors for scoring and active questions
    competitors = get_competitors()
    questions = get_questions()

    judge_id = user.get("judge_id")
    judge = get_judge_by_id(judge_id) if judge_id else None
    if not judge:
        st.error("Judge account is missing a profile.")
        return
    if not competitors:
        st.warning("Add competitors first.")
        return

    if not questions:
        st.warning("Admin needs to add questions before scoring.")
        return

    st.write("---")

    # Competitor selector
    competitor_options = {f"{c['name']}": c for c in competitors}
    selected_label = st.selectbox("Select a competitor", list(competitor_options.keys()), index=0)
    comp = competitor_options[selected_label]

    st.write(f"### Scoring: {comp['name']}")

    # Load existing answers
    existing_answers = get_answers_for_judge_competitor(judge_id, comp["id"])
    answers = {}

    st.write("#### Questions")
    for q in questions:
        display_label = f"{q['prompt']}"
        stored_value = int(existing_answers.get(q["id"], 0))
        stored_choice = int(stored_value / 10) if stored_value else 0
        choice = st.radio(
            display_label,
            options=list(range(0, 11)),
            format_func=lambda v: "Not set" if v == 0 else str(v),
            index=stored_choice,
            horizontal=True,
            key=f"q_radio_{judge_id}_{comp['id']}_{q['id']}"
        )
        answers[q["id"]] = choice

    if st.button("Save scores", key=f"save_scores_{comp['id']}"):
        # Require every question to be scored (non-zero) before saving
        missing = [q for q in questions if answers.get(q["id"], 0) == 0]
        if missing:
            st.error("Please score all questions before saving.")
        else:
            cleaned = {qid: val * 10 for qid, val in answers.items()}
            save_answers_for_judge(judge_id, comp["id"], cleaned)
            st.session_state["score_saved"] = True
            st.rerun()
