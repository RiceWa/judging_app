import streamlit as st
from db import save_banner_image, get_banner_image, delete_banner_image


def show():
    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Admin access required.")
        st.stop()

    st.header("Customize")

    st.write("Upload a banner image that will be shown to judges on the scoring page. Size limit 1MB.")

    existing = get_banner_image()
    if existing and existing.get("data"):
        st.subheader("Current banner")
        st.image(existing["data"], width="stretch")
        if st.button("Remove banner"):
            delete_banner_image()
            st.success("Banner removed.")
            st.rerun()

    st.write("---")

    uploaded = st.file_uploader(
        "Choose image file",
        type=["png", "jpg", "jpeg", "webp"],
        key="banner_uploader",
    )
    if uploaded:
        data = uploaded.getvalue()
        max_bytes = 1 * 1024 * 1024  # 1 MB
        if len(data) > max_bytes:
            size_kb = len(data) / 1024
            st.error(
                f"File too large ({size_kb:.0f} KB). Maximum upload size is 1 MB. "
                "Please choose a smaller image or resize before uploading."
            )
        else:
            st.image(data, caption="Preview", width="stretch")
            if st.button("Upload banner"):
                save_banner_image(data, uploaded.name, uploaded.type)
                st.success("Banner uploaded.")
                st.rerun()
