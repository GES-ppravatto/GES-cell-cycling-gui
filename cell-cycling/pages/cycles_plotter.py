import streamlit as st
import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from core.gui_core import Experiment, ProgramStatus, ExperimentSelector, RGB_to_HEX
from echemsuite.cellcycling.cycles import HalfCycle

# %% Definition of labels and functions specific to the cycles plotting
HALFCYCLE_SERIES = [
    "time (s)",
    "voltage (V)",
    "current (A)",
    "charge (mAh)",
    "energy (mWh)",
]


def get_halfcycle_series(halfcycle: HalfCycle, title: str) -> pd.Series:
    """
    Given the halfcycle of interest and the title of the data series, retuns the pandas
    Serier containing the data to plot

    Arguments
    ---------
        halfcycle : HalfCycle
            the halfcycle from which the data must be taken
        title : str
            the title of the series to be taken from the halfcycle. Note that the title
            must match one of the entries of the HALFCYCLE_SERIES list variable.
    """
    if title == "time (s)":
        return halfcycle.time
    elif title == "voltage (V)":
        return halfcycle.voltage
    elif title == "current (A)":
        return halfcycle.current
    elif title == "charge (mAh)":
        return halfcycle.Q
    elif title == "energy (mWh)":
        return halfcycle.energy
    else:
        raise ValueError


# Check if the main page has set up the proper session state variables and check that at
# least one experiment has been loaded
enable = True
if "ProgramStatus" not in st.session_state:
    enable = False
else:
    status: ProgramStatus = st.session_state["ProgramStatus"]
    if len(status) == 0:
        enable = False

# Create an instance of the ExperimentSelector class to be used to define the data to plot
# and chache it in the session state
if "CyclePlotSelection" not in st.session_state:
    st.session_state["CyclePlotSelection"] = ExperimentSelector()


# Set the title of the page and print some generic instruction
st.title("Cycles plotter")

st.write(
    """In this page you can select the experiments to analyze and plot a selected subset of
    charge/discharge cycles"""
)

# If there is one or more experiment loaded in the buffer start the plotter GUI
if enable:

    # Fetch a fresh instance of the progam status from the session state
    status: ProgramStatus = st.session_state["ProgramStatus"]

    # Define a container to hold the experiment selection box
    with st.container():

        # Fetch a fresh instance of the Experiment Selection variable from the session state
        selected_experiments: ExperimentSelector = st.session_state["CyclePlotSelection"]

        selection = None  # Experiment selected
        col1, col2 = st.columns([4, 1])

        # Create a selectbox from which the user can decide which experiment to analyze
        with col1:

            # Take the available experiments as the names of the experiments loaded in the
            # program status object removing the ones already selected
            available_experiments = [
                obj.name for obj in status if obj.name not in selected_experiments.names
            ]
            selection = st.selectbox("Select the desired experiment", available_experiments)

        # Show and add button to allow the user to add the selected experiment to the list
        with col2:
            st.write("")  # Added for vertical spacing
            st.write("")  # Added for vertical spacing
            add = st.button("➕ Add")
            if add and selection is not None:
                selected_experiments.set(selection)  # Set the experiment in the selector
                st.experimental_rerun()  # Rerun the page to update the selector box

    st.markdown("---")

    # If the Experiment selector is not empty show to the user the cycle selector interface
    if st.session_state["CyclePlotSelection"].is_empty == False:

        # Fetch a fresh instance of the Experiment Selection variable from the session state
        selected_experiments: ExperimentSelector = st.session_state["CyclePlotSelection"]

        # Create an expander holding the Cycle selection options
        with st.expander("Visualization options", expanded=True):

            col1, col2 = st.columns(2)

            # Create a column in which the user can select the experiment to manipulate
            with col1:
                # Show a radio button to allow the selection of the wanted experiment
                st.markdown("###### Loaded experiments selector")
                current_view = st.radio(
                    "Select the experiment to edit",
                    selected_experiments.names,
                )

                st.markdown("---")

                # Show a button to remove the selected experiment from the view
                st.markdown("###### View options")
                remove_current = st.button("➖ Remove from view")
                if remove_current:
                    index = selected_experiments.remove(current_view)
                    st.experimental_rerun()  # Rerun the page to update the GUI

            # Create a column based on the selections made in the first one in which the
            # user can select the desired cycles
            with col2:

                # Show a selector allowing the user to choose how to set the cycles view
                st.markdown("###### Cycle selector mode")
                view_mode = st.radio(
                    "Select the mode of operation", ["Constant interval", "Manual"]
                )

                st.markdown("---")

                # Show the appropriate selection box
                if view_mode == "Constant interval":

                    st.markdown("###### Constant interval cycle selector")

                    id = status.get_index_of(current_view)
                    max_cycle = len(status[id].manager.get_cycles()) - 1

                    # Show a number input to allow the selection of the start point
                    start = st.number_input(
                        "Start", min_value=0, max_value=max_cycle - 1, step=1
                    )

                    # Show a number input to allow the selection of the stop point, please
                    # notice how the stop point is excluded from the interval and, as such,
                    # must be allowed to assume a maximum value equal to the last index +1
                    stop = st.number_input(
                        "Stop (included)",
                        min_value=start + 1,
                        max_value=max_cycle,
                        value=max_cycle,
                        step=1,
                    )

                    # Show a number input to allow the selection of the stride
                    stride = st.number_input(
                        "Stride", min_value=1, max_value=max_cycle, step=1
                    )

                    apply = st.button("✅ Apply")
                    if apply:
                        selected_experiments.set(
                            current_view, np.arange(start, stop + 1, step=stride)
                        )

                else:
                    st.markdown("###### Manual cycle selector")

                    # Get the complete cycle list associated to the selected experiment
                    id = status.get_index_of(current_view)
                    cycles = status[id].manager.get_cycles()

                    # Show a multiple selection box with all the available cycles in which
                    # the user can manually add or remove a cycle
                    selected_experiments[current_view] = st.multiselect(
                        "Select the cycles",
                        [obj.number for obj in cycles],
                        default=selected_experiments[current_view],
                    )

                    # Print a remave all button to allow the user to remove alle the selected cycles
                    clear_current_view = st.button("Remove All")
                    if clear_current_view:
                        selected_experiments[current_view] = []
                        st.experimental_rerun()  # Rerun to update the GUI

    # Fetch a fresh instance of the Experiment Selection variable from the session state
    selected_experiments: ExperimentSelector = st.session_state["CyclePlotSelection"]

    # If there are selected experiment in the buffer start the plot operations
    if not selected_experiments.is_empty:

        # Print a header section in which the user can select the plotting options
        st.markdown("### Experiment plots")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("###### x axis options")
            x_axis = st.selectbox("Select the series x axis", HALFCYCLE_SERIES)

        with col2:
            st.markdown("###### y axis options")
            y_axis = st.selectbox(
                "Select the series y axis",
                [element for element in HALFCYCLE_SERIES if element != x_axis],
            )

        with col3:
            st.markdown("###### other options")
            show_charge = st.checkbox("Show charge", value=True)
            show_discharge = st.checkbox("Show discharge", value=True)
            reverse = st.checkbox("Reversed colorscale", value=True)
            plot_height = st.number_input(
                "Plot height", min_value=10, max_value=1000, value=400, step=10
            )

        st.markdown("---")

        # Create a figure with a number of subplots equal to the numebr of selected experiments
        fig = make_subplots(cols=1, rows=len(selected_experiments))

        # For eache experiment update the correspondent subplot
        for index, name in enumerate(selected_experiments.names):

            # Get the cycle list from the experiment
            id = status.get_index_of(name)
            experiment: Experiment = status[id]
            cycles = experiment.manager.get_cycles()

            # Get the user selected cycles and plot only the corresponden lines
            num_traces = len(selected_experiments[name])
            for trace_id, cycle_id in enumerate(selected_experiments[name]):

                # Get the shade associated to the current trace
                shade = RGB_to_HEX(
                    *experiment.color.get_shade(trace_id, num_traces, reversed=reverse)
                )

                # extract the cycle given the id selected
                cycle = cycles[cycle_id]

                # Print the charge halfcycle
                if cycle.charge is not None and show_charge is True:

                    x_series = get_halfcycle_series(cycle.charge, x_axis)
                    y_series = get_halfcycle_series(cycle.charge, y_axis)

                    fig.add_trace(
                        go.Scatter(
                            x=x_series,
                            y=y_series,
                            line=dict(color=shade, dash="dot"),
                            name=f"charge cycle {cycle_id}",
                        ),
                        row=index + 1,
                        col=1,
                    )

                # Print the discharge halfcycle
                if cycle.discharge is not None and show_discharge is True:

                    x_series = get_halfcycle_series(cycle.discharge, x_axis)
                    y_series = get_halfcycle_series(cycle.discharge, y_axis)

                    fig.add_trace(
                        go.Scatter(
                            x=x_series,
                            y=y_series,
                            line=dict(color=shade),
                            name=f"discharge cycle {cycle_id}",
                        ),
                        row=index + 1,
                        col=1,
                    )

        # Update the settings of the x-axis
        fig.update_xaxes(
            title_text=x_axis,
            showline=True,
            linecolor="black",
            gridwidth=1,
            gridcolor="#DDDDDD",
        )

        # Update the settings of the y-axis
        fig.update_yaxes(
            title_text=y_axis,
            showline=True,
            linecolor="black",
            gridwidth=1,
            gridcolor="#DDDDDD",
        )

        # Update the settings of plot layout
        fig.update_layout(
            plot_bgcolor="#FFFFFF", height=plot_height * len(selected_experiments.names)
        )

        # Insert the plot in streamlit
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

# If there are no experiments in the buffer suggest to the user to load data form the main page
else:
    st.info(
        """**No experiment has been loaded yet** \n\n Please go to the file manager 
    page and procede to upload and properly edit the required experiment files before
    accessing this page."""
    )
