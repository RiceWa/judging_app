import streamlit as st
from db import get_competitors, insert_competitor, update_competitor, delete_competitor

def show():
    # Init add form state and pending clear
    if "new_competitor_name" not in st.session_state:
        st.session_state["new_competitor_name"] = ""
    if "new_competitor_notes" not in st.session_state:
        st.session_state["new_competitor_notes"] = ""
    if st.session_state.pop("clear_new_competitor", False):
        st.session_state["new_competitor_name"] = ""
        st.session_state["new_competitor_notes"] = ""

    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Admin access required.")
        st.stop()

    st.header("Manage Competitors")

    # Form to add a new competitor with optional notes
    with st.form("add_competitor"):
        name = st.text_input("Competitor name", key="new_competitor_name")
        notes = st.text_area("Notes (admin only)", key="new_competitor_notes")
        submitted = st.form_submit_button("Add competitor")

        if submitted:
            if not name.strip():
                st.error("Name is required.")
            else:
                insert_competitor(name.strip(), notes.strip())
                st.success(f"Added competitor: {name}")
                st.session_state["clear_new_competitor"] = True
                st.rerun()

    st.subheader("Current competitors")

    # Load and display competitor list with edit/delete
    competitors = get_competitors()
    if not competitors:
        st.info("No competitors yet.")
        return

    for comp in competitors:
        with st.expander(comp["name"]):
            # Inline edit form
            with st.form(f"edit_comp_{comp['id']}"):
                name_val = st.text_input("Name", value=comp["name"])
                notes_val = st.text_area("Notes (admin only)", value=comp.get("notes", ""))
                save = st.form_submit_button("Save changes")
                if save:
                    if not name_val.strip():
                        st.error("Name is required.")
                    else:
                        update_competitor(comp["id"], name_val.strip(), notes=notes_val.strip())
                        st.success("Competitor updated.")
                        st.rerun()

            # Inline delete form
            with st.form(f"delete_comp_{comp['id']}"):
                st.write("Delete this competitor?")
                delete_pressed = st.form_submit_button("Delete competitor")
                if delete_pressed:
                    delete_competitor(comp["id"])
                    st.success("Competitor deleted.")
                    st.rerun()
