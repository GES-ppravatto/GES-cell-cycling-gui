import streamlit as st

from core.gui_core import (
    ColorRGB,
    Experiment,
    ProgramStatus,
    _EXPERIMENT_INIT_COUNTER_,
    RGB_to_HEX,
    HEX_to_RGB,
)


if "ProgramStatus" not in st.session_state:
    st.session_state["ProgramStatus"] = ProgramStatus()
    st.session_state["UploadActionRadio"] = None
    st.session_state["UploadConfirmation"] = [None, None]
    st.session_state["SelectedExperimentName"] = None

st.set_page_config(layout="wide")

st.title("Experiment file manager")

upload_tab, manipulation_tab, inspector_tab = st.tabs(["Upload", "Edit", "Inspect"])


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

    col1, col2 = st.columns(2)

    with col1:
        action = st.radio(
            "Select action:",
            ["Create new experiment", "Add to existing experiment"],
            disabled=(
                status.number_of_experiments == 0
            ),  # Disable the selector if no other experiments are loaded
        )

    with col2:

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

    # Define an upload form where multiple files can be loaded indipendently
    with st.form("File upload form", clear_on_submit=True):

        files = st.file_uploader(
            "Select the cell-cycling datafiles", accept_multiple_files=True
        )

        submitted = st.form_submit_button("Submit")

        # If the button has been pressed and the file list is not empty load the files in the experiment
        if submitted and files != []:

            # Define a new experiment object
            new_experiment = Experiment(files)

            # Set the name selected by the user if existing
            if name != "":
                new_experiment.name = name

            # If the selected action is "Create new experiment" add the new experiment to the ProgramStatus
            if action == "Create new experiment":
                status.append_experiment(new_experiment)

            # If the selected action is "Add new experiment", add the object to the already available one
            else:
                status[status.get_index_of(name)] += new_experiment

            # Add the informations about the loaded experiment to a rerun-safe self-cleaning variable
            st.session_state["UploadConfirmation"][0] = new_experiment.name
            if len(new_experiment.manager.bytestreams) != len(new_experiment.manager.halfcycles):
                skipped_files = []
                for filename in new_experiment.manager.bytestreams.keys():
                    if filename not in new_experiment.manager.halfcycles.keys():
                        skipped_files.append(filename)
                st.session_state["UploadConfirmation"][1] = skipped_files

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
    st.markdown("### Experiment manipulator:")
    st.write(
        """In this tab you can manipulate the experiments loaded. Plese notice that to complete
    the operation you must press the `Apply` button. Changing page or tab without doing so will result
    in the lost of the loaded data."""
    )

    # Display a selectbox listing all the experiments available
    experiment_names = status.get_experiment_names()
    default_index = 0
    if st.session_state["SelectedExperimentName"] is not None:
        default_index = status.get_index_of(st.session_state["SelectedExperimentName"])

    name = st.selectbox(
        "Select the experiment to manipulate", experiment_names, index=default_index
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
            st.markdown("##### Experiment name:")
            new_experiment_name = st.text_input("Experiment name", name)
            if new_experiment_name != name:
                experiment.name = new_experiment_name
                st.session_state["SelectedExperimentName"] = new_experiment_name
                st.experimental_rerun()

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

        with col2:
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
                remove = st.button("🗑️ Remove selected", key="lower")

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
                        missing.append(index)

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
    pass
