import streamlit as st

st.write(f"Streamlit version: {st.__version__}") # Display current version in the app
st.markdown("This is a test markdown with no key.")
st.markdown("This is a test markdown **with a key**.", key="test_key")
st.write("If you see this, and the version is >= 1.10.0, but the error still happened on the line above, something is very odd.")