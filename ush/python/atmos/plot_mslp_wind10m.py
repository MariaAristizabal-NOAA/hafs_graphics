#!/usr/bin/env python3

"""This script is to plot out HAFS atmospheric MSLP and 10-m wind."""

import os
import sys
import logging
import math
import datetime

import yaml
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter

import grib2io
from netCDF4 import Dataset

import matplotlib
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.path as mpath
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec
from mpl_toolkits.axes_grid1 import make_axes_locatable

import pyproj
import cartopy
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from cartopy.mpl.ticker import (LongitudeLocator, LongitudeFormatter, LatitudeLocator, LatitudeFormatter)

# Parse the yaml config file
print('Parse the config file: plot_atmos.yml:')
with open('plot_atmos.yml', 'rt') as f:
    conf = yaml.safe_load(f)
conf['stormNumber'] = conf['stormID'][0:2]
conf['initTime'] = pd.to_datetime(conf['ymdh'], format='%Y%m%d%H', errors='coerce')
conf['fhour'] = int(conf['fhhh'][1:])
conf['fcstTime'] = pd.to_timedelta(conf['fhour'], unit='h')
conf['validTime'] = conf['initTime'] + conf['fcstTime']

# Set Cartopy data_dir location
cartopy.config['data_dir'] = conf['cartopyDataDir']
print(conf)

fname = conf['stormID'].lower()+'.'+conf['ymdh']+'.'+conf['stormModel'].lower()+'.'+conf['stormDomain']+'.'+conf['fhhh']+'.grb2' 
grib2file = os.path.join(conf['COMhafs'], fname)
print(f'grib2file: {grib2file}')
grb = grib2io.open(grib2file,mode='r')   

print('Extracting lat, lon')
lat = np.asarray(grb.select(shortName='NLAT')[0].data())
lon = np.asarray(grb.select(shortName='ELON')[0].data())
[nlat, nlon] = np.shape(lon)

print('Extracting PRMSL')
slp = grb.select(shortName='PRMSL',level='mean sea level')[0].data()
slp.data[slp.mask] = np.nan
slp = np.asarray(slp) * 0.01 # convert Pa to hPa
slp = gaussian_filter(slp, 5)

print('Extracting UGRD, VGRD at 10 m above ground')
levstr='10 m above ground'
ugrd = grb.select(shortName='UGRD', level=levstr)[0].data()
ugrd.data[ugrd.mask] = np.nan
ugrd = np.asarray(ugrd) * 1.94384 # convert m/s to kt

vgrd = grb.select(shortName='VGRD', level=levstr)[0].data()
vgrd.data[vgrd.mask] = np.nan
vgrd = np.asarray(vgrd) * 1.94384 # convert m/s to kt

# Calculate wind speed
wspd = (ugrd**2+vgrd**2)**.5

#===================================================================================================
print('Plotting MSLP and 10-m wind')
fig_prefix = conf['stormName'].upper()+conf['stormID'].upper()+'.'+conf['ymdh']+'.'+conf['stormModel']

# Set default figure parameters
mpl.rcParams['figure.figsize'] = [8, 8]
mpl.rcParams["figure.dpi"] = 150
mpl.rcParams['axes.titlesize'] = 9
mpl.rcParams['axes.labelsize'] = 8
mpl.rcParams['xtick.labelsize'] = 8
mpl.rcParams['ytick.labelsize'] = 8
mpl.rcParams['legend.fontsize'] = 8

if conf['stormDomain'] == 'grid02':
    mpl.rcParams['figure.figsize'] = [6, 6]
    fig_name = fig_prefix+'.storm.'+'slp_10m_wind.'+conf['fhhh'].lower()+'.png'
    cbshrink = 1.0
    skip = 20
    wblength = 4.5
    lonmin = lon[int(nlat/2), int(nlon/2)]-3
    lonmax = lon[int(nlat/2), int(nlon/2)]+3
    latmin = lat[int(nlat/2), int(nlon/2)]-3
    latmax = lat[int(nlat/2), int(nlon/2)]+3
else:
    mpl.rcParams['figure.figsize'] = [8, 4.8]
    fig_name = fig_prefix+'.'+'slp_10m_wind.'+conf['fhhh'].lower()+'.png'
    cbshrink = 1.0
    skip = round(nlon/360)*10
    wblength = 4
   #skip = 40
    lonmin = np.min(lon)
    lonmax = np.max(lon)
    latmin = np.min(lat)
    latmax = np.max(lat)

myproj = ccrs.PlateCarree()
transform = ccrs.PlateCarree()

# create figure and axes instances
fig = plt.figure()
ax = plt.axes(projection=myproj)
ax.axis('equal')

cflevels = [0,5,10,15,20,25,30,35,      # TD
            40,45,50,55,60,65,          # TS
            70,75,80,85,                # H1
            90,95,100,                  # H2
            105,110,115,                # H3
            120,125,130,135,            # H4
            140,145,150,155,160,165]    # H5

cfcolors = ['white','white','lightcyan','paleturquoise','cyan','darkturquoise','darkcyan',    # TD: cyanish
            'aquamarine','mediumspringgreen','limegreen','mediumseagreen','seagreen','green', # TS: greenish
            'olive','darkkhaki','khaki','yellow',                                             # H1: Yellowish
            'gold','orange','darkorange',                                                     # H2: Orange
            'deeppink','crimson','red',                                                       # H3: Red
            'lightcoral','indianred','firebrick','brown','darkred',                           # H4: Dark red or thick brown
            'purple','darkviolet','magenta','violet','plum','thistle']                        # H5: magenta or violet

cm = matplotlib.colors.ListedColormap(cfcolors)
norm = matplotlib.colors.BoundaryNorm(cflevels, cm.N)  

cf = ax.contourf(lon, lat, wspd, cflevels, cmap=cm, norm=norm, transform=transform)
#cb = plt.colorbar(cf, orientation='vertical', pad=0.02, aspect=50, shrink=cbshrink, extendrect=True, 
#                  ticks=[10,20,30,35,40,50,60,65,70,80,85,90,100,110,115,120,130,140,150,160])
#cb.ax.set_yticklabels(['10','20','30','TS','40','50','60','H1','70','80','H2','90',
#                       'H3','110','H4','120','130','H5','150','160'])
cb = plt.colorbar(cf, orientation='vertical', pad=0.02, aspect=50, shrink=cbshrink, extendrect=True, 
                  ticks=[10,20,30,34,40,50,60,64,70,80,90,96,100,110,120,130,140,150,160])
cb.ax.set_yticklabels(['10','20','30','TS','40','50','60','HR','70','80','90',
                       'MH','100','110','120','130','140','150','160'])

wb = ax.barbs(lon[::skip,::skip], lat[::skip,::skip], ugrd[::skip,::skip], vgrd[::skip,::skip], 
              length=wblength, linewidth=0.2, color='black', transform=transform)

cslevels = np.arange(850,1050,5)
cs = ax.contour(lon, lat, slp, levels=cslevels, colors='black', linewidths=0.6, transform=transform)
lblevels = np.arange(850,1050,10)
lb = plt.clabel(cs, levels=lblevels, inline_spacing=1, fmt='%d', fontsize=8)

# Add borders and coastlines
#ax.add_feature(cfeature.LAND, facecolor='whitesmoke')
ax.add_feature(cfeature.BORDERS, linewidth=0.5, facecolor='none', edgecolor='gray')
ax.add_feature(cfeature.STATES, linewidth=0.5, facecolor='none', edgecolor='gray')
ax.add_feature(cfeature.COASTLINE, linewidth=1.0, facecolor='none', edgecolor='dimgray')

gl = ax.gridlines(crs=transform, draw_labels=True, linewidth=0.6, color='lightgray', alpha=0.6, linestyle=(0, (5, 10)))
gl.top_labels = False
gl.right_labels = False
gl.xlabel_style = {'size': 8, 'color': 'black'}
gl.ylabel_style = {'size': 8, 'color': 'black'}

print('lonlat limits: ', [lonmin, lonmax, latmin, latmax])
ax.set_extent([lonmin, lonmax, latmin, latmax], crs=transform)

title_center = 'MSLP (hPa) and 10-m Wind (shaded, kt)'
ax.set_title(title_center, loc='center', y=1.05)
title_left = conf['stormModel']+' '+conf['stormName']+conf['stormID']
ax.set_title(title_left, loc='left')
title_right = conf['initTime'].strftime('Init: %Y%m%d%HZ ')+conf['fhhh'].upper()+conf['validTime'].strftime(' Valid: %Y%m%d%HZ')
ax.set_title(title_right, loc='right')

#plt.show() 
plt.savefig(fig_name, bbox_inches='tight')
plt.close(fig)
