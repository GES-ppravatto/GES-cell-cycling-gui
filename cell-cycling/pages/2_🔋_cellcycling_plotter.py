import sys, os, logging, traceback, pickle
from typing import Dict, List, Tuple, Union
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_plotly_events import plotly_events

from core.gui_core import ProgramStatus, CellcyclingPlotSettings
from core.experiment import Experiment, ExperimentContainer
from core.utils import set_production_page_style, force_update_once
from core.colors import get_plotly_color


st.set_page_config(layout="wide")
set_production_page_style()


# Fetch logger from the session state
if "Logger" in st.session_state:
    logger: logging.Logger = st.session_state["Logger"]
else:
    raise RuntimeError


# Define a dictionary of available markers with their plotly name
MARKERS = {
    "●": "circle",
    "■": "square",
    "▲": "triangle-up",
    "▼": "triangle-down",
    "🞤": "cross",
    "🞭": "x",
}

# Define a list of possible alternatives for the y axis
Y_OPTIONS = [
    "Capacity retention",
    "Columbic efficiency",
    "Energy efficiency",
    "Voltaic Efficiency",
    "Total energy - Discharge",
    "Total capacity - Discharge",
    "Average power - Discharge",
]


# Define a function to exracte the wanted dataset from a cellcycling experiment give the label
def get_data_series(
    option: str,
    index: int,
    container: ExperimentContainer,
    scale_by_volume: bool = False,
    scale_by_area: bool = False,
) -> Tuple[str, List[float]]:

    if option not in Y_OPTIONS:
        raise TypeError

    experiment = container[index]
    cellcycling = experiment.cellcycling

    volume = experiment.volume if scale_by_volume else None
    area = experiment.area if scale_by_area else None

    if option == "Capacity retention":
        return "Capacity retention (%)", container.capacity_retention(index)

    elif option == "Columbic efficiency":
        return "Columbic efficiency (%)", cellcycling.coulomb_efficiencies

    elif option == "Energy efficiency":
        return "Energy efficiency (%)", cellcycling.energy_efficiencies

    elif option == "Voltaic Efficiency":
        return "Voltaic Efficiency (%)", cellcycling.voltage_efficiencies

    elif option == "Total energy - Discharge":
        total_energies = [cycle.discharge.total_energy for cycle in cellcycling]
        if volume is None:
            return "Energy (mWh)", total_energies
        else:
            normalized_energies = [energy / (1000 * volume) for energy in total_energies]
            return "Energy density (Wh/L)", normalized_energies

    elif option == "Total capacity - Discharge":
        total_capacities = [cycle.discharge.capacity for cycle in cellcycling]

        if volume is None:
            return "Capacity (mAh)", total_capacities
        else:
            normalized_energies = [
                capacity / (1000 * volume) for capacity in total_capacities
            ]
            return "Volumetric capacity (Ah/L)", normalized_energies

    elif option == "Average power - Discharge":
        average_powers = [cycle.discharge.power.mean() for cycle in cellcycling]

        if area is None:
            return "Power (W)", average_powers
        else:
            average_powers = [1000*power / area for power in average_powers]
            return (
                "Power density (mW/cm<sup>2</sup>)",
                average_powers,
            )

    else:
        raise RuntimeError


# Initialize the session state with the page specific variables
if "ExperimentContainers" not in st.session_state:
    st.session_state["ExperimentContainers"] = []
    st.session_state["Cellcycling_plots_settings"] = {}

# Fetch fresh reference to the variables in session state
available_containers: List[ExperimentContainer] = st.session_state["ExperimentContainers"]
plot_settings_dict: Dict[str, CellcyclingPlotSettings] = st.session_state[
    "Cellcycling_plots_settings"
]


def clear_y_plot_limit(
    plot_limits: Dict[str, List[Union[None, float]]], which: str = "both"
) -> None:
    if which == "y":
        plot_limits["y"] = [None, None]
    elif which == "y2":
        plot_limits["y2"] = [None, None]
    elif which == "both":
        plot_limits["y"] = [None, None]
        plot_limits["y2"] = [None, None]
    else:
        raise RuntimeError


def cell_cycling_plotter_widget(
    plot_settings: CellcyclingPlotSettings, unique_id: str
) -> None:

    # Define an annotation editor if there is a plot to which the annotations can be
    # added (plot_limits will be initialized on plot change and a rerun will be triggered)
    if plot_settings.limits["x"][0] != None:

        logger.info("Entering annotation options menu")

        with st.expander("Annotation editor", expanded=False):
            st.markdown("###### Global annotation settings")

            # Let the user define the annotation font size and color
            col1, col2 = st.columns(2)

            with col1:
                plot_settings.annotation_size = int(
                    st.number_input(
                        "Enter the dimension of the annotation font",
                        min_value=4,
                        value=plot_settings.annotation_size,
                        key=f"annotation_size_{unique_id}",
                    )
                )
                logger.debug(f"-> Annotation size: {plot_settings.annotation_size}")

            with col2:
                plot_settings.annotation_color = st.color_picker(
                    "Select annotation color",
                    value=plot_settings.annotation_color,
                    key=f"annotation_color_{unique_id}",
                )
                logger.debug(f"-> Annotation color: {plot_settings.annotation_color}")

            # Define and annotation editor in which the user can select the mode of
            # operation, the annotation content and its x-y position
            st.markdown("###### Edit annotation")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                mode = st.radio(
                    "Select operation",
                    ["Add new", "Edit existing"],
                    key=f"mode_radio_{unique_id}",
                )
                logger.debug(f"-> Annotation editor mode: {mode}")

            with col2:
                if mode == "Add new":
                    annotation = st.text_input(
                        "Enter the annotation content", key=f"annotation_text_{unique_id}"
                    )
                else:
                    annotation = st.selectbox(
                        "Select annotation",
                        [text for text in plot_settings.annotations.keys()],
                        key=f"annotation_select_{unique_id}",
                    )
                logger.debug(f"-> Annotation: {annotation}")

            with col3:
                x_position = st.slider(
                    "X position",
                    min_value=float(plot_settings.limits["x"][0]),
                    max_value=float(plot_settings.limits["x"][1]),
                    value=plot_settings.annotations[annotation][0]
                    if annotation in plot_settings.annotations
                    else None,
                    step=0.1,
                    key=f"annotation_x_{unique_id}",
                )
                logger.debug(f"-> Annotation X position: {x_position}")

            with col4:
                y_position = st.slider(
                    "Y position",
                    min_value=float(plot_settings.limits["y_annotation_reference"][0]),
                    max_value=float(plot_settings.limits["y_annotation_reference"][1]),
                    value=plot_settings.annotations[annotation][1]
                    if annotation in plot_settings.annotations
                    else None,
                    step=0.1,
                    key=f"annotation_y_{unique_id}",
                )
                logger.debug(f"-> Annotation Y position: {y_position}")

            col1, col2 = st.columns(2)

            with col1:
                if mode == "Edit existing":
                    remove = st.button(
                        "❌ Remove annotation",
                        disabled=True if annotation is None else False,
                        key=f"annotation_remove_{unique_id}",
                    )
                pass

            with col2:
                apply = False
                if mode == "Add new":
                    apply = st.button(
                        "✅ Apply",
                        key=f"annotation_apply_{unique_id}",
                        disabled=True if annotation == "" else False,
                    )

            if mode == "Edit existing":
                if remove:
                    logger.info(f"REMOVE annotation: '{annotation}'")
                    del plot_settings.annotations[annotation]
                    st.experimental_rerun()

            if apply or mode == "Edit existing":
                if annotation is not None and annotation != "":
                    logger.info(
                        f"SET annotation '{annotation}' to x: {x_position}, y: {y_position}"
                    )
                    plot_settings.annotations[annotation] = [x_position, y_position]

    # Initialize a set of columns on top of the plot section to hold buttons
    chide, cunhide, crefresh = st.columns(3)

    # Define an unhide button to unhide all the manually hided cycles
    with cunhide:
        unhide = st.button("👁 Unhide all", key=f"unhide_{unique_id}")

        if unhide:
            st.info("UNHIDE all manually hidden data points")
            for container in available_containers:
                for experiment in container._experiments:
                    experiment.unhide_all_cycles()

    logger.info("Rendering Plot section")
    col1, col2 = st.columns([3.5, 1])

    # Define a small column on the right to hold the plot options
    with col2:

        logger.info("Entering plot options menu")

        with st.expander("Series selector"):
            st.markdown("###### Series selector")

            plot_settings.primary_axis_name = st.selectbox(
                "Select the dataset for the primary Y axis",
                Y_OPTIONS,
                index=Y_OPTIONS.index(plot_settings.primary_axis_name)
                if plot_settings.primary_axis_name
                else 0,
                on_change=clear_y_plot_limit,
                args=[plot_settings.limits],
                key=f"primary_y_name_{unique_id}"
                # kwargs={"which": "y"},
            )
            logger.debug(f"-> Primary Y series: {plot_settings.primary_axis_name}")

            sub_Y_OPTIONS = [
                opt for opt in Y_OPTIONS if opt != plot_settings.primary_axis_name
            ]
            plot_settings.secondary_axis_name = st.selectbox(
                "Select the dataset for the secondary Y axis",
                sub_Y_OPTIONS,
                index=sub_Y_OPTIONS.index(plot_settings.secondary_axis_name)
                if plot_settings.secondary_axis_name
                and plot_settings.secondary_axis_name in sub_Y_OPTIONS
                else 0,
                on_change=clear_y_plot_limit,
                args=[plot_settings.limits],
                key=f"secondary_y_name_{unique_id}"
                # kwargs={"which": "y2"},
            )
            logger.debug(f"-> Secondary Y series: {plot_settings.secondary_axis_name}")

            Y_MODES = ["Both", "Only primary", "Only secondary"]
            plot_settings.y_axis_mode = st.radio(
                "Select which Y axis series to show",
                Y_MODES,
                index=Y_MODES.index(plot_settings.y_axis_mode)
                if plot_settings.y_axis_mode
                else 0,
                key=f"y_mode_{unique_id}",
            )
            logger.debug(f"-> Y axis mode: {plot_settings.y_axis_mode}")

            volume_is_available = True
            for container in available_containers:
                for name in container.get_experiment_names:
                    experiment_id = status.get_index_of(name)
                    experiment = status[experiment_id]
                    if experiment.volume is None:
                        volume_is_available = False
                        break

            plot_settings.scale_by_volume = st.checkbox(
                "Scale values by volume",
                value=plot_settings.scale_by_volume if volume_is_available else False,
                disabled=not volume_is_available,
                key=f"volume_{unique_id}",
            )
            logger.debug(f"-> Scale by volume: {plot_settings.scale_by_volume}")

            area_is_available = True
            for container in available_containers:
                for name in container.get_experiment_names:
                    experiment_id = status.get_index_of(name)
                    experiment = status[experiment_id]
                    if experiment.area is None:
                        area_is_available = False
                        break

            plot_settings.scale_by_area = st.checkbox(
                "Scale values by area",
                value=plot_settings.scale_by_area if area_is_available else False,
                disabled=not area_is_available,
                key=f"area_{unique_id}",
            )
            logger.debug(f"-> Scale by area: {plot_settings.scale_by_area}")

        with st.expander("Graph options"):
            st.markdown("###### Graph options")

            available_MARKERS = [m for m in MARKERS.keys()]
            plot_settings.primary_axis_marker = st.selectbox(
                "Select primary Y axis markers",
                available_MARKERS,
                index=available_MARKERS.index(plot_settings.primary_axis_marker)
                if plot_settings.primary_axis_marker
                else 0,
                key=f"primary_marker_{unique_id}",
            )
            logger.debug(f"-> Primary axis marker: {plot_settings.primary_axis_marker}")

            available_MARKERS = [
                m for m in MARKERS.keys() if m != plot_settings.primary_axis_marker
            ]
            plot_settings.secondary_axis_marker = st.selectbox(
                "Select secondary Y axis markers",
                available_MARKERS,
                index=available_MARKERS.index(plot_settings.secondary_axis_marker)
                if plot_settings.secondary_axis_marker
                and plot_settings.secondary_axis_marker in available_MARKERS
                else 0,
                key=f"secondary_marker_{unique_id}",
            )
            logger.debug(f"-> Secondary axis marker: {plot_settings.secondary_axis_marker}")

            plot_settings.marker_size = int(
                st.number_input(
                    "Marker size",
                    min_value=1,
                    value=plot_settings.marker_size,
                    step=1,
                    key=f"marker_size_{unique_id}",
                )
            )
            logger.debug(f"-> Marker size: {plot_settings.marker_size}")

            plot_settings.marker_with_border = st.checkbox(
                "Marker with border",
                value=plot_settings.marker_with_border,
                key=f"marker_border_{unique_id}",
            )
            logger.debug(f"-> Marker with border: {plot_settings.marker_with_border}")

            options = []
            if plot_settings.y_axis_mode == "Only primary":
                options = ["Primary", "None"]
            elif plot_settings.y_axis_mode == "Only secondary":
                options = ["Secondary", "None"]
            else:
                options = ["Primary", "Secondary", "None"]

            plot_settings.which_grid = st.radio(
                "Y-axis grid selector",
                options=options,
                index=options.index(plot_settings.which_grid)
                if plot_settings.which_grid and plot_settings.which_grid in options
                else 0,
                key=f"grid_mode_{unique_id}",
            )
            logger.debug(f"-> Grid mode: {plot_settings.which_grid}")

            plot_settings.font_size = int(
                st.number_input(
                    "Label/tick font size",
                    min_value=4,
                    value=plot_settings.font_size,
                    key=f"label_size_{unique_id}",
                )
            )
            logger.debug(f"-> Label/tick font size: {plot_settings.font_size}")

            plot_settings.axis_font_size = int(
                st.number_input(
                    "Label font size",
                    min_value=4,
                    value=plot_settings.axis_font_size,
                    key=f"axis_title_font_size_{unique_id}",
                )
            )
            logger.debug(f"-> Axis title font size: {plot_settings.axis_font_size}")

            plot_settings.height = int(
                st.number_input(
                    "Plot height",
                    min_value=10,
                    max_value=2000,
                    value=plot_settings.height,
                    step=10,
                    key=f"plot_height_{unique_id}",
                )
            )
            logger.debug(f"-> Plot height: {plot_settings.height}")

    with col1:

        logger.info("Entering plot section")

        # Create a figure object with the secondary y-axis option enabled
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Iterate over each container
        for container in available_containers:

            logger.info(f"Plotting container {container.name}")

            offset = 0
            experiment: Experiment

            # Iterate over each cell_cycling object in the container
            for cycling_index, experiment in enumerate(container):

                if cycling_index != 0:
                    offset += container.max_cycles_numbers[cycling_index - 1] + 1

                cycle_index = [n + offset for n in experiment.cellcycling.numbers]

                primary_label, primary_axis = get_data_series(
                    plot_settings.primary_axis_name,
                    cycling_index,
                    container,
                    scale_by_volume=plot_settings.scale_by_volume,
                    scale_by_area=plot_settings.scale_by_area,
                )
                secondary_label, secondary_axis = get_data_series(
                    plot_settings.secondary_axis_name,
                    cycling_index,
                    container,
                    scale_by_volume=plot_settings.scale_by_volume,
                    scale_by_area=plot_settings.scale_by_area,
                )

                primary_marker = MARKERS[plot_settings.primary_axis_marker]
                secondary_marker = MARKERS[plot_settings.secondary_axis_marker]

                if plot_settings.y_axis_mode != "Only secondary":
                    fig.add_trace(
                        go.Scatter(
                            x=cycle_index,
                            y=primary_axis,
                            name=container.name,
                            mode="markers",
                            marker_symbol=primary_marker,
                            marker=dict(
                                size=plot_settings.marker_size,
                                line=dict(width=1, color="DarkSlateGrey")
                                if plot_settings.marker_with_border
                                else None,
                            ),
                            line=dict(color=container.hex_color),
                            showlegend=True if cycling_index == 0 else False,
                        ),
                        secondary_y=False,
                    )

                if plot_settings.y_axis_mode != "Only primary":
                    fig.add_trace(
                        go.Scatter(
                            x=cycle_index,
                            y=secondary_axis,
                            name=container.name,
                            mode="markers",
                            marker_symbol=secondary_marker,
                            marker=dict(
                                size=plot_settings.marker_size,
                                line=dict(width=1, color="DarkSlateGrey")
                                if plot_settings.marker_with_border
                                else None,
                            ),
                            line=dict(color=container.hex_color),
                            showlegend=True
                            if plot_settings.y_axis_mode == "Only secondary"
                            and cycling_index == 0
                            else False,
                        ),
                        secondary_y=True,
                    )

        if plot_settings.annotations != {}:

            for text, position in plot_settings.annotations.items():
                fig.add_annotation(
                    x=position[0],
                    y=position[1],
                    text=text,
                    font_size=plot_settings.annotation_size,
                    font_color=plot_settings.annotation_color,
                    showarrow=False,
                )

        # Apply proper formatting to the x and y_a axis
        fig.update_xaxes(
            title_text="Cycle number",
            showline=True,
            linecolor="black",
            gridwidth=1,
            gridcolor="#DDDDDD",
            title_font={"size": plot_settings.axis_font_size},
        )

        fig.update_yaxes(
            title_text=f"{plot_settings.primary_axis_marker}  {primary_label}",
            # color=primary_axis_color,
            secondary_y=False,
            range=plot_settings.limits["y"],
            showline=True,
            linecolor="black",
            gridwidth=1,
            gridcolor="#DDDDDD" if plot_settings.which_grid == "Primary" else None,
            title_font={"size": plot_settings.axis_font_size},
        )
        fig.update_yaxes(
            title_text=f"{plot_settings.secondary_axis_marker}  {secondary_label}",
            # color=secondary_axis_color,
            secondary_y=True,
            range=plot_settings.limits["y2"],
            showline=True,
            linecolor="black",
            gridwidth=1,
            gridcolor="#DDDDDD" if plot_settings.which_grid == "Secondary" else None,
            title_font={"size": plot_settings.axis_font_size},
        )

        # Apply proper formatting to legend and plot background
        fig.update_layout(
            font=dict(size=plot_settings.font_size),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.0,
                xanchor="center",
                x=0.5,
            ),
            plot_bgcolor="#FFFFFF",
        )

        # Use the plotly event widget to allow for interactive selection of points
        # on the plot
        selected_points = plotly_events(
            fig,
            click_event=False,
            select_event=True,
            override_height=plot_settings.height,
            key=f"plotly_events_{unique_id}",
        )

        # Get the figure data to localize the selected points and to get the plot limits
        figure_data = fig.full_figure_for_development(warn=False)

        if selected_points != [] and selected_points is not None:
            selected_cycles = ", ".join([str(point["x"]) for point in selected_points])
            st.success(f"Currently selected points: {selected_cycles}")
            logger.info(f"SELECTED points: {selected_points}")

        # render the cycle hide button (enabled only if there are selected points)
        with chide:
            hide = st.button(
                "🚫 Hide cycles",
                disabled=False
                if selected_points != [] and selected_points is not None
                else True,
                key=f"hide_{unique_id}",
            )

            if hide:
                logger.info("HIDING selected points")
                trace_list = [obj["name"] for obj in figure_data["data"]]

                for selected_point in selected_points:
                    container_name = trace_list[selected_point["curveNumber"]]
                    container_idx = [obj.name for obj in available_containers].index(
                        container_name
                    )
                    available_containers[container_idx].hide_cycle(selected_point["x"])

                st.experimental_rerun()

        # Render a referesh button to manually trigger a rerun
        with crefresh:
            refresh = st.button("♻ Refresh", key=f"refresh_{unique_id}")

            if refresh:
                st.experimental_rerun()

        # Evaluate the current plot limits
        xrange = (
            None
            if figure_data.layout.xaxis.range is None
            else [float(x) for x in figure_data.layout.xaxis.range]
        )
        yrange = (
            None
            if figure_data.layout.yaxis.range is None
            else [float(y) for y in figure_data.layout.yaxis.range]
        )

        y2range = (
            [float(y) for y in figure_data.layout.yaxis2.range]
            if hasattr(figure_data.layout, "yaxis2")
            else None
        )

        # Update the axis ranges if a change is detected. Exclude the axis not currently
        # plotted to avoid continuous rerun of the page
        if (
            plot_settings.limits["x"] != xrange
            or (
                plot_settings.limits["y"] != yrange
                and plot_settings.y_axis_mode != "Only secondary"
            )
            or (
                plot_settings.limits["y2"] != y2range
                and plot_settings.y_axis_mode != "Only primary"
            )
        ):
            plot_settings.limits["x"] = xrange
            plot_settings.limits["y"] = (
                yrange if yrange is not None else plot_settings.limits["y"]
            )
            plot_settings.limits["y2"] = (
                y2range if y2range is not None else plot_settings.limits["y2"]
            )
            plot_settings.limits["y_annotation_reference"] = (
                yrange if yrange is not None else y2range
            )

            logger.debug(
                f"-> Limits: x={plot_settings.limits['x']}, y1={plot_settings.limits['y']}, y2={plot_settings.limits['y2']}"
            )
            st.experimental_rerun()

    with col2:

        logger.info("Re-Entering plot options menu to set y-range and export")

        with st.expander("Y axis range"):

            figure_data = fig.full_figure_for_development(warn=False)

            if plot_settings.y_axis_mode != "Only secondary":
                st.markdown("###### primary Y-axis range")
                # y1_range = figure_data.layout.yaxis.range
                y1_max = float(
                    st.number_input(
                        "Maximum y-value",
                        value=plot_settings.limits["y"][1],
                        step=1e-3,
                        key=f"y1_max_{unique_id}",
                    )
                )
                logger.debug(f"-> Max Y1: {y1_max}")

                y1_min = float(
                    st.number_input(
                        "Minimum y-value",
                        value=plot_settings.limits["y"][0],
                        step=1e-3,
                        key=f"y1_min_{unique_id}",
                    )
                )
                logger.debug(f"-> Min Y1: {y1_min}")

                if (
                    plot_settings.limits["y"][0] != y1_min
                    or plot_settings.limits["y"][1] != y1_max
                ):
                    plot_settings.limits["y"] = [y1_min, y1_max]
                    logger.info(f"Setting Y limits to {plot_settings.limits['y']}")
                    st.experimental_rerun()

            if plot_settings.y_axis_mode != "Only primary":
                st.markdown("###### secondary Y-axis range")
                # y2_range = figure_data.layout.yaxis2.range
                y2_max = float(
                    st.number_input(
                        "Maximum y-value",
                        value=plot_settings.limits["y2"][1],
                        step=1e-3,
                        key=f"y2_max_{unique_id}",
                    )
                )
                logger.debug(f"-> Max Y2: {y2_max}")

                y2_min = float(
                    st.number_input(
                        "Minimum y-value",
                        value=plot_settings.limits["y2"][0],
                        step=1e-3,
                        key=f"y2_min_{unique_id}",
                    )
                )
                logger.debug(f"-> Min Y2: {y2_min}")

                if (
                    plot_settings.limits["y2"][0] != y2_min
                    or plot_settings.limits["y2"][1] != y2_max
                ):
                    plot_settings.limits["y2"] = [y2_min, y2_max]
                    logger.info(f"Setting Y2 limits to {plot_settings.limits['y2']}")
                    st.experimental_rerun()

        # Add an export option
        with st.expander("Export"):
            st.markdown("###### Export")

            available_formats = ["png", "jpeg", "svg", "pdf"]
            plot_settings.format = st.selectbox(
                "Select the format of the file",
                available_formats,
                index=available_formats.index(plot_settings.format)
                if plot_settings.format
                else 0,
                key=f"format_export_{unique_id}",
            )
            logger.debug(f"-> Export format: {plot_settings.format}")

            plot_settings.width = int(
                st.number_input(
                    "Plot width",
                    min_value=10,
                    max_value=4000,
                    value=plot_settings.width,
                    key=f"plot_width_{unique_id}",
                )
            )
            logger.debug(f"-> Export width: {plot_settings.width}")

            # Redefine layout options to account for user selected width
            fig.update_layout(
                height=plot_settings.height,
                width=plot_settings.width,
                font=dict(size=plot_settings.font_size),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.0,
                    xanchor="center",
                    x=0.5,
                ),
                plot_bgcolor="#FFFFFF",
            )

            st.download_button(
                "Download plot",
                data=fig.to_image(format=plot_settings.format),
                file_name=f"cycle_plot.{plot_settings.format}",
                on_click=lambda msg: logger.info(msg),
                args=[f"DOWNLOAD cycle_plot.{plot_settings.format}"],
                key=f"download_{unique_id}",
            )

            logger.info("FORCING RERUN AT END OF PAGE")
            force_update_once()


try:

    logger.info("RUNNING cell-cycling plotter page rendering")

    # Check if the main page has set up the proper session state variables and check that at
    # least one experiment has been loaded
    enable = True
    if "ProgramStatus" not in st.session_state:
        enable = False
    else:
        status: ProgramStatus = st.session_state["ProgramStatus"]
        if len(status) == 0:
            enable = False

    with st.sidebar:
        st.info(f'Session token: {st.session_state["Token"]}')

    # Set the title of the page and print some generic instruction
    st.title("Cell-cycling plotter")

    st.write(
        """In this page you can analyze and compare cell-cycling experiments carried out in different
        conditions comparing their capacity retention and efficiencies."""
    )

    if enable:

        # Define a two tab page with a container editor and a plotter
        container_tab, plot_tab = st.tabs(["Container editor", "Container plotter"])

        # Define the container editor tab
        with container_tab:

            logger.info("Rendering container editor tab")

            with st.expander("Create new experiment container", expanded=True):

                logger.info("Entering new container creator")

                st.markdown("#### Create a new experiment container")
                st.write(
                    """In this tab you can create new experiments containers to hold different
                    cell-cycling experiments and edit the ones eventually available"""
                )

                # Create a setup section in which the user can create a new experiment given a
                # name, a list of experiments to load and a custom color
                col1, col2, col3 = st.columns([2, 2, 1])

                with col1:
                    container_name = st.text_input(
                        "Insert the name of the container", value=""
                    )
                    logger.debug(f"-> Container name: {container_name}")

                with col2:
                    experiments_names = st.multiselect(
                        "Select the experiments to add to the container",
                        status.get_experiment_names(),
                        key="add_experiment_to_new",
                    )
                    logger.debug(f"-> Experiments names: {experiments_names}")

                with col3:
                    container_color = st.color_picker(
                        "Select the container color",
                        value=get_plotly_color(len(available_containers)),
                    )
                    logger.debug(f"-> Container color: {container_color}")

                apply = st.button(
                    "➕ Create container",
                    key="create container",
                    disabled=True if container_name == "" else False,
                )

                if apply:

                    logger.info("PRESSED apply button")

                    if container_name not in [obj.name for obj in available_containers]:

                        logger.info(
                            f"Creating a new container named {container_name} (color {container_color}) containing experiment {experiments_names}"
                        )

                        new_container = ExperimentContainer(
                            container_name, color=container_color
                        )

                        if experiments_names != []:
                            for name in experiments_names:
                                id = status.get_index_of(name)
                                new_container.add_experiment(status[id])

                        available_containers.append(new_container)
                        st.experimental_rerun()

                    else:
                        st.error(f"ERROR: the name '{container_name}' is already taken.")
                        logger.error(f"The container '{container_name}' already exists.")

            # If there are already loaded container allow the user to edit or delete them
            if available_containers != []:

                with st.expander("Edit experiment container", expanded=False):
                    logger.info("Entering container editor")

                    st.markdown("#### Edit an existing container")

                    col1, col2 = st.columns(2)

                    with col1:
                        selected_container_name = st.selectbox(
                            "Select the container to edit",
                            [obj.name for obj in available_containers],
                        )
                        logger.debug(f"-> Selected container: {selected_container_name}")

                        delete = st.button("❌ Delete the container")

                        if delete:
                            logger.info(f"REMOVING container '{selected_container_name}'")
                            idx = [obj.name for obj in available_containers].index(
                                selected_container_name
                            )
                            del available_containers[idx]
                            st.experimental_rerun()

                        st.markdown("---")

                        operation_mode = st.radio(
                            "Select the operation mode",
                            ["Change reference", "Add experiment", "Remove experiment"],
                        )

                    if selected_container_name != None:

                        container_idx: int = [
                            container.name for container in available_containers
                        ].index(selected_container_name)

                        selected_container: ExperimentContainer = available_containers[
                            container_idx
                        ]

                        with col2:

                            if operation_mode == "Change reference":

                                logger.info(
                                    "Render section to add change reference cycle of the container"
                                )
                                st.markdown("###### Change container reference")

                                current_reference = selected_container.reference
                                exp_index = int(
                                    st.number_input(
                                        "Select experiment index",
                                        value=current_reference[0],
                                        min_value=0,
                                        max_value=len(selected_container) - 1,
                                        step=1,
                                        disabled=True
                                        if len(selected_container) == 0
                                        else False,
                                    )
                                )

                                cycle_index = int(
                                    st.number_input(
                                        "Select cycle index",
                                        value=current_reference[1],
                                        min_value=0,
                                        max_value=len(
                                            selected_container[exp_index]._cycles
                                        )-1,
                                        step=1,
                                        disabled=True
                                        if len(selected_container) == 0
                                        else False,
                                    )
                                )

                                apply_ref = st.button("🗒️ Apply new reference")

                                if apply_ref:
                                    selected_container.reference = [exp_index, cycle_index]
                                    st.experimental_rerun()

                                # selected_container.

                            elif operation_mode == "Add experiment":
                                logger.info(
                                    "Render section to add new experiment to container"
                                )
                                st.markdown("###### Add another experiment")

                                valid_exp_names = [
                                    name
                                    for name in status.get_experiment_names()
                                    if name not in selected_container.get_experiment_names
                                ]
                                experiment_name = st.selectbox(
                                    "Select the experiments to add to the container",
                                    valid_exp_names,
                                )
                                logger.debug(f"-> Selected experiment: '{experiment_name}'")

                                add = st.button(
                                    "➕ Add experiment",
                                    disabled=True if experiment_name is None else False,
                                )

                                if add:
                                    logger.info(
                                        f"ADD experiment {experiment_name} to container {selected_container_name}"
                                    )
                                    id = status.get_index_of(experiment_name)
                                    selected_container.add_experiment(status[id])
                                    st.experimental_rerun()

                            else:
                                logger.info(
                                    "Render section to remove experiments from a container"
                                )
                                st.markdown("###### Remove a currently loaded experiment")

                                get_experiment_names = st.multiselect(
                                    "Select the experiments to remove from the container",
                                    [
                                        name
                                        for name in selected_container.get_experiment_names
                                    ],
                                    key="add_experiment_to_existing",
                                )
                                logger.debug(
                                    f"-> Selected experiments: {get_experiment_names}"
                                )

                                remove = st.button(
                                    "➖ Remove experiment",
                                    disabled=True if get_experiment_names == [] else False,
                                )

                                if remove:
                                    logger.info(
                                        f"REMOVE experiments {get_experiment_names} from container {selected_container_name}"
                                    )

                                    for name in get_experiment_names:
                                        exp_index = selected_container.get_index_from_name(name)

                                        if selected_container.reference[0] == exp_index:
                                            selected_container.reference = [0, 0]

                                    for name in get_experiment_names:
                                        selected_container.remove_experiment(name)
                                    st.experimental_rerun()

                    else:
                        st.info(
                            "Cannot show edit menu, no experiment container has been selected yet."
                        )

        # Define a plot tab to hold the plotted data
        with plot_tab:

            # Visualize something only if there are available containers
            if available_containers != []:

                logger.info("Entering Container plotter tab")

                st.markdown("#### Cell-cycling plotter")
                st.write(
                    """In this tab you can create multiple cell cycling plots and interactively setting
                    their appearence. To create a plot select a plot name and click 'add'."""
                )

                cname, cadd = st.columns([3, 1])

                with cname:
                    plot_name = st.text_input("Select the name of the new plot")

                with cadd:
                    st.write("")
                    st.write("")
                    add = st.button("➕ Add", disabled=True if plot_name == "" else False)

                if add:
                    if plot_name not in plot_settings_dict:
                        plot_settings_dict[plot_name] = CellcyclingPlotSettings()
                    else:
                        st.warning(f"WARNING: The name {plot_name} is already in use")

                st.markdown("---")

                if plot_settings_dict != {}:

                    plot_names: List[str] = [name for name in plot_settings_dict.keys()]

                    st.markdown("###### Plot selector")

                    col1, col2 = st.columns([3, 1])

                    with col1:
                        selected_plot = st.selectbox("Select the plot to show", plot_names)
                        logger.debug(f"-> Selected plot name: {selected_plot})")

                    with col2:
                        st.write("")
                        st.write("")
                        remove = st.button("❌ Delete plot")

                    if remove:
                        logger.info(f"REMOVED plot name: {selected_plot})")
                        del plot_settings_dict[selected_plot]
                        st.experimental_rerun()

                    st.markdown("---")

                    idx = plot_names.index(selected_plot)

                    logger.info(
                        f"RENDERING cellcycling plot {idx} (title: {selected_plot})"
                    )
                    cell_cycling_plotter_widget(plot_settings_dict[selected_plot], idx)

                else:
                    st.info("Please create a cell-cycling plot")

            else:
                st.info(
                    """**No container has been created yet** \n\n Please go to the container
                    editor tab and define at least one experiment container."""
                )

    # If there are no experiments in the buffer suggest to the user to load data form the main page
    else:
        st.info(
            """**No experiment has been loaded yet** \n\n Please go to the file manager 
        page and procede to upload and properly edit the required experiment files before
        accessing this page."""
        )

except st._RerunException:
    logger.info("EXPERIMENTAL RERUN CALLED")
    raise

except:
    logger.exception(
        f"Unexpected exception occurred during cell-cycling plotter page execution:\n\n {traceback.print_exception(*sys.exc_info())}"
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
    logger.debug("-> Cell-cycling plotter page run completed succesfully")
