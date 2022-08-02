import streamlit as st
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from core.gui_core import Experiment, ProgramStatus, ExperimentSelector, RGB_to_HEX

enable = True
if "ProgramStatus" not in st.session_state:
    enable = False
else:
    status: ProgramStatus = st.session_state["ProgramStatus"]
    if len(status) == 0:
        enable = False


if "CyclePlotSelection" not in st.session_state:
    st.session_state["CyclePlotSelection"] = ExperimentSelector()


st.title("Cycles plotter")

st.write(
    "In this page you can select the experiments to analyze and plot a selected subset of charge/discharge cycles"
)

if enable:

    status: ProgramStatus = st.session_state["ProgramStatus"]

    with st.container():

        col1, col2 = st.columns([4, 1])
        selection = None

        with col1:
            available_experiments = [
                obj.name
                for obj in status
                if obj.name not in st.session_state["CyclePlotSelection"].names
            ]
            selection = st.selectbox("Select the desired experiment", available_experiments)

        with col2:
            st.write("")
            st.write("")
            add = st.button("➕ Add")
            if add and selection is not None:
                st.session_state["CyclePlotSelection"].set(selection)
                st.experimental_rerun()

    st.markdown("---")

    if st.session_state["CyclePlotSelection"].is_empty == False:

        with st.expander("Visualization options", expanded=True):

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("###### Loaded experiments selector")
                current_view = st.radio(
                    "Select the experiment to edit",
                    st.session_state["CyclePlotSelection"].names,
                )

                st.markdown("---")
                st.markdown("###### View options")
                remove_current = st.button("➖ Remove from view")
                if remove_current:
                    index = st.session_state["CyclePlotSelection"].remove(current_view)
                    st.experimental_rerun()

            with col2:
                st.markdown("###### Cycle selector mode")
                view_mode = st.radio(
                    "Select the mode of operation", ["Constant interval", "Manual"]
                )

                st.markdown("---")

                if view_mode == "Constant interval":

                    st.markdown("###### Constant interval cycle selector")

                    id = status.get_index_of(current_view)
                    max_cycle = len(status[id].manager.get_cycles()) - 1

                    start = st.number_input(
                        "Start", min_value=0, max_value=max_cycle - 1, step=1
                    )
                    stop = st.number_input(
                        "Stop (included)",
                        min_value=start + 1,
                        max_value=max_cycle,
                        value=max_cycle,
                        step=1,
                    )
                    stride = st.number_input(
                        "Stride", min_value=1, max_value=max_cycle, step=1
                    )

                    apply = st.button("✅ Apply")
                    if apply:
                        view_settings: ExperimentSelector = st.session_state[
                            "CyclePlotSelection"
                        ]
                        view_settings.set(
                            current_view, np.arange(start, stop + 1, step=stride)
                        )

                else:

                    st.markdown("###### Manual cycle selector")

                    view_settings = st.session_state["CyclePlotSelection"]
                    id = status.get_index_of(current_view)
                    cycles = status[id].manager.get_cycles()
                    new_cycle_list = []
                    for cycle in cycles:
                        selection = st.checkbox(
                            f"Cycle n° {cycle.number}",
                            value=(
                                True
                                if cycle.number in view_settings[current_view]
                                else False
                            ),
                        )
                        if selection:
                            new_cycle_list.append(cycle.number)
                    view_settings[current_view] = new_cycle_list

        st.markdown("### Experiment plots")

    view_settings: ExperimentSelector = st.session_state["CyclePlotSelection"]
    st.write(view_settings)

    if not view_settings.is_empty:

        fig = make_subplots(cols=1, rows=len(view_settings))

        for index, name in enumerate(view_settings.names):

            id = status.get_index_of(name)
            experiment: Experiment = status[id]
            cycles = experiment.manager.get_cycles()

            num_traces = len(view_settings[name])
            for trace_id, cycle_id in enumerate(view_settings[name]):

                shade = RGB_to_HEX(*experiment.color.get_shade(trace_id, num_traces))

                cycle = cycles[cycle_id]

                if cycle.charge is not None:
                    fig.add_trace(
                        go.Scatter(
                            x=cycle.charge.time,
                            y=cycle.charge.voltage,
                            line=dict(color=shade, dash="dot"),
                            name=f"charge cycle {cycle_id}",
                        ),
                        row=index + 1,
                        col=1,
                    )

                if cycle.discharge is not None:
                    fig.add_trace(
                        go.Scatter(
                            x=cycle.discharge.time,
                            y=cycle.discharge.voltage,
                            line=dict(color=shade),
                            name=f"discharge cycle {cycle_id}",
                        ),
                        row=index + 1,
                        col=1,
                    )

        st.plotly_chart(fig, use_container_width=True)


else:
    st.info(
        """**No experiment has been loaded yet** \n\n Please go to the file manager 
    page and procede to upload and properly edit the required experiment files before
    accessing this page."""
    )
