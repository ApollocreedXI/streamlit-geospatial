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
geo_level = 'sub_basin'

### Extracting basic geo-level information

# Extracting geo_level information
sub_basin_geometry_data_query = (f'''
SELECT * FROM climate_resilience.proj_sub_basin ORDER BY sub_basin_id''')
# Executing query
sub_basin_geometry_df = conn.query(sub_basin_geometry_data_query, ttl=None) # Store catched result
# Converting the geometry column to WKT
sub_basin_geometry_df['geometry'] = sub_basin_geometry_df['sub_basin_geometry_proj'].apply(loads)
# Converting to GeoDataFrame
sub_basin_geometry_gdf = gpd.GeoDataFrame(sub_basin_geometry_df, geometry='geometry')
# st.write(sub_basin_geometry_df)

# Creating a new simple subbasin id
sub_basin_geometry_gdf['sub_basin_id_simple'] = range(1, len(sub_basin_geometry_gdf) + 1)

### Creating a dropdown menu
# Creating a iterable to pass to the selectbox
sub_basin_names = sub_basin_geometry_gdf['sub_basin_id_simple'].to_list()
# Creating selectbox
sub_basin_selection = st.selectbox('Select a Subbasin', sub_basin_names)

# Creating a mapping of sub_basin_id_simple to sub_basin_id
sub_basin_id_mapping = dict(zip(sub_basin_geometry_gdf['sub_basin_id_simple'], sub_basin_geometry_gdf['sub_basin_id']))
# Getting the selected sub_basin_id
sub_basin_selection_id = sub_basin_id_mapping[sub_basin_selection]

### Creating queries 

# Extracting the basin geometry table to obtain the basin names that the subbasin reports to 
basin_geometry_data_query = (f'''
SELECT * FROM climate_resilience.proj_major_basin''')
# Executing query
basin_geometry_df = conn.query(basin_geometry_data_query, ttl=None) # Store catched result
# Creating a mapping of basin_id to basin_name
basin_id_to_name = dict(zip(basin_geometry_df['basin_id'], basin_geometry_df['basin_name']))
# Applying the mapping to the sub_basin_geometry_gdf
sub_basin_geometry_gdf['basin_name'] = sub_basin_geometry_gdf['basin_id'].map(basin_id_to_name)


# Extracting land aridity stats
aridity_stats_query = (f'''
SELECT * FROM climate_resilience.aridity_stats_{geo_level} WHERE sub_basin_id={sub_basin_selection_id};''')
# Executing query 
aridity_stats = conn.query(aridity_stats_query, ttl=None) # Store catched result
#st.write(aridity_stats)

# Extracting population stats
population_stats_query = (f'''
SELECT * FROM climate_resilience.mv_subbasin_population_statistics WHERE sub_basin_id={sub_basin_selection_id};''')
# Executing query 
population_stats = conn.query(population_stats_query, ttl=None) # Store catched result
#st.write(population_stats)

# Water_distribution points
water_distribution_query = (f'''
SELECT * FROM climate_resilience.mv_sub_basin_waterpoints WHERE sub_basin_id={sub_basin_selection_id};''')
# Executing query 
water_distribution = conn.query(water_distribution_query, ttl=None) # Store catched result
#st.write(water_distribution)

# Extracting drought severity data
drought_severity_query = (f'''
SELECT * FROM climate_resilience.drought_severity_stats_{geo_level} 
WHERE sub_basin_id={sub_basin_selection_id}''')
# Executing query 
drought_severity = conn.query(drought_severity_query, ttl=None) # Store catched result
#st.write(drought_severity)

# Extracting precipitation data
precipitation_stats_query = (f'''
SELECT * FROM climate_resilience.monthly_rainfall_stats_{geo_level} 
WHERE sub_basin_id={sub_basin_selection_id}''')
# Executing query 
precipitation_stats = conn.query(precipitation_stats_query, ttl=None) # Store catched result
#st.write(precipitation_stats.head())

# Extracting data max temperature 
daily_max_temp_query = (f'''
SELECT * FROM climate_resilience.monthly_max_temp_stats_{geo_level} WHERE sub_basin_id={sub_basin_selection_id}''')
max_temp = conn.query(daily_max_temp_query)
#st.write(max_temp.head())

query_ward = (f'''
SELECT * FROM climate_resilience.proj_ward
ORDER BY ward_id''')
ward_df = conn.query(query_ward, ttl=None)
# Converting the geometry column to WKT
ward_df['geometry'] = ward_df['ward_geometry_proj'].apply(loads)
# Converting to GeoDataFrame
ward_df = gpd.GeoDataFrame(ward_df, geometry='geometry')
ward_df = ward_df.set_crs('ESRI:102022')

### EXTRACTING THE TOTAL VULNERABLE AREA OF THE SUBBASIN AND THE PERCENTAGE OF THE TOTAL AREA OF THE SUBBASIN THAT IS HIGHLY VULNERABLE
# Creating a title for the page
#st.write(f"# Subbasin {sub_basin_selection} Descriptive Statistics")

# Stateing the basin that the subbasin belongs to
basin_name = sub_basin_geometry_gdf[sub_basin_geometry_gdf['sub_basin_id']==sub_basin_selection_id]['basin_name'].item()
st.write(f"# The selected subbasin belongs to the :blue[{basin_name}]")

@st.cache_data
def read_data(loc):
    # Reading in the data
    df = pd.read_csv(loc)

    # Returning the data
    return df

# Loading in data
loc = r'excel_files/ward_water_resilience_labels.csv'
df = read_data(loc)

# Merging the ward_df with the water resilience labels
df_merged = pd.merge(df,ward_df, on='ward_id', how='left')

# Converting to GeoDataFrame
df_merged = gpd.GeoDataFrame(df_merged, geometry='geometry')

# Filtering for highly vulnerable clusters
df_merged_filter = df_merged[(df_merged['cluster_label']==2) | (df_merged['cluster_label']==4)]

# Filtering wards that belong to the selected sub_basin
df_merged_filter = df_merged_filter[df_merged_filter['sub_basin_id']==sub_basin_selection_id]

# Computing the area of the wards in the filtered dataframe
df_merged_filter['area'] = df_merged_filter['geometry'].area

# Creating a groupby 
high_risk_clusters_basin = df_merged_filter.groupby(['sub_basin_id'])['area'].agg(['sum','count']).reset_index()
high_risk_clusters_basin.columns = ['sub_basin_id','total_vulnerable_area_meters_2','vulnerable_ward_count']
high_risk_clusters_basin['total_vulnerable_area_km2'] = high_risk_clusters_basin['total_vulnerable_area_meters_2'] / 1000000

# Adding text for the total area with comma formatting
st.write(f"## Total area of the subbasin {sub_basin_selection} region")
### Adding `area_sqkm` text and the normalized vulnerable percentage of the total area

# Computing the percentage of the total area of the highly vulnerable wards
# Note: This truely communicates the percentage of the total area of the subbasin that has been identified as being under the two vulnerable ward clusters.
# This percentage is slightly different than computing the total area of wards that belong to the subbasin and then computing the percentage of the highly vulnerable wards. 
# The difference is that some wards may not be fully contained within the subbasin, and thus their area may be larger than the area of the subbasin that they are contained within.
# The purpose is to communicate the total area of the subbasin as a descriptive statistic, and then communicate the percentage of that area that is highly vulnerable to water scarcity and droughts.
normalized_vulnerable_percentage = (high_risk_clusters_basin['total_vulnerable_area_km2'].item()/population_stats['area_sqkm'].item())*100 

# Ensuring that the normalized vulnerable percentage does not exceed 100%
if normalized_vulnerable_percentage > 100:
    normalized_vulnerable_percentage = 100

st.write("#### The total area of the region is ", f":yellow[{population_stats['area_sqkm'].item():,.2f}] km², of which ", f":red[{normalized_vulnerable_percentage:.2f} %] is characterized by :red[low water-resiliency]")

# Providing basic text of the population stats
st.write("## Population Statistics")

# Adding text of the total population with comma formating
st.write("#### Total Population is ", f":yellow[{population_stats['total_pop'].item():,}], with a population density of ", f":yellow[{population_stats['density'].item():,.2f}] people per km²")

# Displaying the total number of water points according to WPDX+ and the percentage of functional water points
st.write("## Water Distribution Points")
# Adding text of the total water distribution points with comma formating
if water_distribution['waterpoints_total'].item() == 0:
    st.write("#### According to WPDX+, there are no water distribution points in this subbasin")
else:
    st.write("#### According to WPDX+, the total number of water distribution points is ", f":yellow[{water_distribution['waterpoints_total'].item():,}], of which ", f":green[{water_distribution['waterpoints_functional'].item():,}] are functional")

### Creating static chart
st.write("### Land Aridity Distribution")

# Creating long format of the different percentage of aridity land types
aridity_long = pd.melt(aridity_stats, id_vars=["stat_id"], value_vars=["pct_hyper_arid", "pct_arid", "pct_semi_arid", "pct_dry_sub_humid", "pct_humid"], var_name="aridity_type", value_name="percentage")

# Cleaning up column names
map_names = {'pct_hyper_arid': 'Hyper Arid', 'pct_arid': 'Arid', 'pct_semi_arid': 'Semi Arid', 'pct_dry_sub_humid': 'Dry Sub Humid', 'pct_humid': 'Humid'}
aridity_long['aridity_type'] = aridity_long['aridity_type'].map(map_names)

# Creating an order list for the aridity types
aridity_order = ['Hyper Arid', 'Arid', 'Semi Arid', 'Dry Sub Humid', 'Humid']

# Creating bar chart of land aridity stats
aridity_chart = alt.Chart(aridity_long).mark_bar().encode(
    x=alt.X('aridity_type:N', sort=aridity_order, title='Aridity Type'),
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

    
    # base = alt.Chart(filtered_precipitation_stats).encode(
    # alt.X('year_month:T').title(None)
    # )

    # area = base.mark_area(opacity=0.3, color='#57A44C').encode(
    #     alt.Y('monthly_average').axis(title='Avg. Temperature (°C)', titleColor='#57A44C')
    # )

    # line = base.mark_line(stroke='#5276A7', interpolate='monotone').encode(
    #     alt.Y('monthly_std').axis(title='Precipitation (inches)', titleColor='#5276A7')
    # )

    # chart=alt.layer(area, line).resolve_scale(
    #     y='independent'
    # )
    # st.altair_chart(chart, use_container_width=True)
    

    ### Creating a double axis chart
    
    # Creating monthly mean precipitation chart
    base = alt.Chart(filtered_precipitation_stats, title='Monthly Precipitation').encode(
    x=alt.X('year_month:T', title='Month'))

    line_mean_precipitation = base.mark_area(color='#5276A7').encode(
    y=alt.Y('monthly_average:Q', title='Average Precip (mm)').axis(titleColor='#5276A7' ),
    tooltip=['year_month', 'monthly_average', 'monthly_min', 'monthly_max']
    )

    line_std_precipitation = base.mark_line(color='#57A44C').encode(
    y=alt.Y('monthly_std:Q', title='Standard Deviation of Precipitation (mm)').axis(titleColor='#57A44C'),
    tooltip=['year_month', 'monthly_std']
    )  

    chart = alt.layer(line_mean_precipitation, line_std_precipitation).resolve_scale(
    y='independent')

    # Plotting using streamlit
    st.altair_chart(chart, use_container_width=True)

    ### OLD WAY
    # # Creating monthly mean precipitation chart
    # preciptation_chart = alt.Chart(filtered_precipitation_stats, title='Monthly Precipitation').mark_line().encode(
    # x=alt.X('year_month:T', title='Month',
    #         axis=alt.Axis(format='%b %Y', title='Date')),
    # y=alt.Y('monthly_average:Q', title='Average Precip (mm)'),
    # tooltip=['year_month', 'monthly_average', 'monthly_min', 'monthly_max'])

    # # Creating monthly standard deviation precipitation chart
    # preciptation_chart_std = alt.Chart(filtered_precipitation_stats).mark_line().encode(
    # x=alt.X('year_month:T', title='Month',
    #         axis=alt.Axis(format='%b %Y', title='Date')),
    # y=alt.Y('monthly_std:Q', title='Average Precip (mm)'),
    # tooltip=['year_month', 'monthly_average', 'monthly_min', 'monthly_max'])

    # st.write(filtered_precipitation_stats.head())
    # st.altair_chart(preciptation_chart)
with tab2:
    # Creating max and min objects
    min_date = max_temp['year_month'].min()
    max_date = max_temp['year_month'].max()
    
    # Creating slider
    month_slider_max_temp= st.slider("Select a Month", min_value=min_date, max_value=max_date, value=(min_date,max_date), key="month_slider_max_temp")
    # Filtering the max_temp based on the selected month
    filtered_max_temp = max_temp[(max_temp['year_month'] >= month_slider_max_temp[0]) & (max_temp['year_month'] <= month_slider_max_temp[1])]

    # Creating monthly mean precipitation chart
    base = alt.Chart(filtered_max_temp, title='Monthly Max Temp').encode(
    x=alt.X('year_month:T', title='Month'))

    line_mean_max_temp = base.mark_area(opacity=.80, color='#5276A7').encode(
    y=alt.Y('monthly_average:Q', title='Average Max Temp (°C)').axis(titleColor='#5276A7' ),
    tooltip=['year_month', 'monthly_average', 'monthly_min', 'monthly_max']
    )

    line_std_max_temp = base.mark_line(color='#57A44C').encode(
    y=alt.Y('monthly_temperature_std:Q', title='Standard Deviation of Max Temp (°C)').axis(titleColor='#57A44C'),
    tooltip=['year_month', 'monthly_temperature_std']
    )  

    chart = alt.layer(line_mean_max_temp, line_std_max_temp).resolve_scale(
    y='independent')

    # Plotting using streamlit
    st.altair_chart(chart, use_container_width=True)


    ### OLD WAY
    # # Creating daily max temperature chart
    # daily_max_temp_chart = alt.Chart(filtered_max_temp, title='Monthly Max Temperature').mark_line().encode(
    # x=alt.X('year_month:T', title='Month', axis=alt.Axis(format='%b %Y', title='Date')),
    # y=alt.Y('monthly_average:Q', title='Average Max Temp (°C)'),
    # tooltip=['year_month', 'monthly_average', 'monthly_max', 'monthly_min']
    # )

    # # Plotting
    # st.altair_chart(daily_max_temp_chart)
with tab3:
    # Creating a mapping of sub_basin_id_simple to sub_basin_id
    sub_basin_id_mapping_simple = dict(zip(sub_basin_geometry_gdf['sub_basin_id'], sub_basin_geometry_gdf['sub_basin_id_simple']))

    # Adding sub_basin_id_simple to the drought_severity dataframe
    drought_severity['sub_basin_id_simple'] = drought_severity['sub_basin_id'].map(sub_basin_id_mapping_simple)

    # Creating min and max objects
    min_date = drought_severity['measure_date'].min()
    max_date = drought_severity['measure_date'].max()

    # Creating slider
    month_slider_drought= st.slider("Select a Month", min_value=min_date, max_value=max_date, value=(min_date,max_date), key="month_slider_drought")
    
    # Creating a long format of the drought severity data
    drought_severity_long = pd.melt(drought_severity, id_vars=["measure_date","sub_basin_id_simple"], value_vars=["pct_moderate_drought", "pct_severe_drought", "pct_extreme_drought"], var_name="drought_severity_type", value_name="percentage")

    # Remapping the drought types to more readable format
    drought_severity_long['drought_severity_type'] = drought_severity_long['drought_severity_type'].map({'pct_moderate_drought': 'Moderate Drought', 'pct_severe_drought': 'Severe Drought', 'pct_extreme_drought': 'Extreme Drought'})

    # Filtering the drought_severity based on the selected month
    filtered_drought_severity = drought_severity_long[(drought_severity_long['measure_date'] >= month_slider_drought[0]) & (drought_severity_long['measure_date'] <= month_slider_drought[1])]

    # Creating monthly area line charrt of drought severity 
    drought_severity_chart = alt.Chart(filtered_drought_severity, title='Monthly Drought Severity').mark_area().encode(
    x=alt.X('measure_date:T', title='Month', axis=alt.Axis(format='%b %y', title='Date')),
    y=alt.Y('percentage:Q', title='Percentage of Drought Severity Type'),
    color='drought_severity_type:N',
    tooltip=['measure_date', 'drought_severity_type', 'percentage']
)
    # Plotting
    st.altair_chart(drought_severity_chart)








