import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Tuple
from echemsuite.cellcycling.read_input import Cycle, HalfCycle


def halfcycle_property_from_key(halfcycle: HalfCycle, key: str) -> Tuple[pd.Series, str]:
    """
    Extract from the streamlit session_state cache the cycle property and label
    to be used in the plot.

    Parameters
    ----------
    halfcycle : HalfCycle
        halfcycle to be plotted.
    key : str
        keyword of the streamlit session_state cache dictionary encoding the
        axis.

    Returns
    -------
    series : pd.Series
        data series containing the data to be plotted.
    label : str
        name of the data series.
    """
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
    """
    Generate a matplotlib plot of a given halfcycle automatically searching 
    the streamlit session_state cache for the user-selected settings

    Parameters
    ----------
    halfcycle : HalfCycle
        halfcycle to be plotted.
    dpi : int, optional
        resolution of the figure object

    Returns
    -------
    fig : Figure
        matplotlib.pyplot figure object.

    """
    # Define the figure object and a primary set of axis (axa)
    fig, axa = plt.subplots(figsize=(10, 5), dpi=dpi)

    # Extract series and label for the x and y_a axis (axa)
    x_axis, x_label = halfcycle_property_from_key(halfcycle, "inspector_x_scale")
    ya_axis, ya_label = halfcycle_property_from_key(halfcycle, "inspector_ya_scale")

    # Generate the plot and set the labels
    axa.plot(x_axis, ya_axis, c="red", label=ya_label)
    axa.set_xlabel(x_label)
    axa.set_ylabel(ya_label, c="red")

    # Set the plot grids
    axa.grid(which="major", c="#DDDDDD")
    axa.grid(which="minor", c="#EEEEEE")

    # Check if a secondary value is selected for plot
    if st.session_state["inspector_yb_scale"] != "None":
        axb = axa.twinx()  # Generate y_b as the x-twin of y_a

        # Extract series and label for the y_b axis (axb)
        yb_axis, yb_label = halfcycle_property_from_key(halfcycle, "inspector_yb_scale")

        # Plot the data on the secondary axis
        axb.plot(x_axis, yb_axis, c="green", label=yb_label)
        axb.set_ylabel(yb_label, c="green")

    plt.tight_layout()
    return fig


def plot_halfcycle_plotly(halfcycle: HalfCycle):
    """
    Generate a plotly plot of a given halfcycle automatically searching 
    the streamlit session_state cache for the user-selected settings

    Parameters
    ----------
    halfcycle : HalfCycle
        halfcycle to be plotted.

    Returns
    -------
    fig : Figure
        plotly figure object.
    """

    # Create a figure object with the secondary y-axis option enabled
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Extract series and label for the x and y_a axis
    x_axis, x_label = halfcycle_property_from_key(halfcycle, "inspector_x_scale")
    ya_axis, ya_label = halfcycle_property_from_key(halfcycle, "inspector_ya_scale")

    # Plot the y_a axis data on the primary axis
    fig.add_trace(go.Scatter(x=x_axis, y=ya_axis, name=ya_label), secondary_y=False)

    # Apply proper formatting to the x and y_a axis
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

    # Check if a secondary value is selected for plot
    if st.session_state["inspector_yb_scale"] != "None":

        # Extract series and label for the y_b axis (axb)
        yb_axis, yb_label = halfcycle_property_from_key(halfcycle, "inspector_yb_scale")

        # Plot the y_b axis data on the secondary axis
        fig.add_trace(go.Scatter(x=x_axis, y=yb_axis, name=yb_label), secondary_y=True)

        # Apply proper formatting to the y_b axis
        fig.update_yaxes(
            title_text=yb_label,
            secondary_y=True,
            showline=True,
            linecolor="black",
            gridwidth=0,
            gridcolor=None,
        )

    # Apply proper formatting to legend and plot background
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="center", x=0.5),
        plot_bgcolor="#FFFFFF",
    )

    return fig


### START OF THE APP PAGE BODY

# Define local variables for the session_state cache (only those non affecting the global workflow)
if "inspector_x_scale" not in st.session_state:
    st.session_state["inspector_x_scale"] = "Time"
    st.session_state["inspector_ya_scale"] = "Voltage"
    st.session_state["inspector_yb_scale"] = "Current"

st.set_page_config(layout="wide")

st.title("Cycle inspector")

# Check if the cellcycles entry has been set else plot an info message
if st.session_state["cellcycles"] != None:

    # Prompt the user to select a cycle to inspect
    cycle: Cycle = st.selectbox("Select the cycle to inspect", st.session_state["cycles"])

    # Check if the selected cycle is hidden ad inform the user with a warning box
    if cycle._hidden:
        st.warning("WARNING: The selected cycle is marked as hidden")

    # Allow the user to select two parameters to plot on two independent axis (y_a and y_b)
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

    # Check if the charge halfcycle is available
    if cycle.charge != None:
        # Create an expander for the charge halfcycle plot
        with st.expander("Charge cycle data", expanded=True):

            st.markdown("### Charge")
            # fig = plot_halfcycle_mpl(cycle.charge)
            # st.pyplot(fig)

            fig = plot_halfcycle_plotly(cycle.charge)
            st.plotly_chart(fig, use_container_width=True)

    # Check if the discharge halfcycle is available
    if cycle.discharge != None:
        # Create an expander for the discharge halfcycle plot
        with st.expander("Discharge cycle data", expanded=True):

            st.markdown("## Discharge")
            # fig = plot_halfcycle_mpl(cycle.discharge)
            # st.pyplot(fig)

            fig = plot_halfcycle_plotly(cycle.discharge)
            st.plotly_chart(fig, use_container_width=True)

else:
    # Print the info box redirecting the user to the upload page
    st.info(
        "HINT: In order to use this page you must first complete the upload and parsing of the files"
    )
