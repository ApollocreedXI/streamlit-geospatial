import os
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from shapely.wkb import loads
import json
import streamlit as st
import altair as alt
from datetime import datetime as dt


# Initialize connection.
conn = st.connection("postgresql", type="sql")

# Creating geolevel object
geo_level = 'basin'

### Extracting basic geo-level information

# Extracting geo_level information
basin_geometry_data_query = (f'''
SELECT * FROM climate_resilience.proj_major_basin''')
# Executing query
basin_geometry_df = conn.query(basin_geometry_data_query, ttl=None) # Store catched result
# Converting the geometry column to WKT
basin_geometry_df['geometry'] = basin_geometry_df['basin_geometry_proj'].apply(loads)
# Converting to GeoDataFrame
basin_geometry_gdf = gpd.GeoDataFrame(basin_geometry_df, geometry='geometry')
# st.write(basin_geometry_df)
# Extracting mappings for basin name and basin_id
basin_mappings = dict(zip(basin_geometry_gdf['basin_name'], basin_geometry_gdf['basin_id']))



### Creating a dropdown menu

# Creating a iterable to pass to the selectbox
basin_names = basin_geometry_gdf['basin_name'].to_list()
# Creating selectbox
basin_selection = st.selectbox('Select a Basin', basin_names)
basin_selection_id = basin_mappings[basin_selection]

# st.write(basin_selection_id)

### Creating queries 

# Extracting land aridity stats
aridity_stats_query = (f'''
SELECT * FROM climate_resilience.aridity_stats_{geo_level} WHERE basin_id={basin_selection_id};''')
# Executing query 
aridity_stats = conn.query(aridity_stats_query, ttl=None) # Store catched result
# st.write(aridity_stats)

# Extracting population stats
population_stats_query = (f'''
SELECT * FROM climate_resilience.mv_{geo_level}_population_statistics WHERE basin_id={basin_selection_id};''')
# Executing query 
population_stats = conn.query(population_stats_query, ttl=None) # Store catched result
# st.write(population_stats)

# Water_distribution points
water_distribution_query = (f'''
SELECT * FROM climate_resilience.water_distribution''')
# Executing query 
water_distribution = conn.query(water_distribution_query, ttl=None) # Store catched result
# st.write(water_distribution)

# Extracting drought severity data
drought_severity_query = (f'''
SELECT * FROM climate_resilience.drought_severity_stats_{geo_level} 
WHERE basin_id={basin_selection_id}''')
# Executing query 
drought_severity = conn.query(drought_severity_query, ttl=None) # Store catched result
# st.write(drought_severity)

# Extracting precipitation data
precipitation_stats_query = (f'''
SELECT * FROM climate_resilience.monthly_rainfall_stats_{geo_level} 
WHERE basin_id={basin_selection_id}''')
# Executing query 
precipitation_stats = conn.query(precipitation_stats_query, ttl=None) # Store catched result
# st.write(precipitation_stats.head())

# Extracting data max temperature 
daily_max_temp_query = (f'''
SELECT * FROM climate_resilience.monthly_max_temp_stats_{geo_level} WHERE basin_id={basin_selection_id}''')
max_temp = conn.query(daily_max_temp_query)
# st.write(max_temp.head())

### Creating altair plots

# Creating long format of the different percentage of aridity land types
aridity_long = pd.melt(aridity_stats, id_vars=["stat_id"], value_vars=["pct_hyper_arid", "pct_arid", "pct_semi_arid", "pct_dry_sub_humid", "pct_humid"], var_name="aridity_type", value_name="percentage")

# Cleaning up column names
map_names = {'pct_hyper_arid': 'Hyper Arid', 'pct_arid': 'Arid', 'pct_semi_arid': 'Semi Arid', 'pct_dry_sub_humid': 'Dry Sub Humid', 'pct_humid': 'Humid'}
aridity_long['aridity_type'] = aridity_long['aridity_type'].map(map_names)

# providing basic text of the population stats
st.write("## Population Statistics")

# Adding text of the total population with comma formating
st.write("#### Total Population is ", f"{population_stats['total_pop'].item():,}, with a population density of ", f"{population_stats['density'].item():,.2f} people per sq km")

# Adding text for the total area with comma formatting
st.write(f"## Total area of the {basin_selection} region")
# Adding `area_sqkm` text
st.write("#### Area (sq km): ", f"{population_stats['area_sqkm'].item():,.2f}")


### Creating static chart

# Creating bar chart of land aridity stats
aridity_chart = alt.Chart(aridity_long, title='Land Aridity Distribution').mark_bar().encode(
    x=alt.X('aridity_type:N', sort='-y'),
    y=alt.Y('percentage:Q', title='Percentage of Land Area'),
    color='aridity_type:N'

)
st.altair_chart(aridity_chart)


### Creating plots of the monthly enviromental dataset (monthly precipitation, monthly drought, monthly max temperature)
# Creating a tabbed layout for the monthly environmental data
st.write("## Monthly Environmental Data")

# Converting to python datetime format
drought_severity['measure_date'] = pd.to_datetime(drought_severity['measure_date']).dt.to_pydatetime()
precipitation_stats['year_month'] = pd.to_datetime(precipitation_stats['year_month']).dt.to_pydatetime()
max_temp['year_month'] = pd.to_datetime(max_temp['year_month']).dt.to_pydatetime()



tab1, tab2, tab3 = st.tabs(["Monthly Precipitation", "Monthly Max Temperature", "Monthly Drought Severity"])
with tab1:
    # Adding time slider for the monthly environmental data
    min_date = precipitation_stats['year_month'].min()
    max_date = precipitation_stats['year_month'].max()
    month_slider_precipitation = st.slider("Select a Month", min_value=min_date, max_value=max_date, value=(min_date,max_date), key="month_slider_precipitation") 
    # Filtering the precipitation data based on the selected month
    filtered_precipitation_stats = precipitation_stats[(precipitation_stats['year_month'] >= month_slider_precipitation[0]) & (precipitation_stats['year_month'] <= month_slider_precipitation[1])]
    
    # Creating monthly precipitation chart
    preciptation_chart = alt.Chart(filtered_precipitation_stats, title='Monthly Precipitation').mark_line().encode(
    x=alt.X('year_month:T', title='Month',
            axis=alt.Axis(format='%b %Y', title='Date')),
    y=alt.Y('monthly_average:Q', title='Average Precip (mm)'),
    tooltip=['year_month', 'monthly_average', 'monthly_min', 'monthly_max']
)
    st.altair_chart(preciptation_chart)
with tab2:
    # Creating max and min objects
    min_date = max_temp['year_month'].min()
    max_date = max_temp['year_month'].max()
    
    # Creating slider
    month_slider_max_temp= st.slider("Select a Month", min_value=min_date, max_value=max_date, value=(min_date,max_date), key="month_slider_max_temp")
    # Filtering the max_temp based on the selected month
    filtered_max_temp = max_temp[(max_temp['year_month'] >= month_slider_max_temp[0]) & (max_temp['year_month'] <= month_slider_max_temp[1])]

    # Creating daily max temperature chart
    daily_max_temp_chart = alt.Chart(filtered_max_temp, title='Monthly Max Temperature').mark_line().encode(
    x=alt.X('year_month:T', title='Month', axis=alt.Axis(format='%b %Y', title='Date')),
    y=alt.Y('monthly_average:Q', title='Average Max Temp (°C)'),
    tooltip=['year_month', 'monthly_average', 'monthly_max', 'monthly_min']
    )

    # Plotting
    st.altair_chart(daily_max_temp_chart)
with tab3:

    # Creating min and max objects
    min_date = drought_severity['measure_date'].min()
    max_date = drought_severity['measure_date'].max()
    # Creating slider
    month_slider_drought= st.slider("Select a Month", min_value=min_date, max_value=max_date, value=(min_date,max_date), key="month_slider_drought")
    
    # Creating a long format of the drought severity data
    drought_severity_long = pd.melt(drought_severity, id_vars=["measure_date"], value_vars=["pct_moderate_drought", "pct_severe_drought", "pct_extreme_drought"], var_name="drought_severity_type", value_name="percentage")

    # Remapping the drought types to more readable format
    drought_severity_long['drought_severity_type'] = drought_severity_long['drought_severity_type'].map({'pct_moderate_drought': 'Moderate Drought', 'pct_severe_drought': 'Severe Drought', 'pct_extreme_drought': 'Extreme Drought'})

    # Filtering the drought_severity based on the selected month
    filtered_drought_severity = drought_severity_long[(drought_severity_long['measure_date'] >= month_slider_drought[0]) & (drought_severity_long['measure_date'] <= month_slider_drought[1])]

    # Creating monthly area line charrt of drought severity 
    drought_severity_chart = alt.Chart(filtered_drought_severity, title='Monthly Drought Severity').mark_area().encode(
    x=alt.X('measure_date:T', title='Month'),
    y=alt.Y('percentage:Q', title='Percentage of Drought Severity Type'),
    color='drought_severity_type:N',
    tooltip=['measure_date', 'drought_severity_type', 'percentage']
)
    # Plotting
    st.altair_chart(drought_severity_chart)








