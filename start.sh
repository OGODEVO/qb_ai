#!/bin/bash

# Start the API server in the background
python3 api.py &

# Start the Streamlit app in the foreground
/home/codespace/.local/lib/python3.12/site-packages/bin/streamlit run app.py
