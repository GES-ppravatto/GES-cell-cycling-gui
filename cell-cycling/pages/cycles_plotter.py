import math
import streamlit as st
import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from core.gui_core import (
    Experiment,
    ProgramStatus,
    ExperimentSelector,
    CycleFormat,
    RGB_to_HEX,
)
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


# %% Define function to generate the cycle figure
def generate_plotly_figure(
    x_axis: str,
    y_axis: str,
    width: int = 800,
    plot_height: int = 400,
    shared_x: bool = False,
):

    status: ProgramStatus = st.session_state["ProgramStatus"]
    selected_experiments: ExperimentSelector = st.session_state["CyclePlotSelection"]

    # Create a figure with a number of subplots equal to the numebr of selected experiments
    fig = make_subplots(
        cols=1,
        rows=len(selected_experiments),
        shared_xaxes=shared_x,
        vertical_spacing=0.01 if shared_x else None,
    )

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

                series_name = selected_experiments.get_label(name, cycle_id)

                x_series = get_halfcycle_series(cycle.charge, x_axis)
                y_series = get_halfcycle_series(cycle.charge, y_axis)

                fig.add_trace(
                    go.Scatter(
                        x=x_series,
                        y=y_series,
                        line=dict(color=shade),
                        name=series_name,
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
                        name=series_name,
                        showlegend=False if cycle.charge else True,
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
        plot_bgcolor="#FFFFFF",
        height=plot_height * len(selected_experiments.names),
        width=width,
        font=dict(size=font_size),
    )

    return fig


# %% Definition of the page GUI

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
    st.session_state["ManualSelectorBuffer"] = []


def clean_manual_selection_buffer():
    st.session_state["ManualSelectorBuffer"] = []


# Fetch a fresh instance of the Progam Status and Experiment Selection variables from the session state
status: ProgramStatus = st.session_state["ProgramStatus"]
selected_experiments: ExperimentSelector = st.session_state["CyclePlotSelection"]


# Set the title of the page and print some generic instruction
st.title("Cycles plotter")

st.write(
    """In this page you can select the experiments to analyze and plot a selected subset of
    charge/discharge cycles"""
)

# If there is one or more experiment loaded in the buffer start the plotter GUI
if enable:

    # Define a container to hold the experiment selection box
    with st.container():

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
    if selected_experiments.is_empty == False:

        # Create an expander holding the Cycle selection options
        with st.expander("Cycle selector/editor", expanded=False):

            col1, col2 = st.columns(2, gap="medium")

            # Create a column in which the user can select the experiment to manipulate
            with col1:
                # Show a selectbox button to allow the selection of the wanted experiment
                st.markdown("###### Loaded experiments selector")
                current_view = st.selectbox(
                    "Select the experiment to edit",
                    selected_experiments.names,
                    on_change=clean_manual_selection_buffer,
                )

                # Show a button to remove the selected experiment from the view
                remove_current = st.button("➖ Remove from view")
                if remove_current:
                    index = selected_experiments.remove(current_view)
                    st.experimental_rerun()  # Rerun the page to update the GUI

                st.markdown("---")

                # Show a selector allowing the user to choose how to set the cycles view
                st.markdown("###### Mode of operation")
                view_mode = st.radio(
                    "Select the mode of operation",
                    [
                        "Constant-interval cycle selector",
                        "Manual cycle selector",
                        "Data series editor",
                    ],
                )

            # Create a column based on the selections made in the first one in which the
            # user can select the desired cycles
            with col2:

                # Show the appropriate selection box
                if view_mode == "Constant-interval cycle selector":

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

                    guess_stride = int(math.ceil(max_cycle / 10))
                    # Show a number input to allow the selection of the stride
                    stride = st.number_input(
                        "Stride",
                        min_value=1,
                        max_value=max_cycle,
                        step=1,
                        value=guess_stride,
                    )

                    apply = st.button("✅ Apply")
                    if apply:
                        selected_experiments.set(
                            current_view, np.arange(start, stop + 1, step=stride)
                        )

                elif view_mode == "Manual cycle selector":
                    st.markdown("###### Manual cycle selector")

                    # When empty, fill the temorary selection buffer with the selected
                    # experiment object content
                    if st.session_state["ManualSelectorBuffer"] == []:
                        st.session_state["ManualSelectorBuffer"] = selected_experiments[
                            current_view
                        ]

                    # Get the complete cycle list associated to the selected experiment
                    id = status.get_index_of(current_view)
                    cycles = status[id].manager.get_cycles()

                    # Show a multiple selection box with all the available cycles in which
                    # the user can manually add or remove a cycle, save the new list in a
                    # temporary buffer used on the proper rerun
                    st.session_state["ManualSelectorBuffer"] = st.multiselect(
                        "Select the cycles",
                        [obj.number for obj in cycles],
                        default=st.session_state["ManualSelectorBuffer"],
                    )

                    # If the temporary buffer is found to be different from the one currently
                    # set for the current view, update the current view
                    if (
                        st.session_state["ManualSelectorBuffer"]
                        != selected_experiments[current_view]
                    ):
                        selected_experiments.set(
                            current_view, cycles=st.session_state["ManualSelectorBuffer"]
                        )
                        st.experimental_rerun()

                    # Print a remave all button to allow the user to remove alle the selected cycles
                    clear_current_view = st.button("🧹 Clear All")
                    if clear_current_view:
                        selected_experiments[current_view] = []
                        st.experimental_rerun()  # Rerun to update the GUI

                else:
                    st.markdown("###### Data series editor")

                    reset = st.button("🧹 Reset all names")
                    if reset:
                        selected_experiments.reset_default_labels(current_view)

                    selected_series = st.selectbox(
                        "Select the cycle series to edit",
                        selected_experiments[current_view],
                    )

                    current_label = selected_experiments.get_label(
                        current_view, selected_series
                    )
                    new_label = st.text_input(
                        "Select the new label for the series", value=current_label
                    )

                    apply = st.button("✅ Apply")
                    if apply and new_label != "":
                        selected_experiments.set_cycle_label(
                            current_view, selected_series, new_label
                        )

    # If there are selected experiment in the buffer start the plot operations
    if not selected_experiments.is_empty:

        col1, col2 = st.columns([4, 1])

        with col2:

            st.markdown("#### Plot options")

            st.markdown("###### Axis")
            x_axis = st.selectbox("Select the series x axis", HALFCYCLE_SERIES)
            y_axis = st.selectbox(
                "Select the series y axis",
                [element for element in HALFCYCLE_SERIES if element != x_axis],
            )
            shared_x = st.checkbox(
                "Use shared x-axis",
                disabled=True if len(selected_experiments) == 1 else False,
            )

            st.markdown("###### Series")
            show_charge = st.checkbox("Show charge", value=True)
            show_discharge = st.checkbox("Show discharge", value=True)

            st.markdown("###### Aspect")
            reverse = st.checkbox("Reversed colorscale", value=True)
            font_size = st.number_input("Label font size", min_value=4, value=10)
            plot_height = st.number_input(
                "Subplot height", min_value=10, max_value=1000, value=500, step=10
            )

            st.markdown("###### Export")
            format = st.selectbox(
                "Select the format of the file", ["png", "jpeg", "svg", "pdf"]
            )

            suggested_width = int(2.5 * plot_height)
            total_width = st.number_input(
                "Total width",
                min_value=10,
                max_value=2000,
                value=suggested_width if suggested_width <= 2000 else 2000,
            )

            export_fig = generate_plotly_figure(
                x_axis,
                y_axis,
                width=total_width,
                plot_height=plot_height,
                shared_x=shared_x,
            )

            st.download_button(
                "Download plot",
                data=export_fig.to_image(format=format),
                file_name=f"cycle_plot.{format}",
            )

        with col1:
            # Insert the plot in streamlit
            fig = generate_plotly_figure(
                x_axis, y_axis, None, plot_height=plot_height, shared_x=shared_x
            )
            st.plotly_chart(fig, use_container_width=True)

# If there are no experiments in the buffer suggest to the user to load data form the main page
else:
    st.info(
        """**No experiment has been loaded yet** \n\n Please go to the file manager 
    page and procede to upload and properly edit the required experiment files before
    accessing this page."""
    )
