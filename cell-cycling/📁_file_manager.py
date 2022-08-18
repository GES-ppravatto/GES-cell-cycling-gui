import streamlit as st
import pandas as pd
from io import BytesIO

from core.session_state_manager import save_session_state, load_session_state
from core.gui_core import ProgramStatus
from core.colors import ColorRGB, RGB_to_HEX, HEX_to_RGB
from core.experiment import Experiment, _EXPERIMENT_INIT_COUNTER_
from core.utils import set_production_page_style

if "ProgramStatus" not in st.session_state:
    st.session_state["ProgramStatus"] = ProgramStatus()
    st.session_state["UploadActionRadio"] = None
    st.session_state["UploadConfirmation"] = [None, None]
    st.session_state["SelectedExperimentName"] = None

st.set_page_config(layout="wide")
set_production_page_style()

st.title("Experiment file manager")

upload_tab, manipulation_tab, inspector_tab, save_tab = st.tabs(
    ["Upload", "Edit", "Inspect", "💾 save/load"]
)

with upload_tab:

    # Load a fresh ProgramStatus class from the session_state chache
    status: ProgramStatus = st.session_state["ProgramStatus"]

    # Print a title and some info about the usage of the current tab
    st.markdown("### Experiment uploader:")
    st.write(
        """In this tab you can define new experiments by loading the experimental data-files.
    Plese notice that to complete the operation you must press the `Submit` button. Changing page
    or tab without doing so will result in the lost of the loaded data."""
    )

    # Define a two column section to select if the new data will create a new experiment or
    # if they must be added to an existing one.

    action = st.radio(
        "Select action:",
        ["Create new experiment", "Add to existing experiment"],
        disabled=(
            status.number_of_experiments == 0
        ),  # Disable the selector if no other experiments are loaded
    )

    # Define an upload form where multiple files can be loaded indipendently
    with st.form("File upload form", clear_on_submit=True):

        # If "Create new experiment" is selected ask the user to input the experiment name
        if action == "Create new experiment":
            name = st.text_input(
                f"Select a name for the experiment (default: experiment_{_EXPERIMENT_INIT_COUNTER_})",
                "",  # Default "" value will trigger the class default naming experiment_{N}
            )

        # If "Add new experiment" show a selection box to select one of the alreadi loaded experiments
        else:
            experiment_names = status.get_experiment_names()
            name = st.selectbox(
                "Select the experiment to wich the files must be added:", experiment_names
            )

        files = st.file_uploader(
            "Select the cell-cycling datafiles", accept_multiple_files=True
        )

        submitted = st.form_submit_button("Submit")

        # If the button has been pressed and the file list is not empty load the files in the experiment
        if submitted and files != []:

            with st.spinner(text="Wait while the files are uploaded"):

                # Define a new experiment object
                new_experiment = Experiment(files)

                # Set the name selected by the user if existing
                if name != "":
                    new_experiment.name = name
                else:
                    name = new_experiment.name

                # If the selected action is "Create new experiment" add the new experiment to the ProgramStatus
                if action == "Create new experiment":
                    status.append_experiment(new_experiment)

                # If the selected action is "Add new experiment", add the object to the already available one
                else:
                    status[status.get_index_of(name)] += new_experiment

                # Add the informations about the loaded experiment to a rerun-safe self-cleaning variable
                st.session_state["UploadConfirmation"][0] = new_experiment.name

                skipped_files = []
                if new_experiment.manager.instrument == "GAMRY":
                    if len(new_experiment.manager.bytestreams) != len(
                        new_experiment.manager.halfcycles
                    ):
                        for filename in new_experiment.manager.bytestreams.keys():
                            if filename not in new_experiment.manager.halfcycles.keys():
                                skipped_files.append(filename)
                        st.session_state["UploadConfirmation"][1] = skipped_files

                elif new_experiment.manager.instrument == "BIOLOGIC":
                    for filename in new_experiment.manager.bytestreams.keys():
                        find = False
                        for search in new_experiment.manager.halfcycles.keys():
                            if filename in search:
                                find = True
                                break

                        if find is False:
                            skipped_files.append(filename)
                    if skipped_files != []:
                        st.session_state["UploadConfirmation"][1] = skipped_files

                else:
                    raise RuntimeError

                if skipped_files != []:
                    status[status.get_index_of(name)]._skipped_files += len(skipped_files)

                # Rerun the page to force update
                st.experimental_rerun()

    created_experiment = st.session_state["UploadConfirmation"][0]
    skipped_files = st.session_state["UploadConfirmation"][1]
    if created_experiment is not None:
        if skipped_files is not None:
            st.warning(
                "The following empty files have been skipped:\n [{}]".format(
                    ", ".join(skipped_files)
                )
            )
        st.success(
            f"The experiment '{created_experiment}' has succesfully been created/updated"
        )
        st.session_state["UploadConfirmation"] = [None, None]


with manipulation_tab:

    # Load a fresh ProgramStatus class from the session_state chache
    status: ProgramStatus = st.session_state["ProgramStatus"]

    # Print a title and some info about the usage of the current tab
    st.markdown("### Experiment editor:")
    st.write(
        """In this tab you can edit or delete the experiments loaded. In absence of errors or warning requiring user
        attention, edits done to the experiments are automatically saved. The edits are immediately applied to all the
        app components."""
    )

    # Display a selectbox listing all the experiments available
    experiment_names = status.get_experiment_names()
    default_index = 0
    if st.session_state["SelectedExperimentName"] is not None:
        default_index = status.get_index_of(st.session_state["SelectedExperimentName"])

    name = st.selectbox(
        "Select the experiment to edit", experiment_names, index=default_index
    )

    # If the selection is valid open the manipulation tab
    if name != None:

        st.session_state["SelectedExperimentName"] = name

        # Load the selected experiment in a fresh variable
        experiment: Experiment = status[status.get_index_of(name)]

        st.markdown("""---""")

        col1, col2 = st.columns(2)

        with col1:
            # Define the first section with the main experiment attributes
            st.markdown("### Experiment attributes:")
            st.markdown(f"Experiment name: `{name}`")
            st.markdown(f"Internal ID: `{status.get_index_of(name)}`")

        with col2:
            # Define a danger zone with red text to delete an experiment from memory
            st.markdown(
                """### <span style="color:red"> Danger zone:</span>""",
                unsafe_allow_html=True,
            )
            st.markdown(
                """<span style="color:red">WARNING:</span> by pressing the following button you will irreversibly delete the entire experiment from the application memory""",
                unsafe_allow_html=True,
            )

            delete = st.button("❌ Delete Expreiment")

            if delete:
                status.remove_experiment(status.get_index_of(experiment.name))
                if st.session_state["SelectedExperimentName"] == experiment.name:
                    st.session_state["SelectedExperimentName"] = None
                st.experimental_rerun()

        st.markdown("""---""")

        col1, col2 = st.columns(2)

        with col1:

            # Allow the user to re-define the experiment name
            st.markdown("##### Experiment name:")
            new_experiment_name = st.text_input("Experiment name", name)
            if new_experiment_name != name:
                experiment.name = new_experiment_name
                st.session_state["SelectedExperimentName"] = new_experiment_name
                st.experimental_rerun()

            # Allow the user to define the experiment volume
            st.markdown("##### Electrolite volume:")
            volume_str = st.text_input(
                "Volume of the electrolyte (L)",
                value="" if experiment.volume is None else str(experiment.volume),
                help="""If set for all the experiments, it unlocks the options 
                of examining the data in terms of the volumetric capacity""",
            )

            if volume_str != "":
                try:
                    volume = float(volume_str)
                except Exception:
                    st.error(
                        f"ERROR: the input '{volume_str}' does not represent a valid floating point value"
                    )
                else:
                    if volume != experiment.volume:
                        experiment.volume = volume
                        st.experimental_rerun()

            # Allow the user to define the experiment electrode area
            st.markdown("##### Electrode area:")
            area_str = st.text_input(
                "Area of the electrode (cm^2)",
                value="" if experiment.area is None else str(experiment.area),
                help="""If set for all the experiments, it unlocks the options 
                of examining the data in terms of the current density""",
            )

            if area_str != "":
                try:
                    area = float(area_str)
                except Exception:
                    st.error(
                        f"ERROR: the input '{area_str}' does not represent a valid floating point value"
                    )
                else:
                    if area != experiment.area:
                        experiment.area = area
                        st.experimental_rerun()

        with col2:

            # Allow the user to select if the self-cleaning option must be used
            st.markdown("##### Clean non-physical cycles")
            clean_status = st.checkbox(
                " Allow only efficiencies <100% and complete charge/discharge cycles",
                value=experiment.clean,
            )
            if clean_status != experiment.clean:
                experiment.clean = clean_status
                st.experimental_rerun()

            # Allow the user to select a base color for the experiment to be used in the stacked-plot
            st.markdown("##### Base color:")
            current_color = RGB_to_HEX(*experiment.color.get_RGB())
            color = st.color_picker(
                "Select the color to be used as basecolor",
                value=current_color,
            )
            if color != current_color:
                experiment.color = ColorRGB(*HEX_to_RGB(color))
                st.experimental_rerun()

        st.markdown("""   """)

        # Create an expander to hold the data related to the uploaded files
        with st.expander("Loaded files:", expanded=True):

            remove = False
            _, _, cright = st.columns(3)
            with cright:
                remove = st.button("🗑️ Remove selected", key="upper")

            # Print a header for the table
            cid, cname, cselection = st.columns(3)
            with cid:
                st.markdown("#### ID")
            with cname:
                st.markdown("#### Filename")
            with cselection:
                st.markdown("#### Selection")

            # Define an empty list to contain the file selected in the selection column
            selection_list = []

            # Cycle over all the bytestream entry and print the wanted data
            for idx, filename in enumerate(experiment._manager.bytestreams.keys()):

                with st.container():
                    cid, cname, cselection = st.columns(3)
                    with cid:
                        st.write(idx)
                    with cname:
                        st.write(filename)
                    with cselection:
                        checked = st.checkbox("", key=filename)

                    # Update the selection list based on the check_box status
                    if checked:
                        selection_list.append(filename)
                    else:
                        if filename in selection_list:
                            del selection_list[filename]

            # Print a button on the right to remove the selected files
            _, _, cright = st.columns(3)
            with cright:
                remove |= st.button("🗑️ Remove selected", key="lower")

            # If the remove button in pressed remove the file from the experiment and rerun the page
            if remove:
                for filename in selection_list:
                    experiment.remove_file(filename)
                st.experimental_rerun()

        # If the .DTA files from GAMRY are loaded create a section dedicated to the process of merging/ordering of halfcycles
        if experiment.manager.instrument == "GAMRY":

            # Get FileManager suggested ordering
            current_ordering = experiment.ordering

            # Generate a table with number_input widgets to allow the user to select the proper file ordering
            with st.expander("Halfcycle ordering manipulation"):

                # Generate a header section
                with st.container():
                    cname, ctstamp, ctype, ctime, ccycle, chalfcycle = st.columns(6)
                    with cname:
                        st.markdown("#### Filename")
                    with ctstamp:
                        st.markdown("#### Timestamp")
                    with ctype:
                        st.markdown("#### Type")
                    with ctime:
                        st.markdown("#### Runtime (s)")
                    with ccycle:
                        st.markdown("#### Cycle")
                    with chalfcycle:
                        st.markdown("#### Halfcycle")

                # Generate the table body
                max_cycle = 0  # Maximum cycle index selected
                ordering_buffer = (
                    {}
                )  # Buffer dictionary to store the Cycle and HalfCycle IDs associated to a given filename

                # Iterate over all the entry of the suggested ordering list
                for cycle, cycle_list in enumerate(current_ordering):
                    for halfcycle, filename in enumerate(cycle_list):

                        ordering_buffer[filename] = (
                            cycle,
                            halfcycle,
                        )  # Fill the ordering buffer with the current_ordering

                        with st.container():
                            cname, ctstamp, ctype, ctime, ccycle, chalfcycle = st.columns(6)
                            with cname:
                                st.write(filename)
                            with ctstamp:
                                st.write(experiment.manager.halfcycles[filename].timestamp)
                            with ctype:
                                st.write(
                                    experiment.manager.halfcycles[filename].halfcycle_type
                                )
                            with ctime:
                                st.write(
                                    experiment.manager.halfcycles[filename].time.iloc[-1]
                                )
                            with ccycle:
                                # Save a temporary variable with the selected cycle
                                new_cycle = int(
                                    st.number_input(
                                        "Cycle ID:",
                                        min_value=0,
                                        value=cycle,
                                        step=1,
                                        key=f"Cycle_{filename}",
                                    )
                                )
                                max_cycle = max(
                                    max_cycle, new_cycle
                                )  # Update the max_cycle variable
                            with chalfcycle:
                                # Save a temporary variable with the selected halfcycle
                                new_halfcycle = int(
                                    st.number_input(
                                        "Halfcycle order:",
                                        min_value=0,
                                        value=halfcycle,
                                        step=1,
                                        key=f"Halfcycle_{filename}",
                                    )
                                )

                            # If something has been changed by the user override the dictionary entry
                            if cycle != new_cycle or halfcycle != new_halfcycle:
                                ordering_buffer[filename] = (new_cycle, new_halfcycle)

                # Process the ordering_buffer dictionary to a subset of halfcycle ordering dictionary
                repetition = False
                cycle_based_buffer = [{} for _ in range(max_cycle + 1)]
                for filename, entry in ordering_buffer.items():
                    cycle, halfcycle = entry[0], entry[1]
                    if halfcycle in cycle_based_buffer[cycle].keys():
                        repetition = True
                    cycle_based_buffer[cycle][halfcycle] = filename

                # Check if there are empty dictionary in the cycle_based_buffer to identify holes in the cycle sequence
                missing = []
                for index, dictionary in enumerate(cycle_based_buffer):
                    if dictionary == {}:
                        missing.append(str(index))

                # If there are missing levels print a warning to the user
                if missing != []:
                    missing_list = ", ".join(missing)
                    st.warning(
                        f"WARNING: The Cycles IDs must be subsequent. The following IDs are missing: {missing_list}"
                    )
                elif repetition:
                    st.warning(
                        f"WARNING: The halfcycles ordering must not contain repetitions."
                    )

                # Define the new ordering appending the halfcycles in order of index
                else:
                    new_ordering = [[] for _ in range(max_cycle + 1)]
                    for cycle, buffer in enumerate(cycle_based_buffer):
                        for i in range(max(buffer.keys()) + 1):
                            if i in buffer.keys():
                                new_ordering[cycle].append(buffer[i])

                    if new_ordering != experiment.ordering:
                        experiment.ordering = new_ordering
                        st.experimental_rerun()


with inspector_tab:

    # Load a fresh ProgramStatus class from the session_state chache
    status: ProgramStatus = st.session_state["ProgramStatus"]

    # Print a title and some info about the usage of the current tab
    st.markdown("### Experiment inspector:")
    st.write("""In this tab you can inspect the experiments created,  """)

    # Display a selectbox listing all the experiments available
    experiment_names = status.get_experiment_names()
    default_index = 0
    if st.session_state["SelectedExperimentName"] is not None:
        default_index = status.get_index_of(st.session_state["SelectedExperimentName"])

    name = st.selectbox(
        "Select the experiment to inspect", experiment_names, index=default_index
    )

    if name != None:

        # Load the selected experiment in a fresh variable
        experiment: Experiment = status[status.get_index_of(name)]

        st.markdown("### General data:")
        st.markdown("Instrument: ***{}***".format(experiment.manager.instrument))

        # Get the cycle list from the current experiment and compute the number of hidden cycles
        cycles = experiment.cycles
        n_hidden = 0
        for cycle in cycles:
            if cycle._hidden:
                n_hidden += 1

        # Print report on the number of loaded/parsed/skipped files, and on the joined/hidden cycles
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Uploaded files", value=len(experiment.manager.bytestreams))

        with c2:
            st.metric("Parsed halfcycles", value=len(experiment.manager.halfcycles))

        with c3:
            st.metric("Skipped files", value=experiment._skipped_files)

        with c4:
            st.metric(
                "Halfcycles joined",
                value=len(experiment.manager.halfcycles) - len(experiment.ordering),
            )

        with c5:
            st.metric("Hidden cycles", value=n_hidden)

        # Generate a report on the loaded vs parsed/skipped files
        with st.expander("Loaded file report:", expanded=True):

            col1, col2, col3 = st.columns(3)

            with st.container():
                with col1:
                    st.write("ID")
                with col2:
                    st.write("Filename")
                with col3:
                    st.write("Status:")

            for idx, filename in enumerate(experiment.manager.bytestreams.keys()):

                with st.container():
                    with col1:
                        st.write(idx)
                    with col2:
                        st.write(filename)
                    with col3:

                        if (
                            experiment.manager.instrument == "GAMRY"
                            and filename in experiment.manager.halfcycles.keys()
                        ):
                            st.write("🟢 PARSED")

                        elif experiment.manager.instrument == "BIOLOGIC" and any(
                            [
                                filename in key
                                for key in experiment.manager.halfcycles.keys()
                            ]
                        ):
                            st.write("🟢 PARSED")

                        else:
                            st.write("🔴 SKIPPED")

        # Generate a non editable table with the final composition of each halfcycle
        table = []
        for level, level_list in enumerate(experiment.ordering):
            for number, filename in enumerate(level_list):
                table.append(
                    [
                        level,
                        number,
                        experiment.manager.halfcycles[filename].halfcycle_type,
                        experiment.manager.halfcycles[filename].timestamp.strftime(
                            "%d/%m/%Y    %H:%M:%S"
                        ),
                        filename,
                    ]
                )

        df = pd.DataFrame(
            table,
            columns=["Halfcycle", "Partial halfcycle", "Type", "Timestamp", "Filename"],
        )

        # Print the halfcycle table in a dedicated expander
        with st.expander("Halfcycles file ordering report:", expanded=True):
            st.markdown("**Ordering report:**")
            st.table(df)

        # Generate a non-editable table reporting the composition of each cycle
        table = []
        for cycle in cycles:
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

        # Print the cycle table in a dedicated expander
        with st.expander("Cycles report after parsing:", expanded=True):
            st.markdown("**Cycles report:**")
            st.table(df)

with save_tab:

    st.markdown("### Session save/load:")
    st.write("In this tab you can save and load the state of the whole analysis.")

    csave, cload = st.columns(2)

    with csave:
        st.markdown("##### Save session")

        picklename = st.text_input(
            "Enter the name of the file to save", value="my_analysis"
        )

        st.download_button(
            label="💾 Save status",
            data=save_session_state(),
            file_name=f"{picklename}.pickle",
        )

    with cload:

        st.markdown("##### Load session")

        with st.form("Load", clear_on_submit=True):

            source = st.file_uploader(
                "Select the file", accept_multiple_files=False, type="pickle"
            )

            submitted = st.form_submit_button("Submit")

        # If the button has been pressed and the file list is not empty load the files in the experiment
        if submitted and source:
            load_session_state(BytesIO(source.getvalue()))
            st.experimental_rerun()
