import datetime
import os
import pathlib
import pandas as pd
from sqlalchemy import text, create_engine, inspect
import geopandas as gpd
import streamlit as st
import leafmap.colormaps as cm

# String credential
database_credentials = r'/workspaces/streamlit-geospatial/Database_credentials.xlsx'

@st.cache_data
def connect_database(loc):
    # Reading credential file
    db_cred = pd.read_excel(loc)

    # Creating string to connect to the database and suppress the connection string for database integrity
    create_engine_str = db_cred[db_cred['credential_object']=='create_engine_string']['credential'].item()

    # Connecting to the database# Connecting to database
    engine = create_engine(create_engine_str)
    inspector = inspect(engine)

# Connecting to the database
connect_database(database_credentials)

# Obtaining the geodata

def result_query(query, display=False):
    # Running query
    result = engine.connect().execute(query)

    # Conditional print statement
    if display:
        for row in result:
            print(row)
    return result

