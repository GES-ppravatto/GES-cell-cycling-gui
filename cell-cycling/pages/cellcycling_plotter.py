from typing import Dict, List, Tuple, Union
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_plotly_events import plotly_events

from core.gui_core import Experiment, ProgramStatus, get_plotly_color

from echemsuite.cellcycling.cycles import CellCycling


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
            cumulative_sum.append(
                number if i == 0 else cumulative_sum[-1] + number
            )
        
        experiment_id, cycle_id = None, None
        for i, threshold in enumerate(cumulative_sum):
            if cumulative_id <= threshold:
                experiment_id = i
                if i==0:
                    cycle_id = cumulative_id
                else:
                    cycle_id = cumulative_id - cumulative_sum[i-1]
                break

        self._experiments[experiment_id].hide_cycle(cycle_id)
                    

MARKERS = {
    "●": "circle",
    "■": "square",
    "▲": "triangle-up",
    "▼": "triangle-down",
    "+": "cross",
    "X": "x",
}

Y_OPTIONS = [
    "Capacity retention",
    "Columbic efficiency",
    "Energy efficiency",
    "Voltaic Efficiency",
]


def get_data_series(option: str, cellcycling: CellCycling) -> List[float]:

    if option not in Y_OPTIONS:
        raise TypeError

    if option == "Capacity retention":
        return cellcycling.capacity_retention
    elif option == "Columbic efficiency":
        return cellcycling.coulomb_efficiencies
    elif option == "Energy efficiency":
        return cellcycling.energy_efficiencies
    elif option == "Voltaic Efficiency":
        return cellcycling.voltage_efficiencies
    else:
        raise RuntimeError


if "ExperimentContainers" not in st.session_state:
    st.session_state["ExperimentContainers"] = []
    st.session_state["CellCycling_plot_limits"] = {"x": [None, None], "y": [None, None]}
    st.session_state["PlotAnnotations"] = {}


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

# Set the title of the page and print some generic instruction
st.title("Cell-cycling plotter")

st.write(
    """In this page you can analyze and compare cell-cycling experiments carried out in different
    conditions comparing their capacity retention and efficiencies."""
)

if enable:

    available_containers: List[ExperimentContainer] = st.session_state[
        "ExperimentContainers"
    ]
    plot_limits: Dict[str, List[Union[None, float]]] = st.session_state[
        "CellCycling_plot_limits"
    ]
    annotation_dict: dict = st.session_state["PlotAnnotations"]

    container_tab, plot_tab = st.tabs(["Container editor", "Container plotter"])

    with container_tab:

        with st.expander("Create new experiment container", expanded=True):

            st.markdown("#### Create a new experiment container")
            st.write(
                """In this tab you can create new experiments containers to hold different
                cell-cycling experiments and edit the ones eventually available"""
            )

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

    with plot_tab:

        if available_containers != []:

            st.markdown("#### Cell-cycling plotter")
            st.write(
                """In this tab you can create a cell cycling plot and interactively selecting
                its appearence"""
            )

            if plot_limits["x"][0] != None:

                with st.expander("Annotation editor", expanded=False):
                    st.markdown("###### Global annotation settings")

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
                            min_value=float(plot_limits["y"][0]),
                            max_value=float(plot_limits["y"][1]),
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

            chide, cunhide, crefresh = st.columns(3)

            with cunhide:
                unhide = st.button("👁 Unhide all")

                if unhide:
                    for container in available_containers:
                        for experiment in container._experiments:
                            experiment.unhide_all_cycles()

            col1, col2 = st.columns([4, 1])

            with col2:

                st.markdown("###### Series selector")

                primary_axis_name = st.selectbox(
                    "Select the dataset for the primary Y axis", Y_OPTIONS
                )
                secondary_axis_name = st.selectbox(
                    "Select the dataset for the secondary Y axis",
                    [option for option in Y_OPTIONS if option != primary_axis_name],
                )

                y_axis_mode = st.radio(
                    "Select which Y axis series to show",
                    ["Both", "Only primary", "Only secondary"],
                )

                st.markdown("###### Graph options")
                primary_axis_marker = st.selectbox(
                    "Select primary Y axis markers", [m for m in MARKERS.keys()]
                )
                secondary_axis_marker = st.selectbox(
                    "Select secondary Y axis markers",
                    [m for m in MARKERS.keys() if m != primary_axis_marker],
                )
                which_grid = st.radio(
                    "Y-axis grid selector", options=["Primary", "Secondary", "None"]
                )
                font_size = st.number_input(
                    "Label font size", min_value=4, value=14, key="font_size_comparison"
                )
                height = st.number_input(
                    "Plot height", min_value=10, max_value=2000, value=600, step=10
                )


            with col1:
                
                # Create a figure object with the secondary y-axis option enabled
                fig = make_subplots(specs=[[{"secondary_y": True}]])

                for container in available_containers:

                    cellcycling: CellCycling = None
                    for cycling_index, (name, cellcycling) in enumerate(container):

                        offset = (
                            0
                            if cycling_index == 0
                            else container.max_cycles_numbers[cycling_index - 1] + 1
                        )

                        cycle_index = [n + offset for n in cellcycling.numbers]

                        primary_axis = get_data_series(primary_axis_name, cellcycling)
                        secondary_axis = get_data_series(secondary_axis_name, cellcycling)

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
                                    line=dict(color=container.hex_color),
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
                                    line=dict(color=container.hex_color),
                                    showlegend=False,
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
                    title_text=primary_axis_name,
                    # color=primary_axis_color,
                    secondary_y=False,
                    showline=True,
                    linecolor="black",
                    gridwidth=1,
                    gridcolor="#DDDDDD" if which_grid == "Primary" else None,
                )
                fig.update_yaxes(
                    title_text=secondary_axis_name,
                    # color=secondary_axis_color,
                    secondary_y=True,
                    showline=True,
                    linecolor="black",
                    gridwidth=1,
                    gridcolor="#DDDDDD" if which_grid == "Secondary" else None,
                )

                # Apply proper formatting to legend and plot background
                fig.update_layout(
                    legend=dict(
                        orientation="h", yanchor="bottom", y=1.0, xanchor="center", x=0.5
                    ),
                    plot_bgcolor="#FFFFFF",
                )

                selected_points = plotly_events(fig, click_event=False, select_event=True, override_height=height)

                figure_data = fig.full_figure_for_development(warn=False)

                with chide:
                    hide = st.button("🚫 Hide cycles", disabled= False if selected_points != [] and selected_points is not None else True)

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
                
                with crefresh:
                    refresh = st.button("♻ Refresh")

                    if refresh:
                        st.experimental_rerun()

                # st.plotly_chart(fig, use_container_width=True)

                xrange = figure_data.layout.xaxis.range
                yrange = figure_data.layout.yaxis.range

                if yrange is None:
                    yrange = figure_data.layout.yaxis2.range

                if plot_limits["x"] != xrange or plot_limits["y"] != yrange:
                    plot_limits["x"] = xrange
                    plot_limits["y"] = yrange
                    st.experimental_rerun()


            with col2:

                st.markdown("###### Export")
                format = st.selectbox(
                    "Select the format of the file", ["png", "jpeg", "svg", "pdf"]
                )

                width = st.number_input(
                    "Plot width",
                    min_value=10,
                    max_value=4000,
                    value= 1000,
                )
                
                fig.update_layout(
                    height=height,
                    width=width,
                    font=dict(size=font_size),
                    legend=dict(
                        orientation="h", yanchor="bottom", y=1.0, xanchor="center", x=0.5
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
