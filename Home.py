import streamlit as st
import leafmap.foliumap as leafmap

st.set_page_config(layout="wide")

st.sidebar.title("About")
st.sidebar.info("""
    - Web App URL: <https://water-resilience-database-design.streamlit.app/>
    - GitHub repository: <https://github.com/ApollocreedXI/streamlit-geospatial>
    """)

st.sidebar.title("Contact")
st.sidebar.info("""
    James Schorr [schorr@bc.edu](mailto:schorr@bc.edu) | Roydan Cruz [cruzroy@bc.edu](mailto:cruzroy@bc.edu)
    """)



st.title("Database Design for Climate-Resilient Water Management Systems in Tanzania ")

st.markdown("""
    In March 2025, Tanzania released its new water policy that includes the goal of creating a national water grid, along with a focus on climate resilience in all planning and implementation.
    This infrastructure investment intends to provide a reliable and stable water supply to citizens, including rural communities that are highly vulnerable to the impacts of climate change.
    In developing this new infrastructure, policymakers will find it beneficial to evaluate communities that are most vulnerable to the impact of climate change (e.g., more susceptible to droughts and floods) and prioritize investment there.
    Investment prioritization is a challenge as Tanzania’s water management system employs a decentralized structure, creating disparate information regarding administrative water basins and the Water User Associations (WUAs) subsumed in each of these administrative constructs.
    The Capstone Project intends to unify information on the water basins and WUAs, to facilitate the identification of areas or communities under climate stress for investment prioritization. 
    """)

st.info("Click on the left sidebar menu to navigate to the vulnerability clustering app and the exploritory dashboard.")

st.subheader("Timelapse of Satellite Imagery")
st.markdown("""
    The following timelapse animations were created using the Timelapse web app. Click `Timelapse` on the left sidebar menu to create your own timelapse for any location around the globe.
""")

# row1_col1, row1_col2 = st.columns(2)
# with row1_col1:
#     st.image("https://github.com/giswqs/data/raw/main/timelapse/spain.gif")
#     st.image("https://github.com/giswqs/data/raw/main/timelapse/las_vegas.gif")

# with row1_col2:
#     st.image("https://github.com/giswqs/data/raw/main/timelapse/goes.gif")
#     st.image("https://github.com/giswqs/data/raw/main/timelapse/fire.gif")
