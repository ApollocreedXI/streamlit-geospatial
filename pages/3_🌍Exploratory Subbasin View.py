import os
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from shapely.wkb import loads
import json
import streamlit as st
import altair as alt


# Initialize connection.
conn = st.connection("postgresql", type="sql")

# Creating geolevel object
geo_level = 'sub_basin'

### Extracting basic geo-level information

# Extracting geo_level information
sub_basin_geometry_data_query = (f'''
SELECT * FROM climate_resilience.proj_sub_basin''')
# Executing query
sub_basin_geometry_df = conn.query(sub_basin_geometry_data_query, ttl=None) # Store catched result
# Converting the geometry column to WKT
sub_basin_geometry_df['geometry'] = sub_basin_geometry_df['sub_basin_geometry_proj'].apply(loads)
# Converting to GeoDataFrame
sub_basin_geometry_gdf = gpd.GeoDataFrame(sub_basin_geometry_df, geometry='geometry')

# Creating a new sub_basin_id column
sub_basin_geometry_gdf['sub_basin_id_simple'] = range(1, len(sub_basin_geometry_gdf) + 1)
st.write(sub_basin_geometry_df)

### Creating a dropdown menu

# Creating a iterable to pass to the selectbox
sub_basin_id = sub_basin_geometry_gdf['sub_basin_id_simple'].to_list()
# Creating selectbox
sub_basin_selection_id_user = st.selectbox('Select a subbasin', sub_basin_id)

# creating a mapping of sub_basin_id_simple to sub_basin_id
sub_basin_mappings = dict(zip(sub_basin_geometry_gdf['sub_basin_id_simple'], sub_basin_geometry_gdf['sub_basin_id']))
# Getting the selected sub_basin_id from the mapping
sub_basin_selection_id = sub_basin_mappings[sub_basin_selection_id_user]

# st.write(sub_basin_selection_id)

### Creating queries 

# Extracting land aridity stats
aridity_stats_query = (f'''
SELECT * FROM climate_resilience.aridity_stats_{geo_level} WHERE sub_basin_id={sub_basin_selection_id};''')

st.write(aridity_stats_query)

# Executing query 
aridity_stats = conn.query(aridity_stats_query, ttl=None) # Store catched result
st.write(aridity_stats)

# Extracting population stats
population_stats_query = (f'''
SELECT * FROM climate_resilience.mv_subbasin_population_statistics WHERE sub_basin_id={sub_basin_selection_id};''')
# Executing query 
population_stats = conn.query(population_stats_query, ttl=None) # Store catched result
st.write(population_stats)

# Water_distribution points
water_distribution_query = (f'''
SELECT * FROM climate_resilience.water_distribution''')
# Executing query 
water_distribution = conn.query(water_distribution_query, ttl=None) # Store catched result
st.write(water_distribution)

# Extracting drought severity data
drought_severity_query = (f'''
SELECT * FROM climate_resilience.drought_severity_stats_{geo_level} 
WHERE sub_basin_id={sub_basin_selection_id}''')
# Executing query 
drought_severity = conn.query(drought_severity_query, ttl=None) # Store catched result
st.write(drought_severity)

# Extracting precipitation data
precipitation_stats_query = (f'''
SELECT * FROM climate_resilience.monthly_rainfall_stats_{geo_level} 
WHERE sub_basin_id={sub_basin_selection_id}''')
# Executing query 
precipitation_stats = conn.query(precipitation_stats_query, ttl=None) # Store catched result
st.write(precipitation_stats.head())

# Extracting data max temperature 
daily_max_temp_query = (f'''
SELECT * FROM climate_resilience.monthly_max_temp_stats_{geo_level} WHERE sub_basin_id={sub_basin_selection_id}''')
max_temp = conn.query(daily_max_temp_query)
st.write(daily_max_temp.head())

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
st.write(f"## Total area of the {sub_basin_selection_id} region")
# Adding `area_sqkm` text
st.write("#### Area (sq km): ", f"{population_stats['area_sqkm'].item():,.2f}")


### Creating static chart

# Creating bar chart of land aridity stats
aridity_chart = alt.Chart(aridity_long, title='Land Aridity Distribution').mark_bar().encode(
    x=alt.X('aridity_type:N', sort='-y'),
    y='percentage:Q',
    color='aridity_type:N'

)
st.altair_chart(aridity_chart)

### Creating plots of the monthly enviromental dataset (monthly precipitation, monthly drought, monthly max temperature)
# st.write(drought_severity.head())

# Creating monthly precipitation chart
preciptation_chart = alt.Chart(precipitation_stats, title='Monthly Precipitation').mark_line().encode(
    x=alt.X('year_month:T', title='Month'),
    y=alt.Y('monthly_average:Q', title='Average Precip'),
    tooltip=['year_month', 'monthly_average', 'monthly_min', 'monthly_max']
)

# Creating daily max temperature chart
daily_max_temp_chart = alt.Chart(max_temp, title='Monthly Max Temperature').mark_line().encode(
    x=alt.X('year_month:T', title='Month'),
    y=alt.Y('monthly_average:Q', title='Average Max Temp (°C)'),
    tooltip=['year_month', 'monthly_average', 'monthly_max', 'monthly_min']
)

# Creating a long format of the drought severity data
drought_severity_long = pd.melt(drought_severity, id_vars=["measure_date"], value_vars=["pct_moderate_drought", "pct_severe_drought", "pct_extreme_drought"], var_name="drought_severity_type", value_name="percentage")

# Remapping the drought types to more readable format
drought_severity_long['drought_severity_type'] = drought_severity_long['drought_severity_type'].map({'pct_moderate_drought': 'Moderate Drought', 'pct_severe_drought': 'Severe Drought', 'pct_extreme_drought': 'Extreme Drought'})

# st.write(drought_severity_long.head())
# Creating monthly area line charrt of drought severity 
drought_severity_chart = alt.Chart(drought_severity_long, title='Monthly Drought Severity').mark_area().encode(
    x=alt.X('measure_date:T', title='Month'),
    y=alt.Y('percentage:Q', title='Average Drought Severity'),
    color='drought_severity_type:N',
    tooltip=['measure_date', 'drought_severity_type', 'percentage']
)

# Creating a tabbed layout for the monthly environmental data
st.write("## Monthly Environmental Data")
tab1, tab2, tab3 = st.tabs(["Monthly Precipitation", "Monthly Max Temperature", "Monthly Drought Severity"])
with tab1:
    st.altair_chart(preciptation_chart)
with tab2:
    st.altair_chart(daily_max_temp_chart)
with tab3:
    st.altair_chart(drought_severity_chart)








