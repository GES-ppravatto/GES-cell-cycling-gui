from io import BytesIO
import pickle
import streamlit as st

def save_session_state():
    bytestream = BytesIO()
    pickle.dump(dict(st.session_state), bytestream, protocol=pickle.HIGHEST_PROTOCOL)
    bytestream.seek(0)
    return bytestream


def load_session_state(file: BytesIO):
    st.session_state = pickle.load(file)