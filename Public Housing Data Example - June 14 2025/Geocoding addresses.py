# Set environment
# Load dependencies
import os          # provides tools for interacting with the operating system (e.g., paths, directories)
import pandas as pd
import googlemaps
import time
import urllib.parse
import time
import geopandas as gpd
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point  # <-- Make sure this line is included

# Set wd to path where file is saved
current_directory = os.getcwd()  # returns the current working directory
raw_data_directory = os.path.join(current_directory, "Raw Data")
outputs_directory = os.path.join(current_directory, "Outputs")

# # Change working directory
# os.chdir(raw_data_directory) 

# # Read in your raw address data
# addresses = pd.read_csv('raw_address_data.csv') # full set of 4,162 addresses
# # columns: ['primary_key', 'address', 'neighborhood']

# # Initialize the Google Maps client
# API_KEY = '' # omitting for privacy
# gmaps = googlemaps.Client(key=API_KEY)

# # A helper to geocode one address and build URLs
# def geocode_address(addr):
#     try:
#         # send the request
#         result = gmaps.geocode(addr)
#         if not result:
#             return (None,)*6

#         top = result[0]
#         formatted = top['formatted_address']
#         lat = top['geometry']['location']['lat']
#         lng = top['geometry']['location']['lng']
#         place_id = top.get('place_id')

#         # build the raw API request URL
#         encoded = urllib.parse.quote(addr)
#         raw_url = (
#             f"https://maps.googleapis.com/maps/api/geocode/json"
#             f"?address={encoded}&key={API_KEY}"
#         )

#         # build a Google Maps browser URL (opens a map pin)
#         maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"

#         return formatted, lat, lng, place_id, raw_url, maps_url

#     except Exception as e:
#         print(f"Error geocoding {addr!r}: {e}")
#         return (None,)*6

# # Prepare columns to hold results
# for col in ['geocoded_address','lat','lng','place_id','raw_url','maps_url']:
#     addresses[col] = None

# # Loop through each row, geocode, then pause to respect 50 QPS
# for idx, row in addresses.iterrows():
#     (formatted, lat, lng,
#      place_id, raw_url, maps_url) = geocode_address(row['address'])

#     addresses.at[idx, 'geocoded_address'] = formatted
#     addresses.at[idx, 'lat']              = lat
#     addresses.at[idx, 'lng']              = lng
#     addresses.at[idx, 'place_id']         = place_id
#     addresses.at[idx, 'raw_url']          = raw_url
#     addresses.at[idx, 'maps_url']         = maps_url

#     # throttle: ~0.02s pause → ≈50 requests/sec
#     time.sleep(1/50)

# # Change working directory
# os.chdir(outputs_directory) 

# # Save out your enriched file
# addresses.to_csv('raw_address_data_geocoded_with_urls.csv', index=False)

# print("Results (including URLs) saved to raw_address_data_geocoded_with_urls.csv")

# Change working directory
os.chdir(raw_data_directory) 

# Read in geocoded address data
addresses = pd.read_csv('data_geocoded.csv') # Geocoded set of addresses, including ones without a match (4,162 rows)

# Remove addresses that were not geocoded
addresses_2 = addresses.dropna(subset=['lat', 'lng']) # filtered out NULL values in lat and lng columns (3,077 rows)

# Create a GeoDataFrame in WGS84 (latitude/longitude)
addresses_3 = gpd.GeoDataFrame(
    addresses_2,
    geometry=gpd.points_from_xy(addresses_2['lng'], addresses_2['lat']),
    crs='EPSG:4326'
)

# Read in your Lisbon boundary shapefile
# (assumes files LisbonBoundary.shp + .dbf + etc are in raw_data_directory)
lisbon = gpd.read_file('lisbon_boundary.shp')

# Make sure both layers use the same CRS
# (most city boundary shapefiles might be in a local projected CRS)
lisbon = lisbon.to_crs(addresses_3.crs)

# Filter addresses to those whose points fall within boundary
# Filter points to those within the Lisbon boundary
# Use unary_union in case the boundary is multipart
lisbon_union = lisbon.unary_union
addresses_4 = addresses_3[
    addresses_3.geometry.within(lisbon_union)
].copy() # flag for addresses within Lisbon proper, 2,456 rows

# Add a 'within_expected_range' column (value = 1 for every row)
addresses_4['within_expected_range'] = 1

# Keep only relevant columns for join
addresses_4 = addresses_4[['primary_key', 'within_expected_range']]

# Left‐join onto the original addresses DataFrame/GeoDataFrame
addresses_5 = (
    addresses_2
    .merge(addresses_4, on='primary_key', how='left')
)

# Fill missing counts with 0 (those outside the buffer)
addresses_5['within_expected_range'] = addresses_5['within_expected_range'].fillna(0).astype(int)

# Evaluate # of records that geocoded + have records that fell within expected area
print(addresses_5['within_expected_range'].value_counts()) # 2,456 records that geocoded that are within Lisbon (flagged), 621 that were out of range (flagged), and 1,085 that were not geocoded (filtered out), out of 4,621 original total

# Change working directory
os.chdir(outputs_directory) 

# Export to Excel (drops the geometry column so it’s a plain table)
addresses_5.to_excel('Addresses Geocoded and Flagged.xlsx', index=False)

# Export to KML (will use the geometry column for point locations)
# Filter to only rows where within_expected_range == 1
addresses_6 = gpd.GeoDataFrame(
    addresses_5,
    geometry=gpd.points_from_xy(addresses_5['lng'], addresses_5['lat']),
    crs='EPSG:4326'
)

# Filter for addresses that fall within Lisbon ONLY, or 2,456 records
addresses_6 = addresses_6[
    addresses_6['within_expected_range'] == 1
]

# Export final df to KML for Google Maps visual
addresses_6.to_file('addresses_for_gmaps.kml', driver='KML')

# export to ESRI Shapefile (creates .shp, .shx, .dbf, etc.)
addresses_6.to_file('001_lisbon_public_housing_june_14_2025.shp', driver='ESRI Shapefile')