from typing import List
import streamlit as st

from core.gui_core import ExperimentSelector, SingleCycleSeries
from core.experiment import ExperimentContainer

def update_experiment_name(old: str, new: str) -> None:

    if "Page2_CyclePlotSelection" in st.session_state:
        exp_selector: ExperimentSelector = st.session_state["Page2_CyclePlotSelection"]
        for name in list(exp_selector.view.keys()):
            if name == old:
                exp_selector.view[new] = exp_selector.view.pop(old)

    if "Page2_ComparisonPlot" in st.session_state:
        selected_series: List[SingleCycleSeries] = st.session_state["Page2_ComparisonPlot"]
        for series in selected_series:
            if series.experiment_name == old:
                series.experiment_name = new


def remove_experiment_entries(old: str) -> None:

    if "Page2_CyclePlotSelection" in st.session_state:
        exp_selector: ExperimentSelector = st.session_state["Page2_CyclePlotSelection"]
        for name in list(exp_selector.view.keys()):
            if name == old:
                del exp_selector.view[old]

    if "Page2_ComparisonPlot" in st.session_state:
        selected_series: List[SingleCycleSeries] = st.session_state["Page2_ComparisonPlot"]
        for series in selected_series:
            if series.experiment_name == old:
                del selected_series[selected_series.index(series)]
