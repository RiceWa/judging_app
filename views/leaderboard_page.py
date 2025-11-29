import streamlit as st
from db import get_leaderboard

def show():
    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Admin access required.")
        st.stop()

    st.header("Leaderboard")
    if st.button("Refresh leaderboard"):
        st.rerun()

    # Get aggregated scores
    results = get_leaderboard()
    if not results:
        st.info("No scores yet.")
        return

    # Convert result rows into dict format for Streamlit
    data = []
    for idx, row in enumerate(results, start=1):
        data.append({
            "Rank": idx,
            "Competitor": row["competitor_name"],
            "Number of Judges that entered scores": row["num_scores"],
            "Total Score": round(row["total_score"], 2),
            "Average Score": round(row["avg_score"], 2),
        })

    st.dataframe(data)
