import streamlit as st

def set_production_page_style():

    hide_st_style = """
                <style>
                #MainMenu {visibility: hidden;}
                footer {visibility: hidden;}
                header {visibility: hidden;}
                </style>
                """

    st.markdown(hide_st_style, unsafe_allow_html=True)


def force_update_once():
    if "forced update executed" not in st.session_state:
        st.session_state["forced update executed"] = False
        st.experimental_rerun()
    if not st.session_state["forced update executed"]:
        st.session_state["forced update executed"] = True
        return
    st.session_state["forced update executed"] = False
    st.experimental_rerun()