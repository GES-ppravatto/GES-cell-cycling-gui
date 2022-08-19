from io import BytesIO
import streamlit as st

from core.session_state_manager import save_session_state, load_session_state


st.title("Analysis Import-Export page")

texport, timport = st.tabs(["📤 Export", "📥 Import"])

with texport:
    st.markdown("### Session export:")
    st.write("""In this tab you can export the current status of the analysis. The obtained
    file can than be shared among users operating the same version of the program.""")

    col1, col2 = st.columns([3, 1])

    with col1:
        picklename = st.text_input(
            "Enter the name of the file to save", value="my_analysis"
        )

    with col2:
        st.write("")
        st.write("")
        st.download_button(
            label="💾 Save status",
            data=save_session_state(),
            file_name=f"{picklename}.pickle",
        )

with timport:

    st.markdown("### Session import:")
    st.write("""In this tab you can load a previous state of the analysis session starting
    from a `.pickle` file.""")

    with st.form("Load", clear_on_submit=True):

        source = st.file_uploader(
            "Select the file", accept_multiple_files=False, type="pickle"
        )

        submitted = st.form_submit_button("Submit")

    # If the button has been pressed and the file list is not empty load the files in the experiment
    if submitted and source:
        load_session_state(BytesIO(source.getvalue()))
        st.experimental_rerun()