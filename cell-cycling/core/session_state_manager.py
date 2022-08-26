from io import BytesIO
from copy import deepcopy

import pickle
import streamlit as st

def save_session_state():
    bytestream = BytesIO()

    session_state_buffer = deepcopy(dict(st.session_state))
    del session_state_buffer["Version"]
    del session_state_buffer["Logger"]
    del session_state_buffer["Token"]

    pickle.dump(session_state_buffer, bytestream, protocol=pickle.HIGHEST_PROTOCOL)
    bytestream.seek(0)

    return bytestream


def load_session_state(file: BytesIO):
    loaded_session_state: dict = pickle.load(file)
    for key, value in loaded_session_state.items():
        st.session_state[key] = value