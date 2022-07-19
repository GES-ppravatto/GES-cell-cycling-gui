import sys
import streamlit as st
import pandas as pd
from io import BytesIO
from os.path import splitext
from echemsuite.cellcycling.file_manager import FileManager, Instrument


def set_default() -> None:
    st.session_state["num_uploaded_files"] = 0
    st.session_state["uploader_expanded"] = True
    st.session_state["file_manager"] = None
    st.session_state["number_of_halfcycles_files"] = 0
    st.session_state["orderer_expander"] = True
    st.session_state["user_ordering_gui"] = {}
    st.session_state["custom_ordering"] = []
    st.session_state["clean_cycles"] = True
    st.session_state["cycles"] = []
    st.session_state["hidden_cycles"] = 0
    st.session_state["cellcycles"] = None


# inital setup of the session state variables
if "uploader_expanded" not in st.session_state:
    set_default()

st.set_page_config(layout="wide")

st.title("Cell-cycling")


with st.expander(
    "Files upload section", expanded=st.session_state["uploader_expanded"]
):
    with st.form("Upload form", clear_on_submit=True):
        files = st.file_uploader(
            "Select the cell-cycling datafiles", accept_multiple_files=True
        )
        submitted = st.form_submit_button("Load files")
        if submitted and files != []:
            st.session_state["num_uploaded_files"] = len(files)
            extensions = [splitext(file.name)[1] for file in files]
            if extensions.count(extensions[0]) != len(extensions):
                st.error(
                    "ERROR: Cannot operate on different file types"
                )  # Create custom exceptions

            else:
                bytestreams = {}
                for file in files:
                    stream = BytesIO(file.getvalue())
                    try:
                        stream.read().decode("utf-8")
                    except:
                        pass
                    else:
                        stream.seek(0)
                        bytestreams[file.name] = stream

                manager = FileManager(verbose=False)

                if extensions[0].lower() == ".dta":
                    manager._instrument = Instrument.GAMRY
                else:
                    st.error("ERROR: Unknown file extension detected.")
                    raise RuntimeError

                manager.bytestreams = bytestreams
                manager.parse()

                suggested_ordering = manager.suggest_ordering()
                st.write(suggested_ordering)

                st.session_state["number_of_halfcycles_files"] = len(manager.halfcycles)
                st.session_state["file_manager"] = manager

            st.session_state["uploader_expanded"] = False
            st.experimental_rerun()


if st.session_state["file_manager"] != None:

    manager = st.session_state["file_manager"]
    suggested_ordering = manager.suggest_ordering()

    with st.expander(
        "Ordering selection", expanded=st.session_state["orderer_expander"]
    ):

        with st.container():
            cname, ctstamp, ctype, ctime, corder = st.columns(5)
            with cname:
                st.markdown("**Filename**")
            with ctstamp:
                st.markdown("**Timestamp**")
            with ctype:
                st.markdown("**Type**")
            with ctime:
                st.markdown("**Runtime (s)**")
            with corder:
                st.markdown("**ID selector**")

        for level, block in enumerate(suggested_ordering):
            for n, entry in enumerate(block):
                with st.container():
                    cname, ctstamp, ctype, ctime, corder = st.columns(5)
                    with cname:
                        st.write(entry)
                    with ctstamp:
                        st.write(manager.halfcycles[entry].timestamp)
                    with ctype:
                        st.write(manager.halfcycles[entry].halfcycle_type)
                    with ctime:
                        st.write(manager.halfcycles[entry].time.iloc[-1])
                    with corder:
                        st.session_state["user_ordering_gui"][f"{level}:{n}"] = int(
                            st.number_input(
                                "halfcycle ID:",
                                min_value=0,
                                value=level,
                                step=1,
                                key=level
                                * st.session_state["number_of_halfcycles_files"]
                                + n,
                            )
                        )

        max_level = max(st.session_state["user_ordering_gui"].values())

        missing = []
        for halfcycle_id in range(max_level):
            if halfcycle_id not in st.session_state["user_ordering_gui"].values():
                missing.append(str(halfcycle_id))

        build = False
        if missing == []:
            st.session_state["clean_cycles"] = st.checkbox(
                "Clean non-physical cycles (only efficiencies <100% and complete charge/discharge cycles)",
                value=st.session_state["clean_cycles"],
            )
            build = st.button("Build cycle")

        else:
            missing_list = ", ".join(missing)
            st.warning(
                f"WARNING: The halfcycles IDs must be subsequent. The following IDs are missing: {missing_list}"
            )

        if build:

            custom_order = []
            for level in range(max_level):
                custom_order.append([])
                for key, selected_level in st.session_state[
                    "user_ordering_gui"
                ].items():
                    if selected_level == level:
                        old_id = key.split(":")
                        custom_order[level].append(
                            suggested_ordering[int(old_id[0])][int(old_id[1])]
                        )

            st.session_state["custom_ordering"] = custom_order
            st.session_state["orderer_expander"] = False
            st.experimental_rerun()

if st.session_state["custom_ordering"] != []:

    manager = st.session_state["file_manager"]
    st.session_state["cycles"] = manager.get_cycles(
        st.session_state["custom_ordering"], clean=st.session_state["clean_cycles"]
    )

    st.session_state["hidden_cycles"] = 0
    for cycle in st.session_state["cycles"]:
        if cycle._hidden == True:
            st.session_state["hidden_cycles"] += 1

    st.session_state["cellcycles"] = manager.build_cycles(
        st.session_state["custom_ordering"], clean=st.session_state["clean_cycles"]
    )

    with st.container():
        st.markdown("**General data:**")
        st.markdown("Instrument: ***{}***".format(manager.instrument))

        c1, c2, c3, c4, c5 = st.columns(5)

        with c1:
            st.metric("Uploaded files", value=st.session_state["num_uploaded_files"])

        with c2:
            st.metric("Parsed files", value=len(manager.bytestreams))

        with c3:
            st.metric(
                "Skipped files",
                value=len(manager.bytestreams) - len(manager.halfcycles),
            )

        with c4:
            st.metric(
                "Halfcycles joined",
                value=len(manager.halfcycles)
                - len(st.session_state["custom_ordering"]),
            )

        with c5:
            st.metric("Hidden cycles", value=st.session_state["hidden_cycles"])

        table = []
        for level, level_list in enumerate(st.session_state["custom_ordering"]):
            for number, filename in enumerate(level_list):
                table.append(
                    [
                        level,
                        number,
                        manager.halfcycles[filename].halfcycle_type,
                        manager.halfcycles[filename].timestamp.strftime(
                            "%d/%m/%Y    %H:%M:%S"
                        ),
                        filename,
                    ]
                )

        df = pd.DataFrame(
            table,
            columns=["Halfcycle", "Partial halfcycle", "Type", "Timestamp", "Filename"],
        )

        with st.expander("Halfcycles file ordering report:", expanded=True):
            st.markdown("**Ordering report:**")
            st.table(df)

        table = []
        for cycle in st.session_state["cycles"]:
            charge_timestamp = (
                cycle._charge._timestamp.strftime("%d/%m/%Y    %H:%M:%S")
                if cycle._charge != None
                else "None"
            )
            discharge_timestamp = (
                cycle._discharge._timestamp.strftime("%d/%m/%Y    %H:%M:%S")
                if cycle._discharge != None
                else "None"
            )
            table.append([charge_timestamp, discharge_timestamp, cycle._hidden])

        df = pd.DataFrame(
            table, columns=["Charge timestamp", "Discharge timestamp", "Hidden"]
        )

        with st.expander("Cycles report after parsing:", expanded=True):
            st.markdown("**Cycles report:**")
            st.table(df)

        st.success(
            "SUCCESS: The dataset has been loaded and is now available for analysis"
        )

clear_all = st.button("CLEAR ALL DATA")
if clear_all:
    set_default()
    st.experimental_rerun()
