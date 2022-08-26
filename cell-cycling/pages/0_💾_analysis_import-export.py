import logging, traceback, os, sys, pickle
from io import BytesIO
import streamlit as st

from core.session_state_manager import save_session_state, load_session_state


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#logging.basicConfig(filename=st.session_state["LogName"])


def print_log_entry(name, save: bool = True):
    if save:
        logger.info(f"Saving session state to '{name}.pickle'")
    else:
        logger.info(f"Loading session state from '{name}.pickle'")


logger.info("RUNNING export/import page rendering")

try:
    st.title("Analysis Import-Export page")

    texport, timport = st.tabs(["📤 Export", "📥 Import"])

    with texport:
        st.markdown("### Session export:")
        st.write(
            """In this tab you can export the current status of the analysis. The obtained
        file can than be shared among users operating the same version of the program."""
        )

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
                on_click=print_log_entry,
                args=[picklename],
                kwargs={"save": True},
            )

    with timport:

        st.markdown("### Session import:")
        st.write(
            """In this tab you can load a previous state of the analysis session starting
        from a `.pickle` file."""
        )

        with st.form("Load", clear_on_submit=True):

            source = st.file_uploader(
                "Select the file", accept_multiple_files=False, type="pickle"
            )

            submitted = st.form_submit_button("Submit")

        # If the button has been pressed and the file list is not empty load the files in the experiment
        if submitted and source:
            print_log_entry(source.name, save=False)
            load_session_state(BytesIO(source.getvalue()))
            st.experimental_rerun()

except st._RerunException:
    logger.info("EXPERIMENTAL RERUN CALLED")
    raise

except:
    logger.exception(
        f"Unexpected exception occurred during export/import page execution:\n\n {traceback.print_exception(*sys.exc_info())}"
    )
    dump_index = 0
    while True:
        dump_file = f"./GES_echem_gui_dump_{dump_index}.pickle"
        if os.path.isfile(dump_file):
            dump_index += 1
        else:
            logger.critical(f"Dumping the content of the session state to '{dump_file}'")
            with open(dump_file, "wb") as file:
                pickle.dump(dict(st.session_state), file, protocol=pickle.HIGHEST_PROTOCOL)
            break
    raise

else:
    logger.debug("-> export/import page run completed succesfully")
