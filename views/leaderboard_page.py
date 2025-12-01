import streamlit as st
from db import get_leaderboard
import io
import csv
from datetime import datetime

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
    # Assign ranks so that tied average scores share the same rank
    data = []
    # Dense ranking: ties receive the same rank, and the next distinct score increments rank by 1
    prev_avg = None
    current_rank = 0
    for row in results:
        avg = row.get("avg_score", 0)
        if prev_avg is None:
            current_rank = 1
        elif avg != prev_avg:
            current_rank += 1
        rank = current_rank
        data.append({
            "Rank": rank,
            "Competitor": row["competitor_name"],
            "Number of Judges that entered scores": row["num_scores"],
            "Total Score": round(row["total_score"], 2),
            "Average Score": round(avg, 2),
        })
        prev_avg = avg

    st.dataframe(data)

    # CSV export: create CSV bytes and provide a download button
    if data:
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=[
            "Rank",
            "Competitor",
            "Number of Judges that entered scores",
            "Total Score",
            "Average Score",
        ])
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        csv_bytes = csv_buffer.getvalue().encode("utf-8")
        filename = f"leaderboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        st.download_button(
            label="Export",
            data=csv_bytes,
            file_name=filename,
            mime="text/csv",
            help="Download current leaderboard as a CSV file",
        )
