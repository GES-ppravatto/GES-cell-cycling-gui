from typing import Dict, List, Tuple, Union
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_plotly_events import plotly_events

from core.gui_core import (
    Experiment,
    ProgramStatus,
    get_plotly_color,
    set_production_page_style,
)

from echemsuite.cellcycling.cycles import CellCycling

# Define an Experiment container to hold all the experiments related to a single multi-parameter
# cycling experiment
class ExperimentContainer:
    def __init__(self, name: str, color: str = None) -> None:
        self._name = name
        self._color = color if color is not None else "#000000"
        self._experiments: List[Experiment] = []

    def __iter__(self) -> Tuple[str, CellCycling]:
        for experiment in self._experiments:
            yield experiment.name, experiment.cellcycling

    @property
    def name(self) -> str:
        return self._name

    @property
    def get_experiment_names(self) -> List[str]:
        return [name for name, _ in self]

    @property
    def hex_color(self) -> str:
        return self._color

    @property
    def max_cycles_numbers(self) -> List[int]:
        numbers = []
        for _, obj in self:
            obj.get_numbers()
            numbers.append(obj._numbers[-1])
        return numbers

    def add_experiment(self, experiment: Experiment) -> None:
        if experiment not in self._experiments:
            self._experiments.append(experiment)
        else:
            raise RuntimeError

    def remove_experiment(self, name: str) -> None:
        if name in [obj.name for obj in self._experiments]:
            id = [obj.name for obj in self._experiments].index(name)
            del self._experiments[id]
        else:
            raise ValueError

    def clear_experiments(self) -> None:
        self._experiments = {}

    def hide_cycle(self, cumulative_id: int) -> None:
        cumulative_sum = []
        for i, number in enumerate(self.max_cycles_numbers):
            cumulative_sum.append(number if i == 0 else cumulative_sum[-1] + number + 1)

        experiment_id, cycle_id = None, None
        for i, threshold in enumerate(cumulative_sum):
            if cumulative_id <= threshold:
                experiment_id = i
                if i == 0:
                    cycle_id = cumulative_id
                else:
                    cycle_id = cumulative_id - cumulative_sum[i - 1] - 1
                break

        self._experiments[experiment_id].hide_cycle(cycle_id)


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
    "Average power - Discharge"
]


# Define a function to exracte the wanted dataset from a cellcycling experiment give the label
def get_data_series(
    option: str,
    cellcycling: CellCycling,
    volume: Union[float, None] = None,
    area: Union[float, None] = None,
) -> Tuple[str, List[float]]:

    if option not in Y_OPTIONS:
        raise TypeError

    if volume is not None and volume <= 0:
        raise ValueError

    if option == "Capacity retention":
        return "Capacity retention (%)", cellcycling.capacity_retention
    elif option == "Columbic efficiency":
        return "Columbic efficiency (%)", cellcycling.coulomb_efficiencies
    elif option == "Energy efficiency":
        return "Energy efficiency (%)", cellcycling.energy_efficiencies
    elif option == "Voltaic Efficiency":
        return "Voltaic Efficiency (%)", cellcycling.voltage_efficiencies
    elif option == "Total energy - Discharge":
        total_energies = [cycle.discharge.total_energy for cycle in cellcycling]
        if volume is None and area is None:
            return "discharge total energy (mWh)", total_energies
        elif volume is not None and area is None:
            normalized_energies = [energy / (1000 * volume) for energy in total_energies]
            return "normalized discharge total energy (Wh/L)", normalized_energies
        elif volume is None and area is not None:
            normalized_energies = [energy / (1000 * area) for energy in total_energies]
            return (
                "normalized discharge total energy (Wh/cm<sup>2</sup>)",
                normalized_energies,
            )
        elif volume is not None and area is not None:
            normalized_energies = [
                energy / (1000 * volume * area) for energy in total_energies
            ]
            return (
                "normalized discharge total energy (Wh/L cm<sup>2</sup>)",
                normalized_energies,
            )
        else:
            raise RuntimeError

    elif option == "Total capacity - Discharge":
        total_capacities = [cycle.discharge.capacity for cycle in cellcycling]

        if volume is None and area is None:
            return "discharge total capacity (mAh)", total_capacities
        elif volume is not None and area is None:
            normalized_energies = [
                capacity / (1000 * volume) for capacity in total_capacities
            ]
            return "normalized discharge total capacity (Ah/L)", normalized_energies
        elif volume is None and area is not None:
            normalized_energies = [
                capacity / (1000 * area) for capacity in total_capacities
            ]
            return (
                "normalized discharge total capacity (Ah/cm<sup>2</sup>)",
                normalized_energies,
            )
        elif volume is not None and area is not None:
            normalized_energies = [
                capacity / (1000 * volume * area) for capacity in total_capacities
            ]
            return (
                "normalized discharge total capacity (Ah/L cm<sup>2</sup>)",
                normalized_energies,
            )
        else:
            raise RuntimeError
    
    elif option == "Average power - Discharge":
        average_powers = [cycle.discharge.power.mean() for cycle in cellcycling]

        if volume is None and area is None:
            return "average power (W)", average_powers
        elif volume is not None and area is None:
            average_powers = [
                power / volume for power in average_powers
            ]
            return "normalized average power (W/L)", average_powers
        elif volume is None and area is not None:
            average_powers = [
                power / area for power in average_powers
            ]
            return (
                "normalized average power (W/cm<sup>2</sup>)",
                average_powers,
            )
        elif volume is not None and area is not None:
            average_powers = [
                power / (volume * area) for power in average_powers
            ]
            return (
                "normalized average power (W/L cm<sup>2</sup>)",
                average_powers,
            )
        else:
            raise RuntimeError

    else:
        raise RuntimeError


# Initialize the session state with the page specific variables
if "ExperimentContainers" not in st.session_state:
    st.session_state["ExperimentContainers"] = []
    st.session_state["CellCycling_plot_limits"] = {
        "x": [None, None],
        "y": [None, None],
        "y2": [None, None],
        "y_annotation_reference": [None, None],
    }
    st.session_state["PlotAnnotations"] = {}


def clear_y_plot_limit(which: str = "both") -> None:
    plot_limits = st.session_state["CellCycling_plot_limits"]
    if which == "y":
        plot_limits["y"] = [None, None]
    elif which == "y2":
        plot_limits["y2"] = [None, None]
    elif which == "both":
        plot_limits["y"] = [None, None]
        plot_limits["y2"] = [None, None]
    else:
        raise RuntimeError


# Check if the main page has set up the proper session state variables and check that at
# least one experiment has been loaded
enable = True
if "ProgramStatus" not in st.session_state:
    enable = False
else:
    status: ProgramStatus = st.session_state["ProgramStatus"]
    if len(status) == 0:
        enable = False

st.set_page_config(layout="wide")
set_production_page_style()

# Set the title of the page and print some generic instruction
st.title("Cell-cycling plotter")

st.write(
    """In this page you can analyze and compare cell-cycling experiments carried out in different
    conditions comparing their capacity retention and efficiencies."""
)

if enable:

    # Fetch fresh reference to the variables in session state
    available_containers: List[ExperimentContainer] = st.session_state[
        "ExperimentContainers"
    ]
    plot_limits: Dict[str, List[Union[None, float]]] = st.session_state[
        "CellCycling_plot_limits"
    ]
    annotation_dict: dict = st.session_state["PlotAnnotations"]

    # Define a two tab page with a container editor and a plotter
    container_tab, plot_tab = st.tabs(["Container editor", "Container plotter"])

    # Define the container editor tab
    with container_tab:

        with st.expander("Create new experiment container", expanded=True):

            st.markdown("#### Create a new experiment container")
            st.write(
                """In this tab you can create new experiments containers to hold different
                cell-cycling experiments and edit the ones eventually available"""
            )

            # Create a setup section in which the user can create a new experiment given a
            # name, a list of experiments to load and a custom color
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                container_name = st.text_input("Insert the name of the container", value="")

            with col2:
                experiments_names = st.multiselect(
                    "Select the experiments to add to the container",
                    status.get_experiment_names(),
                    key="add_experiment_to_new",
                )

            with col3:
                container_color = st.color_picker(
                    "Select the container color",
                    value=get_plotly_color(len(available_containers)),
                )

            apply = st.button(
                "➕ Create container",
                key="create container",
                disabled=True if container_name == "" else False,
            )

            if apply:

                if container_name not in [obj.name for obj in available_containers]:

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

        # If there are already loaded container allow the user to edit or delete them
        if available_containers != []:

            with st.expander("Edit experiment container", expanded=False):

                st.markdown("#### Edit an existing container")
                selected_container_name = st.selectbox(
                    "Select the container to edit",
                    [obj.name for obj in available_containers],
                )

                delete = st.button("❌ Delete the container")

                if delete:
                    idx = [obj.name for obj in available_containers].index(
                        selected_container_name
                    )
                    del available_containers[idx]
                    st.experimental_rerun()

                if selected_container_name != None:

                    container_idx: int = [
                        container.name for container in available_containers
                    ].index(selected_container_name)
                    selected_container: ExperimentContainer = available_containers[
                        container_idx
                    ]

                    st.markdown("---")
                    st.markdown("###### Add another experiment")

                    col1, col2 = st.columns([4, 1])

                    with col1:
                        valid_exp_names = [
                            name
                            for name in status.get_experiment_names()
                            if name not in selected_container.get_experiment_names
                        ]
                        experiment_name = st.selectbox(
                            "Select the experiments to add to the container",
                            valid_exp_names,
                        )

                    with col2:
                        st.write("")
                        st.write("")
                        add = st.button(
                            "➕ Add experiment",
                            disabled=True if experiment_name is None else False,
                        )

                    if add:
                        id = status.get_index_of(experiment_name)
                        selected_container.add_experiment(status[id])
                        st.experimental_rerun()

                    st.markdown("---")
                    st.markdown("###### Remove a currently loaded experiment")

                    col1, col2 = st.columns([4, 1])

                    with col1:
                        get_experiment_names = st.multiselect(
                            "Select the experiments to remove from the container",
                            [name for name in selected_container.get_experiment_names],
                            key="add_experiment_to_existing",
                        )

                    with col2:
                        st.write("")
                        st.write("")
                        remove = st.button(
                            "➖ Remove experiment",
                            disabled=True if get_experiment_names == [] else False,
                        )

                    if remove:
                        for name in experiments_names:
                            selected_container.remove_experiment(name)
                        st.experimental_rerun()

    # Define a plot tab to hold the plotted data
    with plot_tab:

        # Visualize something only if there are available containers
        if available_containers != []:

            st.markdown("#### Cell-cycling plotter")
            st.write(
                """In this tab you can create a cell cycling plot and interactively selecting
                its appearence"""
            )

            # Define an annotation editor if there is a plot to which the annotations can be
            # added (plot_limits will be initialized on plot change and a rerun will be triggered)
            if plot_limits["x"][0] != None:

                with st.expander("Annotation editor", expanded=False):
                    st.markdown("###### Global annotation settings")

                    # Let the user define the annotation font size and color
                    col1, col2 = st.columns(2)

                    with col1:
                        annotation_size = st.number_input(
                            "Enter the dimension of the annotation font",
                            min_value=4,
                            value=12,
                        )

                    with col2:
                        annotation_color = st.color_picker(
                            "Select annotation color", value="#000000"
                        )

                    # Define and annotation editor in which the user can select the mode of
                    # operation, the annotation content and its x-y position
                    st.markdown("###### Edit annotation")

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        mode = st.radio("Select operation", ["Add new", "Edit existing"])

                    with col2:
                        if mode == "Add new":
                            annotation = st.text_input("Enter the annotation content")
                        else:
                            annotation = st.selectbox(
                                "Select annotation",
                                [text for text in annotation_dict.keys()],
                            )

                    with col3:
                        x_position = st.slider(
                            "X position",
                            min_value=float(plot_limits["x"][0]),
                            max_value=float(plot_limits["x"][1]),
                            step=0.1,
                        )

                    with col4:
                        y_position = st.slider(
                            "Y position",
                            min_value=float(plot_limits["y_annotation_reference"][0]),
                            max_value=float(plot_limits["y_annotation_reference"][1]),
                            step=0.1,
                        )

                    col1, col2 = st.columns(2)

                    with col1:
                        if mode == "Edit existing":
                            remove = st.button(
                                "❌ Remove annotation",
                                key="annotation_remove",
                                disabled=True if annotation is None else False,
                            )
                        pass

                    with col2:
                        if mode == "Add new":
                            apply = st.button(
                                "✅ Apply",
                                key="annotation_apply",
                                disabled=True if annotation == "" else False,
                            )

                    if mode == "Edit existing":
                        if remove:
                            del annotation_dict[annotation]
                            st.experimental_rerun()

                    if apply or mode == "Edit existing":
                        if annotation is not None and annotation != "":
                            annotation_dict[annotation] = [x_position, y_position]

            # Initialize a set of columns on top of the plot section to hold buttons
            chide, cunhide, crefresh = st.columns(3)

            # Define an unhide button to unhide all the manually hided cycles
            with cunhide:
                unhide = st.button("👁 Unhide all")

                if unhide:
                    for container in available_containers:
                        for experiment in container._experiments:
                            experiment.unhide_all_cycles()

            col1, col2 = st.columns([3.5, 1])

            # Define a small column on the right to hold the plot options
            with col2:

                with st.expander("Series selector"):
                    st.markdown("###### Series selector")

                    primary_axis_name = st.selectbox(
                        "Select the dataset for the primary Y axis",
                        Y_OPTIONS,
                        on_change=clear_y_plot_limit,
                        # kwargs={"which": "y"},
                    )
                    secondary_axis_name = st.selectbox(
                        "Select the dataset for the secondary Y axis",
                        [option for option in Y_OPTIONS if option != primary_axis_name],
                        on_change=clear_y_plot_limit,
                        # kwargs={"which": "y2"},
                    )

                    y_axis_mode = st.radio(
                        "Select which Y axis series to show",
                        ["Both", "Only primary", "Only secondary"],
                    )

                    volume_is_available = True
                    for container in available_containers:
                        for name in container.get_experiment_names:
                            experiment_id = status.get_index_of(name)
                            experiment = status[experiment_id]
                            if experiment.volume is None:
                                volume_is_available = False
                                break

                    scale_by_volume = st.checkbox(
                        "Scale values by volume",
                        value=False,
                        disabled=not volume_is_available,
                    )

                    area_is_available = True
                    for container in available_containers:
                        for name in container.get_experiment_names:
                            experiment_id = status.get_index_of(name)
                            experiment = status[experiment_id]
                            if experiment.area is None:
                                area_is_available = False
                                break

                    scale_by_area = st.checkbox(
                        "Scale values by area", value=False, disabled=not area_is_available
                    )

                with st.expander("Graph options"):
                    st.markdown("###### Graph options")
                    primary_axis_marker = st.selectbox(
                        "Select primary Y axis markers", [m for m in MARKERS.keys()]
                    )
                    secondary_axis_marker = st.selectbox(
                        "Select secondary Y axis markers",
                        [m for m in MARKERS.keys() if m != primary_axis_marker],
                    )

                    marker_size = int(
                        st.number_input("Marker size", min_value=1, value=8, step=1)
                    )

                    marker_with_border = st.checkbox("Marker with border")

                    options = []
                    if y_axis_mode == "Only primary":
                        options = ["Primary", "None"]
                    elif y_axis_mode == "Only secondary":
                        options = ["Secondary", "None"]
                    else:
                        options = ["Primary", "Secondary", "None"]

                    which_grid = st.radio("Y-axis grid selector", options=options)
                    font_size = st.number_input(
                        "Label font size", min_value=4, value=14, key="font_size_comparison"
                    )
                    height = st.number_input(
                        "Plot height", min_value=10, max_value=2000, value=600, step=10
                    )

            with col1:

                # Create a figure object with the secondary y-axis option enabled
                fig = make_subplots(specs=[[{"secondary_y": True}]])

                # Iterate over each container
                for container in available_containers:

                    offset = 0
                    cellcycling: CellCycling = None

                    # Iterate over each cell_cycling object in the container
                    for cycling_index, (name, cellcycling) in enumerate(container):

                        experiment = status[status.get_index_of(name)]
                        volume = experiment.volume if scale_by_volume else None
                        area = experiment.area if scale_by_area else None

                        if cycling_index != 0:
                            offset += container.max_cycles_numbers[cycling_index - 1] + 1

                        cycle_index = [n + offset for n in cellcycling.numbers]

                        primary_label, primary_axis = get_data_series(
                            primary_axis_name, cellcycling, volume=volume, area=area
                        )
                        secondary_label, secondary_axis = get_data_series(
                            secondary_axis_name, cellcycling, volume=volume, area=area
                        )

                        primary_marker = MARKERS[primary_axis_marker]
                        secondary_marker = MARKERS[secondary_axis_marker]

                        if y_axis_mode != "Only secondary":
                            fig.add_trace(
                                go.Scatter(
                                    x=cycle_index,
                                    y=primary_axis,
                                    name=container.name,
                                    mode="markers",
                                    marker_symbol=primary_marker,
                                    marker=dict(
                                        size=marker_size,
                                        line=dict(width=1, color="DarkSlateGrey")
                                        if marker_with_border
                                        else None,
                                    ),
                                    line=dict(color=container.hex_color),
                                    showlegend=True if cycling_index == 0 else False,
                                ),
                                secondary_y=False,
                            )

                        if y_axis_mode != "Only primary":
                            fig.add_trace(
                                go.Scatter(
                                    x=cycle_index,
                                    y=secondary_axis,
                                    name=container.name,
                                    mode="markers",
                                    marker_symbol=secondary_marker,
                                    marker=dict(
                                        size=marker_size,
                                        line=dict(width=1, color="DarkSlateGrey")
                                        if marker_with_border
                                        else None,
                                    ),
                                    line=dict(color=container.hex_color),
                                    showlegend=True
                                    if y_axis_mode == "Only secondary"
                                    and cycling_index == 0
                                    else False,
                                ),
                                secondary_y=True,
                            )

                if annotation_dict != {}:

                    for text, position in annotation_dict.items():
                        fig.add_annotation(
                            x=position[0],
                            y=position[1],
                            text=text,
                            font_size=annotation_size,
                            font_color=annotation_color,
                            showarrow=False,
                        )

                # Apply proper formatting to the x and y_a axis
                fig.update_xaxes(
                    title_text="Cycle number",
                    showline=True,
                    linecolor="black",
                    gridwidth=1,
                    gridcolor="#DDDDDD",
                )

                fig.update_yaxes(
                    title_text=f"{primary_axis_marker}  {primary_label}",
                    # color=primary_axis_color,
                    secondary_y=False,
                    range=plot_limits["y"],
                    showline=True,
                    linecolor="black",
                    gridwidth=1,
                    gridcolor="#DDDDDD" if which_grid == "Primary" else None,
                )
                fig.update_yaxes(
                    title_text=f"{secondary_axis_marker}  {secondary_label}",
                    # color=secondary_axis_color,
                    secondary_y=True,
                    range=plot_limits["y2"],
                    showline=True,
                    linecolor="black",
                    gridwidth=1,
                    gridcolor="#DDDDDD" if which_grid == "Secondary" else None,
                )

                # Apply proper formatting to legend and plot background
                fig.update_layout(
                    font=dict(size=font_size),
                    legend=dict(
                        orientation="h", yanchor="bottom", y=1.0, xanchor="center", x=0.5
                    ),
                    plot_bgcolor="#FFFFFF",
                )

                # Use the plotly event widget to allow for interactive selection of points
                # on the plot
                selected_points = plotly_events(
                    fig, click_event=False, select_event=True, override_height=height
                )

                # Get the figure data to localize the selected points and to get the plot limits
                figure_data = fig.full_figure_for_development(warn=False)

                if selected_points != [] and selected_points is not None:
                    selected_cycles = ", ".join(
                        [str(point["x"]) for point in selected_points]
                    )
                    st.success(f"Currently selected points: {selected_cycles}")

                # render the cycle hide button (enabled only if there are selected points)
                with chide:
                    hide = st.button(
                        "🚫 Hide cycles",
                        disabled=False
                        if selected_points != [] and selected_points is not None
                        else True,
                    )

                    if hide:
                        trace_list = [obj["name"] for obj in figure_data["data"]]

                        for selected_point in selected_points:
                            container_name = trace_list[selected_point["curveNumber"]]
                            container_id = [obj.name for obj in available_containers].index(
                                container_name
                            )
                            available_containers[container_idx].hide_cycle(
                                selected_point["x"]
                            )

                        st.experimental_rerun()

                # Render a referesh button to manually trigger a rerun
                with crefresh:
                    refresh = st.button("♻ Refresh")

                    if refresh:
                        st.experimental_rerun()

                # Evaluate the current plot limits
                xrange = figure_data.layout.xaxis.range
                yrange = figure_data.layout.yaxis.range

                y2range = (
                    figure_data.layout.yaxis2.range
                    if hasattr(figure_data.layout, "yaxis2")
                    else None
                )

                if (
                    plot_limits["x"] != xrange
                    or plot_limits["y"] != yrange
                    or plot_limits["y2"] != y2range
                ):
                    plot_limits["x"] = xrange
                    plot_limits["y"] = yrange if yrange is not None else plot_limits["y"]
                    plot_limits["y2"] = (
                        y2range if y2range is not None else plot_limits["y2"]
                    )
                    plot_limits["y_annotation_reference"] = (
                        yrange if yrange is not None else y2range
                    )
                    st.experimental_rerun()

            with col2:

                with st.expander("Y axis range"):

                    figure_data = fig.full_figure_for_development(warn=False)

                    if y_axis_mode != "Only secondary":
                        st.markdown("###### primary Y-axis range")
                        y1_range = figure_data.layout.yaxis.range
                        y1_max = st.number_input(
                            "Maximum y-value",
                            key="y_max_prim",
                            value=plot_limits["y"][1],
                        )
                        y1_min = st.number_input(
                            "Minimum y-value",
                            key="y_min_prim",
                            value=plot_limits["y"][0],
                        )

                        if plot_limits["y"][0] != y1_min or plot_limits["y"][1] != y1_max:
                            plot_limits["y"] = [y1_min, y1_max]
                            st.experimental_rerun()

                    if y_axis_mode != "Only primary":
                        st.markdown("###### secondary Y-axis range")
                        y2_range = figure_data.layout.yaxis2.range
                        y2_max = st.number_input(
                            "Maximum y-value",
                            key="y_max_sec",
                            value=plot_limits["y2"][1],
                        )
                        y2_min = st.number_input(
                            "Minimum y-value",
                            key="y_min_sec",
                            value=plot_limits["y2"][0],
                        )

                        if plot_limits["y2"][0] != y2_min or plot_limits["y2"][1] != y2_max:
                            plot_limits["y2"] = [y2_min, y2_max]
                            st.experimental_rerun()

                # Add an export option
                with st.expander("Export"):
                    st.markdown("###### Export")
                    format = st.selectbox(
                        "Select the format of the file", ["png", "jpeg", "svg", "pdf"]
                    )

                    width = st.number_input(
                        "Plot width",
                        min_value=10,
                        max_value=4000,
                        value=1000,
                    )

                    # Redefine layout options to account for user selected width
                    fig.update_layout(
                        height=height,
                        width=width,
                        font=dict(size=font_size),
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
                        data=fig.to_image(format=format),
                        file_name=f"cycle_plot.{format}",
                    )

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
