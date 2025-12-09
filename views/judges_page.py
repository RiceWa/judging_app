import streamlit as st
from db import (
    get_judges_with_user,
    create_judge_account,
    update_judge_account,
    delete_judge_account,
)
from pymongo.errors import DuplicateKeyError

def show():
    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Admin access required.")
        st.stop()

    st.header("Manage Judges")

    # Flash success from previous add submission
    add_success = st.session_state.pop("judge_add_success", None)
    if add_success:
        st.success(add_success)

    # If prior submission requested a reset, clear the widget state before rendering inputs
    if st.session_state.pop("reset_add_judge_form", False):
        for key in ("add_judge_name", "add_judge_email", "add_judge_username", "add_judge_password"):
            st.session_state[key] = ""

    # Form to add a new judge + login
    with st.form("add_judge"):
        name = st.text_input("Judge name", key="add_judge_name")
        email = st.text_input("Judge email", key="add_judge_email")
        username = st.text_input("Judge username", key="add_judge_username")
        password = st.text_input("Temporary password", type="password", key="add_judge_password")
        submitted = st.form_submit_button("Add judge")

        if submitted:
            if not name.strip() or not email.strip() or not username.strip() or not password:
                st.error("Name, email, username, and password are required.")
            else:
                try:
                    create_judge_account(
                        name.strip(),
                        email.strip(),
                        username.strip(),
                        password
                    )
                    st.session_state["reset_add_judge_form"] = True
                    st.session_state["judge_add_success"] = f"Added judge account for: {name}"
                    st.rerun()
                except DuplicateKeyError:
                    message = "Email or username already exists."
                    st.error(message)

    st.subheader("Current judges")

    # Load and display judge list with edit/delete controls
    judges = get_judges_with_user()
    if not judges:
        st.info("No judges yet.")
        return

    for judge in judges:
        with st.expander(f"{judge['name']} ({judge['email']})"):
            # Inline edit form
            with st.form(f"edit_judge_{judge['id']}"):
                name_val = st.text_input("Name", value=judge["name"])
                email_val = st.text_input("Email", value=judge["email"])
                username_val = st.text_input("Username", value=judge["username"] or "")
                password_val = st.text_input("New password (leave blank to keep)", type="password")
                updated = st.form_submit_button("Save changes")

                if updated:
                    if not name_val.strip() or not email_val.strip() or not username_val.strip():
                        st.error("Name, email, and username are required.")
                    else:
                        try:
                            update_judge_account(
                                judge["id"],
                                name_val.strip(),
                                email_val.strip(),
                                username_val.strip(),
                                password=password_val or None,
                            )
                            st.success("Judge updated.")
                            st.rerun()
                        except DuplicateKeyError:
                            st.error("Email or username already exists.")

            # Inline delete form
            with st.form(f"delete_judge_{judge['id']}"):
                st.write("Delete this judge account and all their scores?")
                delete_pressed = st.form_submit_button("Delete judge")
                if delete_pressed:
                    delete_judge_account(judge["id"])
                    st.success("Judge deleted.")
                    st.rerun()
