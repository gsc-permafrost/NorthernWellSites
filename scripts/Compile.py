import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path
from tabulate import tabulate
import matplotlib as mpl

metadata = pd.DataFrame({
    'Source':[
        'GSC',
        'OROGO',
        'Basin',
        'GeoYukon',
        'Arktis',
        'LTLC'
    ],
    'Description':[
        'GSC open files with embedded well site data for the Mackenzie Delta and Beaufort Sea, primarily sourced from the Canadian Energy Regulator and/or Industry',
        'NWT Office of the Regulator of Oil and Gas Operation (OROGO) maintains a public database of all wells in the NWT *outside of* the Inuvialuit Settlement Region',
        'Database maintained by the Canadian Energy Regulator (CER) covering the central and eastern Arctic',
        'Yukon government data portal',
        'Consultant report for the Inuvialuit Regional Corporation (IRC) with an embedded table of well site data',
        'Consultant report for Aboriginal Affairs and Northern Development Canada with an embedded table of well site data'],
    'Citation':[
        '@osadetz_review_mackenzie_2005_a; @hu_permafrost_investigation_2013_a; hu_overpressure_detection_2021_a',
        '@orogo_orogo_well_2026_a',
        '@natural_resources_canada_basin_contains_2021_a',
        '@yukon_geocortex_viewer_2026_a',
        '@van_gulck_inuvialuit_settlement_2020_a',
        '@callow_oil_gas_2013_a'
        ],
    },
    index=['GSC','OROGO','Basin','GeoYukon','Arktis','LTLC'])

with open('includes/Table1.qmd','w+') as f:
    f.write(tabulate(metadata[['Source','Description','Citation']],headers='keys',showindex=False))

pd.set_option('display.max_columns', None)

index = 'UWI' # Universal Well Identifier

standardCols = [
    'x','y', # Geometry columns
    'Name', # Name from original dataset
    'Status', # Current status
    'Operator', #Listed operator
    'Spud_Date', # Date well was first drilled
    'Geologic_Formation', # Geologic Formation
    'Depth', # Depth of well
    'Data_Source' #source(s) for the data
    ]


## GSC data

# https://ostrnrcan-dostrncan.canada.ca/entities/publication/d623c10f-690c-41a9-a441-6d56e186401a
GSC = pd.read_csv('source_data/wells/GSC/GSC_OF_6959.csv',encoding='utf-8')
GSC['x'] = GSC['SURF_LONG']
GSC['y'] = GSC['SURF_LAT']

GSC = GSC.rename(
    columns={
        'Well Short Name':'Name',
        'Well Status':'Status',
        'Formation':'Geologic_Formation'
     }
)
GSC = GSC.set_index("Name")

#https://ostrnrcan-dostrncan.canada.ca/entities/publication/ad4353b9-f7b9-4855-b895-e452dcd12292
GSC2 = pd.read_csv('source_data/wells/GSC/GSC_OF_4828.csv')

for c in ['Latitude', 'Longitude']:
    # print(GSC2.loc[GSC2[c].replace(r'[^0-9.]',' ',regex=True).str.split().str.len()>3,c])
    DMS = pd.DataFrame(GSC2[c].replace(r'[^0-9.]',' ',regex=True).str.split().to_list(),columns=['D','M','S'],index=GSC2['Well Name'])
    print(DMS)
    if len(DMS.loc[DMS['M'].astype('float')>60]):
        print('Implausible Values')
        print(DMS.loc[DMS['M'].astype('float')>60])
        
    GSC2[c] = (DMS['D'].astype('float')+DMS['M'].astype('float')/60+DMS['S'].astype('float')/3600).values

GSC2['x'] = GSC2['Longitude']*-1
GSC2['y'] = GSC2['Latitude']

GSC2 = GSC2.rename(
    columns={
        'Well Name':'Name',
        'Company':'Operator',
        'TVD':'Depth'
    }
)
GSC2 = GSC2.set_index('Name')

# https://ostrnrcan-dostrncan.canada.ca/entities/publication/5ca84673-f85a-4614-bfde-f6c573ed2f07
GSC3 = pd.read_csv('source_data/wells/GSC/GSC_OF_327948.csv')

GSC3 = GSC3.rename(
    columns={
        'Well name':'Name',
    }
)
GSC3 = GSC3.loc[~GSC3['UWI'].duplicated(keep='first')]
GSC3 = GSC3.set_index('Name')
GSC2 = GSC2.join(GSC3[['UWI']],how='left')
GSC2 = GSC2.join(GSC[['UWI']],how='left',rsuffix='_2')
GSC2['UWI'] = GSC2['UWI'].fillna(GSC2['UWI_2'])
GSC2 = GSC2.drop(columns=['UWI_2'])

missingUWI = {
    'Smoking Hills A-23':'300A236930126150',# ISR Report
    'Mallik 3L-38':'303L386930134300',# ISR Report
    'Mallik 4L-38':'304L386930134300',# ISR Report

}
for key,value in missingUWI.items():
    GSC2.loc[GSC2.index==key,'UWI'] = value

GSC = GSC.reset_index()
fna = GSC2.loc[GSC2['UWI'].isna(),'UWI']
fna = {k:v for k,v in zip(fna.index,[f'NAN_GSC_{i}' for i in range(len(fna))])}
GSC2.loc[GSC2['UWI'].isna(),'UWI'] = GSC2.loc[GSC2['UWI'].isna(),'UWI'].fillna(fna)
GSC = GSC.set_index('UWI')
GSC2 = GSC2.reset_index()

GSC2 = GSC2.set_index('UWI')

# Combine the GSC records
GSC = GSC.join(GSC2[['Operator','Depth']],how='left')

GSC = pd.concat([GSC,GSC2.loc[~GSC2.index.isin(GSC.index),['Name','Operator','Depth','x','y']]])

GSC['Data_Source'] = 'GSC'
GSC['Spud_Date'] = pd.to_datetime('NaT')

# Table B-1 in 
# https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&cad=rja&uact=8&ved=2ahUKEwiT35ezmLKWAxVyoisGHbwrKCEQFnoECA0QAQ&url=https%3A%2F%2Firc.inuvialuit.com%2Fwp-content%2Fuploads%2F2023%2F10%2FIRC_Drilling-Sumps-Failure-and-Climate-Change-Report.pdf&usg=AOvVaw0j_-_UcZ_u18z3As721IPS&opi=89978449
ISR = pd.read_csv('source_data/wells/ISR/ISR_well_report_B1.csv')
ISR = ISR.loc[~ISR['Well Name'].isna()].copy()
mult = [1,1/60,1/3600,1/3600*.1]
for c in ['Latitude (NAD83) -Well Post', 'Longitude (NAD83) -Well Post']:
    DMS = pd.DataFrame(ISR[c].replace(r'[^A-Za-z0-9.]',' ',regex=True).str.split().to_list(),columns=['D','M','S'],index=ISR['Well Name'])
    if len(DMS.loc[DMS['M'].astype('float')>60]):
        print('Implausible Values')
        print(DMS.loc[DMS['M'].astype('float')>60])
        
    ISR[c] = (DMS['D'].astype('float')+DMS['M'].astype('float')/60+DMS['S'].astype('float')/3600).values

ISR['x'] = ISR['Longitude (NAD83) -Well Post']*-1
ISR['y'] = ISR['Latitude (NAD83) -Well Post']

ISR = ISR.rename(
    columns={
        'Well Name':'Name',
        'Status':'Status',
        'Current Owner':'Operator',
        'Original Spud Date':'Spud_Date',
        'Depth (m)':'Depth'
    }
)

ISR['Geologic_Formation'] = None
ISR['Data_Source'] = 'Arktis'
ISR['Spud_Date'] = pd.to_datetime(ISR['Spud_Date'],format="%d-%b-%y",errors='coerce').map(lambda x: x.replace(year=x.year - 100) if x.year >= 2040 else x)

ISR['UWI'] = ISR['UWI'].str.replace(' ','')


ISR = ISR.set_index(index)

# https://www.orogo.gov.nt.ca/en/orogo-well-status
OROGO = pd.read_csv('source_data/wells/NWT/orogo-well-status-updated-2026-04-10.csv')
OROGO = OROGO.dropna(how='all')
OROGO['y'] = OROGO['NAD_83_LatDD']
OROGO['x'] = OROGO['NAD_83_LongDD']
OROGO['Data_Source'] = 'OROGO'
OROGO['Geologic_Formation'] = None
OROGO['Depth'] = np.nan

OROGO = OROGO.rename(
    columns={
        'Well Name':'Name',
        'Well Status':'Status',
        'Last Operator':'Operator',
        'First SPUD Year':'Spud_Date'
    }
)

OROGO['Spud_Date'] = pd.to_datetime(OROGO['First SPUD year'],format='%Y')

OROGO = OROGO.set_index('UWI')

#print(OROGO.head())


# https://mapservices.gov.yk.ca/GeoYukon/index.html?layerTheme=9
Yukon = gpd.read_file('source_data/wells/yukon/Oil_and_Gas_Wells_50k.shp').to_crs('NAD1983')
Yukon['short_code'] = Yukon['WELL_LABEL']
Yukon['x'] = Yukon.geometry.x
Yukon['y'] = Yukon.geometry.y

Yukon = Yukon.rename(
    columns={
        'WELL_NAME':'Name',
        'STATUS':'Status',
        'OPERATOR':'Operator',
        'DATE':'Spud_Date',
        'WELL_UWI':'UWI',
        'BASIN_NAME':'Geologic_Formation'
    }
)
Yukon = Yukon.set_index('UWI')
Yukon['Data_Source'] = 'GeoYukon'
Yukon['Depth'] = np.nan


# https://basin.marine-geo.canada.ca/index_e.php
Basin = pd.read_csv('source_data/wells/Basin/BASIN_well_coords.txt',delimiter='\t',skiprows=3)
Basin2 = pd.read_csv('source_data/wells/Basin/q1787332704.txt',delimiter='\t',skiprows=3)
Basin = pd.merge(Basin,Basin2[['Well Name','GSC #','Original Spud Year','Operator','Status','Unique Well Identifier']],on='Well Name',how='left')

Basin = Basin.rename(
    columns={
        'Well Name':'Name',
        'Unique Well Identifier':'UWI',
        'Basin':'Geologic_Formation',
        'Original Spud Year':'Spud_Date',
        'Status':'Status',
        # 'Operator':'Operator'
	}
)

Basin['Spud_Date'] = pd.to_datetime(Basin['Spud_Date'],format='%Y')
Basin['x'] = Basin['Longitude (NAD83)']
Basin['y'] = Basin['Latitude (NAD83)']
Basin['Data_Source'] = 'Basin'
Basin['UWI'] = Basin['UWI'].str.replace(' ','')

fna = Basin.loc[Basin['UWI'].isna(),'UWI']
fna = {k:v for k,v in zip(fna.index,[f'NAN_Basin_{i}' for i in range(len(fna))])}
Basin.loc[Basin['UWI'].isna(),'UWI'] = Basin.loc[Basin['UWI'].isna(),'UWI'].fillna(fna)
Basin = Basin.set_index('UWI')
Basin = Basin.loc[((Basin.y>60)&(~Basin.index.isna()))].copy()
Basin['Depth'] = np.nan


# https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&cad=rja&uact=8&ved=2ahUKEwjgt-Of8L6WAxV7MYYAHRquHEwQFnoECBkQAQ&url=https%3A%2F%2Fbeaufortrea.ca%2Fwp-content%2Fuploads%2F2013%2F03%2F2.0-L-Callow-Oil-and-Gas-Forecast.pdf&usg=AOvVaw1_HuVT_tPfw6bXXRiTD441&opi=89978449
LTLC = pd.read_csv('source_data/wells/misc/LTLC_report.csv')
LTLC['Data_Source'] = 'LTLC'
# LTLC["UWI"] = None
GSCa = GSC.reset_index()
GSCa['Name'] = GSCa['Name'].str.lower()
GSCa = GSCa.set_index('Name')
ISRa = ISR.reset_index()
ISRa['Name'] = ISRa['Name'].str.lower()
ISRa = ISRa.set_index('Name')
LTLC = LTLC.set_index(LTLC['Name'].str.lower())
LTLC = LTLC.join(GSCa[['UWI']])
fna = LTLC.loc[LTLC['UWI'].isna(),'UWI']
fna = {k:v for k,v in zip(fna.index,[f'NAN_LTLC_{i}' for i in range(len(fna))])}
LTLC.loc[LTLC['UWI'].isna(),'UWI'] = LTLC.loc[LTLC['UWI'].isna(),'UWI'].fillna(fna)
LTLC = LTLC.set_index('UWI')
LTLC['Data_Source'] = 'LTLC'
LTLC['Spud_Date'] = pd.to_datetime(LTLC['Spud_Date'])
for c in standardCols:
    if c not in LTLC:
        LTLC[c] = np.nan

Temp = pd.concat(
    [
        GSC[['Data_Source']],
		Basin[['Data_Source']],
		Yukon[['Data_Source']],
		OROGO[['Data_Source']],
		ISR[['Data_Source']],
        LTLC[['Data_Source']]
	]
)
Wx = Temp.groupby(Temp.index)[['Data_Source']].agg(list).reset_index()

Wx['Data_Source'] = Wx['Data_Source'].str.join('-')

UWI_by_source = Wx.groupby('Data_Source').agg(list)
Summary = Wx.groupby('Data_Source').count().sort_values(by='UWI',ascending=False)


dataSources = {
    'GSC':GSC[standardCols],
    'Arktis':ISR[standardCols],
    'OROGO':OROGO[standardCols],
    'GeoYukon':Yukon[standardCols],
    'Basin':Basin[standardCols],
    'LTLC':LTLC[standardCols]
}
    
toCat = []
for source in Summary.index:
    sources = source.split('-')
    if len(sources) == 1:
        ds = dataSources[source]
        toCat.append(
            ds.loc[ds.index.isin(UWI_by_source.loc[source,'UWI'])]
		)
    else:
        temp = dataSources[sources[0]].loc[dataSources[sources[0]].index.isin(UWI_by_source.loc[source,'UWI'])].copy().sort_index()
        temp['Data_Source'] = source
        for alt in sources[1:]:
            ftemp = dataSources[alt].loc[dataSources[alt].index.isin(UWI_by_source.loc[source,'UWI'])].copy().sort_index()
            for c in standardCols:
                temp[c] = temp[c].fillna(ftemp[c])
        toCat.append(temp)

WellSites = pd.concat(toCat)
WellSites = gpd.GeoDataFrame(WellSites,geometry=gpd.points_from_xy(x=WellSites['x'],y=WellSites['y']),crs='NAD1983').to_crs('EPSG:4326')
WellSites['Operator'] = WellSites['Operator'].fillna(None)
WellSites['Spud_Date'] = WellSites['Spud_Date'].dt.strftime('%Y-%m-%d').fillna(None)

cbf = gpd.read_file('source_data/boundary/lpr_000b16a_e.shp').to_crs(WellSites.crs)
WellSites['Off_Shore'] = True
WellSites.loc[WellSites.within(cbf.dissolve().geometry[0]),'Off_Shore'] = False


WellSites['Latitude'] = WellSites.geometry.y
WellSites['Longitude'] = WellSites.geometry.x
WDB = pd.DataFrame(WellSites.drop(columns=['geometry','x','y']))
WDB.to_csv('NorthernWellSites.csv')

Smry = WDB.groupby('Data_Source').count()
for c in Smry.columns:
    if c != 'Name':
        Smry[c] = (100*Smry[c]/Smry['Name']).round(1)

Smry['n'] = WellSites.groupby('Data_Source').count()['Name']
Smry = Smry.drop(columns='Name')
# breakpoint()


fn = 'source_data/wells/NorthernWellSites.geojson'
if os.path.isfile(fn):
    os.remove(fn)
WellSites['description'] = '<table><tbody><tr><td><b>Operator:</b></td><td>'+WellSites['Operator'].fillna('Unknown') + '</td></tr><tr><td><b>Spud Date:</b></td><td>' + WellSites['Spud_Date'].fillna('Unknown')+ '</td></tr><tr><td><b>Data Source:</b></td><td>' + WellSites['Data_Source'] + '</td></tr></tbody></table>'
WellSites.to_file(fn,driver='geojson', mode='w')


with open(fn) as t:
    wells = json.load(t)

template = 'mapping/pointMapTemplate.html'
mapTemplate = Path(template).read_text()

mapTemplate = mapTemplate.replace('pointDataJson',json.dumps(wells))

mapTemplate = mapTemplate.replace("['get','Category']","['get','Data_Source']")
N = len(Summary)
cmap = mpl.colormaps['Set2'].resampled(N)
colors = [mpl.colors.to_hex(cmap(i)) for i in np.linspace(0, 1, N)]
clist = ', '.join([f"'{ix}', '{c}'" for ix,c in zip(Summary.index,colors)])
mapTemplate = mapTemplate.replace("'None','#000000'",clist)


with open(f'mapping/NorthernWellSites.html','w+') as out:
    out.write(mapTemplate)

# Summary = Summary.reset_index().rename(columns={'UWI':'Number of Wells','Data_Source':'Data Source(s)'})

# print(Summary)
Smry = Smry.sort_values(by='n',ascending=False)
Smry = Smry.reset_index()
Smry['Lat/Long'] = Smry['Latitude'].copy()
Smry = Smry[['Data_Source','n','Lat/Long','Depth','Status','Operator','Spud_Date','Geologic_Formation']].copy()
for col in Smry[['Lat/Long','Depth','Status','Operator','Spud_Date','Geologic_Formation']]:
    Smry[col] = Smry[col].astype(str)
print(Smry)
with open('includes/Table2.qmd','w+') as f:
    f.write(tabulate(Smry,headers='keys',showindex=False))

# import geopandas as gpd
# import matplotlib.pyplot as plt
# import geodatasets
# import contextily as cx

# WellSites = gpd.read_file('source_data/wells/WellDatabase.geojson').to_crs('EPSG:3857')

# ISR_poly = gpd.read_file('source_data/context/Region_inuite_Inuit_Region.shp')
# ISR_poly = ISR_poly.loc[ISR_poly['REGION']=='Inuvialuit'].to_crs('EPSG:3857')
# fig,ax=plt.subplots()

# for source in WellSites['Data_Source'].unique():
# 	Wp = WellSites.loc[WellSites['Data_Source'] == source].copy()
# 	cax = ax.scatter(Wp.geometry.x,Wp.geometry.y,edgecolor='black',s=50,alpha=0.5,label=f"{Wp.shape[0]}: {source}")
# offset = 1e5
# xmin,xmax,ymin,ymax=WellSites.geometry.x.min()-offset,WellSites.geometry.x.max()+offset,WellSites.geometry.y.min()-offset,WellSites.geometry.y.max()+offset

# ISR_poly.plot(ax=ax,color='None',edgecolor='k')

# ax.set_xlim(xmin,xmax)
# ax.set_ylim(ymin,ymax)
# cx.add_basemap(ax,crs = WellSites.crs , source=cx.providers.Esri.WorldImagery)
# ax.set_title("Well Sites in the Mackenzie Delta Region")
# ax.axis('off')
# ax.legend()
# plt.show()