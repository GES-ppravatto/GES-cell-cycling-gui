import streamlit as st
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from echemsuite.cellcycling.read_input import Cycle, HalfCycle


def halfcycle_property_from_key(halfcycle: HalfCycle, key: str):
    series, label = None, None
    if st.session_state[key] == "Time":
        series = halfcycle.time
        label = "Time (s)"
    elif st.session_state[key] == "Charge":
        series = halfcycle._Q
        label = "Charge (mAh)"
    elif st.session_state[key] == "Voltage":
        series = halfcycle.voltage
        label = "Voltage (V)"
    elif st.session_state[key] == "Current":
        series = halfcycle.current
        label = "Current (A)"
    return series, label


def plot_halfcycle_mpl(halfcycle: HalfCycle, dpi: int = 600):

    fig, axa = plt.subplots(figsize=(10, 5), dpi=dpi)

    x_axis, x_label = halfcycle_property_from_key(halfcycle, "inspector_x_scale")
    ya_axis, ya_label = halfcycle_property_from_key(halfcycle, "inspector_ya_scale")

    axa.plot(x_axis, ya_axis, c="red", label=ya_label)
    axa.set_xlabel(x_label)
    axa.set_ylabel(ya_label, c="red")
    axa.grid(which="major", c="#DDDDDD")
    axa.grid(which="minor", c="#EEEEEE")

    if st.session_state["inspector_yb_scale"] != "None":
        yb_axis, yb_label = halfcycle_property_from_key(halfcycle, "inspector_yb_scale")

        axb = axa.twinx()
        axb.plot(x_axis, yb_axis, c="green", label=yb_label)
        axb.set_ylabel(yb_label, c="green")

    plt.tight_layout()

    return fig


def plot_halfcycle_plotly(halfcycle: HalfCycle, dpi: int = 600):

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    x_axis, x_label = halfcycle_property_from_key(halfcycle, "inspector_x_scale")
    ya_axis, ya_label = halfcycle_property_from_key(halfcycle, "inspector_ya_scale")

    fig.add_trace(go.Scatter(x=x_axis, y=ya_axis, name=ya_label), secondary_y=False)

    fig.update_xaxes(
        title_text=x_label,
        showline=True,
        linecolor="black",
        gridwidth=1,
        gridcolor="#DDDDDD",
    )
    fig.update_yaxes(
        title_text=ya_label,
        secondary_y=False,
        showline=True,
        linecolor="black",
        gridwidth=1,
        gridcolor="#DDDDDD",
    )

    if st.session_state["inspector_yb_scale"] != "None":

        yb_axis, yb_label = halfcycle_property_from_key(halfcycle, "inspector_yb_scale")

        fig.add_trace(go.Scatter(x=x_axis, y=yb_axis, name=yb_label), secondary_y=True)
        fig.update_yaxes(
            title_text=yb_label,
            secondary_y=True,
            showline=True,
            linecolor="black",
            gridwidth=0,
            gridcolor=None,
        )

    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="center", x=0.5),
        plot_bgcolor="#FFFFFF",
    )

    return fig


if "inspector_x_scale" not in st.session_state:
    st.session_state["inspector_x_scale"] = "Time"
    st.session_state["inspector_ya_scale"] = "Voltage"
    st.session_state["inspector_yb_scale"] = "Current"

st.title("Cycle inspector")

if st.session_state["cellcycles"] != None:
    cycle: Cycle = st.selectbox("Select the cycle to inspect", st.session_state["cycles"])
    if cycle._hidden:
        st.warning("WARNING: The selected cycle is marked as hidden")

    cx, cya, cyb = st.columns(3)
    with cx:
        x_axis_options = ["Time", "Charge", "Voltage", "Current"]
        st.session_state["inspector_x_scale"] = st.radio(
            "Select the x-axis series",
            x_axis_options,
            index=x_axis_options.index(st.session_state["inspector_x_scale"]),
        )

    with cya:
        ya_axis_options = ["Time", "Charge", "Voltage", "Current"]
        st.session_state["inspector_ya_scale"] = st.radio(
            "Select the main y-axis series",
            ya_axis_options,
            index=ya_axis_options.index(st.session_state["inspector_ya_scale"]),
        )

    with cyb:
        yb_axis_options = ["Time", "Charge", "Voltage", "Current", "None"]
        st.session_state["inspector_yb_scale"] = st.radio(
            "Select the secondary y-axis series",
            yb_axis_options,
            index=yb_axis_options.index(st.session_state["inspector_yb_scale"]),
        )

    if cycle.charge != None:
        with st.expander("Charge cycle data", expanded=True):

            st.markdown("### Charge")
            # fig = plot_halfcycle_mpl(cycle.charge)
            # st.pyplot(fig)

            fig = plot_halfcycle_plotly(cycle.charge)
            st.plotly_chart(fig, use_container_width=True)

    if cycle.discharge != None:
        with st.expander("Discharge cycle data", expanded=True):

            st.markdown("## Discharge")
            # fig = plot_halfcycle_mpl(cycle.discharge)
            # st.pyplot(fig)

            fig = plot_halfcycle_plotly(cycle.discharge)
            st.plotly_chart(fig, use_container_width=True)


else:
    st.info(
        "HINT: In order to use this page you must first complete the upload and parsing of the files"
    )
