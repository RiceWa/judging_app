import streamlit as st
from db import init_db, authenticate_user
import views.judges_page as judges_page
import views.competitors_page as competitors_page
import views.scoring_page as scoring_page
import views.leaderboard_page as leaderboard_page

def main():
    # Setup Streamlit page
    st.set_page_config(page_title="Judging Tool", layout="wide")

    # Create DB tables if needed
    init_db()

    user = st.session_state.get("user")
    if not user:
        render_login()
        return

    # Sidebar navigation
    st.sidebar.title("Judging Tool")
    st.sidebar.write(f"Logged in as **{user['username']}** ({user['role']})")
    if st.sidebar.button("Log out"):
        st.session_state.pop("user", None)
        st.rerun()

    if user["role"] == "admin":
        page = st.sidebar.radio("Navigation", [
            "Manage Judges", "Manage Competitors", "Leaderboard"
        ])
    else:
        page = st.sidebar.radio("Navigation", [
            "Enter Scores"
        ])

    # Route to correct page
    if page == "Manage Judges":
        judges_page.show()
    elif page == "Manage Competitors":
        competitors_page.show()
    elif page == "Enter Scores":
        scoring_page.show()
    elif page == "Leaderboard":
        leaderboard_page.show()

def render_login():
    st.title("Judging Tool")
    st.subheader("Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

        if submitted:
            user = authenticate_user(username.strip(), password)
            if user:
                st.session_state["user"] = dict(user)
                st.rerun()
            else:
                st.error("Invalid username or password.")
    st.stop()

if __name__ == "__main__":
    main()
