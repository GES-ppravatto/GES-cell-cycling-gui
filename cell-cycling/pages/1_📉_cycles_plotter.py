from typing import List, Tuple, Union
import math
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.gui_core import (
    Experiment,
    ProgramStatus,
    ExperimentSelector,
    SingleCycleSeries,
    RGB_to_HEX,
    get_plotly_color,
    set_production_page_style,
)
from echemsuite.cellcycling.cycles import HalfCycle


# %% Definition of labels and functions specific to the cycles plotting

HALFCYCLE_SERIES = [
    "time",
    "voltage",
    "current",
    "charge",
    "power",
    "energy",
]


def get_halfcycle_series(
    halfcycle: HalfCycle,
    title: str,
    volume: Union[None, float] = None,
    area: Union[None, float] = None,
) -> Tuple[str, pd.Series]:
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
        volume: Union[None, float]
            if not None will trigger the normalization of current, charge and energy per unit area
        area: Union[None, float]
            if not None will trigger the normalization of current, charge and energy per unit area
    """
    if title == "time":
        return "time (s)", halfcycle.time

    elif title == "voltage":
        return "voltage (V)", halfcycle.voltage

    elif title == "current":
        current = halfcycle.current
        if volume is None and area is None:
            return "current (A)", current
        elif volume is not None and area is None:
            return "normalized current (A/L)", current / volume
        elif area is not None and volume is None:
            return "normalized current (A/cm<sup>2</sup>)", current / area
        elif area is not None and volume is not None:
            return "normalized current (A/L cm<sup>2</sup>)", current / (volume * area)
        else:
            raise RuntimeError

    elif title == "charge":
        charge = halfcycle.Q
        if volume is None and area is None:
            return "charge (mAh)", charge
        elif volume is not None and area is None:
            return "normalized charge (Ah/L)", charge / (1000 * volume)
        elif area is not None and volume is None:
            return "normalized charge (Ah/cm<sup>2</sup>)", charge / (1000 * area)
        elif area is not None and volume is not None:
            return "normalized charge (Ah/L cm<sup>2</sup>)", charge / (1000 * volume * area)
        else:
            raise RuntimeError

    elif title == "power":
        power = halfcycle.power
        if volume is None and area is None:
            return "power (W)", power
        elif volume is not None and area is None:
            return "normalized power (W/L)", power / volume
        elif area is not None and volume is None:
            return "normalized power (W/cm<sup>2</sup>)", power / area
        elif area is not None and volume is not None:
            return "normalized power (W/L cm<sup>2</sup>)", power / (volume * area)
        else:
            raise RuntimeError

    elif title == "energy":
        energy = halfcycle.energy
        if volume is None and area is None:
            return "energy (mWh)", energy
        elif volume is not None and area is None:
            return "normalized energy (Wh/L)", energy / (1000 * volume)
        elif area is not None and volume is None:
            return "normalized energy (Wh/cm<sup>2</sup>)", energy / (1000 * area)
        elif area is not None and volume is not None:
            return "normalized energy (Wh/L cm<sup>2</sup>)", energy / (1000 * volume * area)
        else:
            raise RuntimeError

    else:
        raise ValueError


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
    st.session_state["ComparisonPlot"] = []


def clean_manual_selection_buffer():
    st.session_state["ManualSelectorBuffer"] = []


# Fetch a fresh instance of the Progam Status and Experiment Selection variables from the session state
status: ProgramStatus = st.session_state["ProgramStatus"]
selected_experiments: ExperimentSelector = st.session_state["CyclePlotSelection"]
selected_series: List[SingleCycleSeries] = st.session_state["ComparisonPlot"]

st.set_page_config(layout="wide")
set_production_page_style()

# Set the title of the page and print some generic instruction
st.title("Cycles plotter")

st.write(
    """In this page you can analyze cycling experiments comparing the profile associated to
    each charge/discharge cycle. The stacked plot tab will allow you to visualize, in 
    individual sub-plots, cycles belonging to different experiments. The comparison plot tab
    will allow you to generate a single plot in which cycles belonging to different 
    experiments can be overlayed and compared"""
)

# If there is one or more experiment loaded in the buffer start the plotter GUI
if enable:

    stacked_plot, comparison_plot = st.tabs(["Stacked plot", "Comparison plot"])

    # Define the stacked plot tab to compare cycling of different experiments
    with stacked_plot:

        st.markdown("### Experiments plotter")

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
                selection = st.selectbox(
                    "Select the experiment to be added to the view",
                    available_experiments,
                )

            # Show and add button to allow the user to add the selected experiment to the list
            with col2:
                st.write("")  # Added for vertical spacing
                st.write("")  # Added for vertical spacing
                add = st.button("➕ Add", key="stacked")
                if add and selection is not None:
                    selected_experiments.set(
                        selection
                    )  # Set the experiment in the selector
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
                        max_cycle = len(status[id].cycles) - 1

                        # Show a number input to allow the selection of the start point
                        start = st.number_input(
                            "Start",
                            min_value=0,
                            max_value=max_cycle - 1,
                            step=1,
                        )
                        start = int(start)

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

                        apply = st.button("✅ Apply", key="comparison_apply")
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
                        cycles = status[id].cycles

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
                                current_view,
                                cycles=st.session_state["ManualSelectorBuffer"],
                            )
                            st.experimental_rerun()

                        # Print a remave all button to allow the user to remove alle the selected cycles
                        clear_current_view = st.button("🧹 Clear All")
                        if clear_current_view:
                            selected_experiments[current_view] = []
                            st.experimental_rerun()  # Rerun to update the GUI

                    else:
                        st.markdown("###### Data series editor")

                        # Reset all labels given to the series
                        reset = st.button("🧹 Reset all names")
                        if reset:
                            selected_experiments.reset_default_labels(current_view)

                        # Let the user select the series and its new name
                        selected_series_to_edit = st.selectbox(
                            "Select the cycle series to edit",
                            selected_experiments[current_view],
                        )

                        current_label = selected_experiments.get_label(
                            current_view, selected_series_to_edit
                        )
                        new_label = st.text_input(
                            "Select the new label for the series", value=current_label
                        )

                        apply = st.button("✅ Apply")
                        if apply and new_label != "":
                            selected_experiments.set_cycle_label(
                                current_view, selected_series_to_edit, new_label
                            )

        # If there are selected experiment in the buffer start the plot operations
        if not selected_experiments.is_empty:

            col1, col2 = st.columns([4, 1])

            # Visualize some plot options in a small coulomn on the right
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

                volume_is_available = True
                for name in selected_experiments.view.keys():
                    experiment_id = status.get_index_of(name)
                    experiment = status[experiment_id]
                    if experiment.volume is None:
                        volume_is_available = False
                        break

                scale_by_volume = st.checkbox(
                    "Scale values by volume", value=False, disabled=not volume_is_available
                )

                area_is_available = True
                for name in selected_experiments.view.keys():
                    experiment_id = status.get_index_of(name)
                    experiment = status[experiment_id]
                    if experiment.area is None:
                        area_is_available = False
                        break

                scale_by_area = st.checkbox(
                    "Scale values by area", value=False, disabled=not area_is_available
                )

                st.markdown("###### Series")
                show_charge = st.checkbox("Show charge", value=True)
                show_discharge = st.checkbox("Show discharge", value=True)

                st.markdown("###### Aspect")
                reverse = st.checkbox("Reversed colorscale", value=True)
                font_size = st.number_input("Label font size", min_value=4, value=14)
                plot_height = st.number_input(
                    "Subplot height", min_value=10, max_value=1000, value=500, step=10
                )

            with col1:

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
                    exp_id = status.get_index_of(name)
                    experiment: Experiment = status[exp_id]
                    cycles = experiment.cycles
                    volume = experiment.volume if scale_by_volume else None
                    area = experiment.area if scale_by_area else None

                    # Get the user selected cycles and plot only the corresponden lines
                    num_traces = len(selected_experiments[name])
                    for trace_id, cycle_id in enumerate(selected_experiments[name]):

                        # Get the shade associated to the current trace
                        shade = RGB_to_HEX(
                            *experiment.color.get_shade(
                                trace_id, num_traces, reversed=reverse
                            )
                        )

                        # extract the cycle given the id selected
                        cycle = cycles[cycle_id]

                        # Print the charge halfcycle
                        if cycle.charge is not None and show_charge is True:

                            series_name = selected_experiments.get_label(name, cycle_id)

                            x_label, x_series = get_halfcycle_series(
                                cycle.charge, x_axis, volume, area
                            )
                            y_label, y_series = get_halfcycle_series(
                                cycle.charge, y_axis, volume, area
                            )

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

                            series_name = selected_experiments.get_label(name, cycle_id)

                            x_label, x_series = get_halfcycle_series(
                                cycle.discharge, x_axis, volume, area
                            )
                            y_label, y_series = get_halfcycle_series(
                                cycle.discharge, y_axis, volume, area
                            )

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
                    title_text=x_label,
                    showline=True,
                    linecolor="black",
                    gridwidth=1,
                    gridcolor="#DDDDDD",
                )

                # Update the settings of the y-axis
                fig.update_yaxes(
                    title_text=y_label,
                    showline=True,
                    linecolor="black",
                    gridwidth=1,
                    gridcolor="#DDDDDD",
                )

                # Update the settings of plot layout
                fig.update_layout(
                    plot_bgcolor="#FFFFFF",
                    height=plot_height * len(selected_experiments.names),
                    width=None,
                    font=dict(size=font_size),
                )

                st.plotly_chart(fig, use_container_width=True)

            with col2:

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

                # Set new layout options to account for the user selected width
                fig.update_layout(
                    plot_bgcolor="#FFFFFF",
                    height=plot_height * len(selected_experiments.names),
                    width=total_width,
                    font=dict(size=font_size),
                )

                st.download_button(
                    "Download plot",
                    data=fig.to_image(format=format),
                    file_name=f"cycle_plot.{format}",
                )

    # Define a comparison plot tab to compare cycle belonging to different experiments
    with comparison_plot:

        # Create a manager section allowing the user to select the trace to plot based on
        # the experiment name and the cycle number
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            experiment_name = st.selectbox(
                "Select the experiment",
                status.get_experiment_names(),
            )

        with col2:
            exp_idx = status.get_index_of(experiment_name)
            experiment = status[exp_idx]

            exclude = [
                entry.cycle_id
                for entry in selected_series
                if entry.experiment_name == experiment_name
            ]

            numbers = [obj.number for obj in experiment.cycles]

            cycle_number = st.selectbox(
                "Select the cycle",
                [n for n in numbers if n not in exclude],
            )

            cycle = experiment.cycles[numbers.index(cycle_number)]

        with col3:
            st.write("")
            st.write("")
            add = st.button("➕ Add", key="comparison")

            if add:
                selected_series.append(
                    SingleCycleSeries(
                        f"{experiment_name} [{cycle_number}]",
                        experiment_name,
                        cycle_number,
                        hex_color=get_plotly_color(len(selected_series)),
                    )
                )
                st.experimental_rerun()

        # Create a setup section to define the series to visualize and their color/name
        if selected_series != []:

            with st.expander("Series options:", expanded=True):

                cleft, cright = st.columns(2)

                with cleft:
                    st.markdown("##### Series selection")
                    available_labels = [entry.label for entry in selected_series]

                    series_label = st.selectbox("Select series to edit", available_labels)

                    series_position = available_labels.index(series_label)
                    current_series = selected_series[series_position]

                    remove = st.button("➖ Remove from selection")
                    if remove:
                        del selected_series[series_position]
                        st.experimental_rerun()

                    st.markdown("---")

                    st.markdown("###### Current selection")
                    st.markdown(f"Experiment: `{experiment_name}`")
                    st.markdown(f"Cycle: `{cycle_number}`")

                with cright:
                    st.markdown("##### Series options")
                    new_label = st.text_input("Select the series name", value=series_label)
                    new_color = st.color_picker(
                        "Select the series color", value=current_series.hex_color
                    )

                    apply = st.button("✅ Apply", key="Apply_coparison_plot")
                    if apply:
                        current_series.label = new_label
                        current_series.hex_color = new_color
                        st.experimental_rerun()

            col1, col2 = st.columns([4, 1])

            # Create a small column on the right to allow the user to set some properties of
            # the plot
            with col2:

                st.markdown("#### Plot options")

                st.markdown("###### Axis")
                x_axis = st.selectbox(
                    "Select the series x axis", HALFCYCLE_SERIES, key="x_comparison"
                )
                y_axis = st.selectbox(
                    "Select the series y axis",
                    [element for element in HALFCYCLE_SERIES if element != x_axis],
                    key="y_comparison",
                )

                volume_is_available = True
                for series in selected_series:
                    experiment_id = status.get_index_of(series.experiment_name)
                    experiment = status[experiment_id]
                    if experiment.volume is None:
                        volume_is_available = False
                        break

                scale_by_volume = st.checkbox(
                    "Scale values by volume",
                    value=False,
                    disabled=not volume_is_available,
                    key="comparison_plot",
                )

                st.markdown("###### Aspect")
                font_size = st.number_input(
                    "Label font size", min_value=4, value=14, key="font_size_comparison"
                )
                height = st.number_input(
                    "Plot height", min_value=10, max_value=1000, value=800, step=10
                )

            with col1:

                # Create a figure with a single plo
                fig = make_subplots(cols=1, rows=1)

                # For each selected series add an independent trace to the plot
                for entry in selected_series:

                    name = entry.experiment_name
                    cycle_id = entry.cycle_id

                    exp_idx = status.get_index_of(name)
                    cycle = status[exp_idx].cycles[cycle_id]

                    label = entry.label
                    color = entry.hex_color
                    volume = status[exp_idx].volume if scale_by_volume else None

                    # Print the charge halfcycle
                    if cycle.charge is not None:

                        x_label, x_series = get_halfcycle_series(
                            cycle.charge, x_axis, volume
                        )
                        y_label, y_series = get_halfcycle_series(
                            cycle.charge, y_axis, volume
                        )

                        fig.add_trace(
                            go.Scatter(
                                x=x_series,
                                y=y_series,
                                line=dict(color=color),
                                name=label,
                            ),
                            row=1,
                            col=1,
                        )

                    # Print the discharge halfcycle
                    if cycle.discharge is not None:

                        x_label, x_series = get_halfcycle_series(
                            cycle.discharge, x_axis, volume
                        )
                        y_label, y_series = get_halfcycle_series(
                            cycle.discharge, y_axis, volume
                        )

                        fig.add_trace(
                            go.Scatter(
                                x=x_series,
                                y=y_series,
                                line=dict(color=color),
                                name=label,
                                showlegend=False if cycle.charge else True,
                            ),
                            row=1,
                            col=1,
                        )

                # Update the settings of the x-axis
                fig.update_xaxes(
                    title_text=x_label,
                    showline=True,
                    linecolor="black",
                    gridwidth=1,
                    gridcolor="#DDDDDD",
                )

                # Update the settings of the y-axis
                fig.update_yaxes(
                    title_text=y_label,
                    showline=True,
                    linecolor="black",
                    gridwidth=1,
                    gridcolor="#DDDDDD",
                )

                # Update the settings of plot layout
                fig.update_layout(
                    plot_bgcolor="#FFFFFF",
                    height=height,
                    width=None,
                    font=dict(size=font_size),
                )

                st.plotly_chart(fig, use_container_width=True)

            with col2:

                # Add to the right column the export option
                st.markdown("###### Export")
                format = st.selectbox(
                    "Select the format of the file",
                    ["png", "jpeg", "svg", "pdf"],
                    key="format_comparison",
                )

                suggested_width = int(2.0 * height)
                width = st.number_input(
                    "Plot width",
                    min_value=10,
                    max_value=2000,
                    value=suggested_width if suggested_width <= 2000 else 2000,
                )

                # Update the settings of plot layout to account for the user define width
                fig.update_layout(
                    plot_bgcolor="#FFFFFF",
                    height=height,
                    width=width,
                    font=dict(size=font_size),
                )

                st.download_button(
                    "Download plot",
                    data=fig.to_image(format=format),
                    file_name=f"cycle_comparison_plot.{format}",
                )

# If there are no experiments in the buffer suggest to the user to load data form the main page
else:
    st.info(
        """**No experiment has been loaded yet** \n\n Please go to the file manager 
    page and procede to upload and properly edit the required experiment files before
    accessing this page."""
    )
