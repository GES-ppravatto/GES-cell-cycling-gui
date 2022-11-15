from io import BytesIO
from copy import deepcopy

import pickle
from typing import List
import streamlit as st


def generate_session_state_model(keys: List[str]):
    buffer = {}
    for key in keys:
        if key in st.session_state:
            buffer[key] = deepcopy(st.session_state[key])
    return buffer


def save_session_state():

    bytestream = BytesIO()

    keys = [
        "Version",
        "ProgramStatus",
        "UploadActionRadio",
        "UploadConfirmation",
        "SelectedExperimentName",
        "Page2_CyclePlotSelection",
        "Page2_ManualSelectorBuffer",
        "Page2_ComparisonPlot",
        "Page2_stacked_settings",
        "Page2_comparison_settings",
        "ExperimentContainers",
        "Cellcycling_plots_settings",
    ]

    buffer = generate_session_state_model(keys)

    pickle.dump(buffer, bytestream, protocol=pickle.HIGHEST_PROTOCOL)
    bytestream.seek(0)

    return bytestream


def load_session_state(file: BytesIO):
    loaded_session_state: dict = pickle.load(file)
    for key, value in loaded_session_state.items():
        st.session_state[key] = value
