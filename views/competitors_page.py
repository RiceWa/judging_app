import streamlit as st
from db import get_competitors, insert_competitor, update_competitor, delete_competitor

def show():
    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Admin access required.")
        st.stop()

    st.header("Manage Competitors")

    # Form to add a new competitor
    with st.form("add_competitor"):
        name = st.text_input("Competitor name")
        submitted = st.form_submit_button("Add competitor")

        if submitted:
            if not name.strip():
                st.error("Name is required.")
            else:
                insert_competitor(name.strip())
                st.success(f"Added competitor: {name}")

    st.subheader("Current competitors")

    # Load and display competitor list
    competitors = get_competitors()
    if not competitors:
        st.info("No competitors yet.")
        return

    for comp in competitors:
        with st.expander(comp["name"]):
            with st.form(f"edit_comp_{comp['id']}"):
                name_val = st.text_input("Name", value=comp["name"])
                save = st.form_submit_button("Save changes")
                if save:
                    if not name_val.strip():
                        st.error("Name is required.")
                    else:
                        update_competitor(comp["id"], name_val.strip())
                        st.success("Competitor updated.")
                        st.rerun()

            with st.form(f"delete_comp_{comp['id']}"):
                st.write("Delete this competitor and all related scores?")
                delete_pressed = st.form_submit_button("Delete competitor")
                if delete_pressed:
                    delete_competitor(comp["id"])
                    st.success("Competitor deleted.")
                    st.rerun()
