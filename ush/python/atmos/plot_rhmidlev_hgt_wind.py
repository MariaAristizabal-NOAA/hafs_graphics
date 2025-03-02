#!/usr/bin/env python3

"""This script is to plot out HAFS atmospheric 700-500hPa mean RH, and 700-hPa geopotential height and wind"""

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

fname = conf['stormID'].lower()+'.'+conf['ymdh']+'.'+conf['stormModel'].lower()+'.'+conf['stormDomain']+'.atm.'+conf['fhhh']+'.grb2'
grib2file = os.path.join(conf['COMhafs'], fname)
print(f'grib2file: {grib2file}')
grb = grib2io.open(grib2file,mode='r')

print('Extracting lat, lon')
lat = np.asarray(grb.select(shortName='NLAT')[0].data())
lon = np.asarray(grb.select(shortName='ELON')[0].data())
# The lon range in grib2 is typically between 0 and 360
# Cartopy's PlateCarree projection typically uses the lon range of -180 to 180
print('raw lonlat limit: ', np.min(lon), np.max(lon), np.min(lat), np.max(lat))
if abs(np.max(lon) - 360.) < 10.:
    lon[lon>180] = lon[lon>180] - 360.
    lon_offset = 0.
else:
    lon_offset = 180.
lon = lon - lon_offset
print('new lonlat limit: ', np.min(lon), np.max(lon), np.min(lat), np.max(lat))
[nlat, nlon] = np.shape(lon)

RHlevs=np.arange(500,701,25)
print(RHlevs)
for ind, lv in enumerate(RHlevs):
    levstr= str(lv)+' mb'
    print('Extracting RH at '+levstr)
    rh = grb.select(shortName='RH', level=levstr)[0].data()
    rh.data[rh.mask] = np.nan
    rh[rh<0.] = np.nan
    rh = np.asarray(rh)
    if ind == 0:
        rhtmp=np.zeros((len(RHlevs),rh.shape[0],rh.shape[1]))
        print(rhtmp.shape)
        rhtmp[ind,:,:]=rh
    rhtmp[ind,:,:]=rh
print(rhtmp.shape)

rhave = np.mean(rhtmp,axis=0)
print(rhave.shape)

levstr='700 mb'
print('Extracting HGT, UGRD, VGRD, at '+levstr)
hgt = grb.select(shortName='HGT', level=levstr)[0].data()
hgt.data[hgt.mask] = np.nan
hgt = np.asarray(hgt) * 0.1 # convert meter to decameter
hgt = gaussian_filter(hgt, 5)

ugrd = grb.select(shortName='UGRD', level=levstr)[0].data()
ugrd.data[ugrd.mask] = np.nan
ugrd = np.asarray(ugrd) * 1.94384 # convert m/s to kt

vgrd = grb.select(shortName='VGRD', level=levstr)[0].data()
vgrd.data[vgrd.mask] = np.nan
vgrd = np.asarray(vgrd) * 1.94384 # convert m/s to kt

#===================================================================================================
print('Plotting HGT, RH, UGRD, VGRD, at '+levstr)
fig_prefix = conf['stormName'].upper()+conf['stormID'].upper()+'.'+conf['ymdh']+'.'+conf['stormModel']

# Set default figure parameters
mpl.rcParams['figure.figsize'] = [8, 8]
mpl.rcParams["figure.dpi"] = 150
mpl.rcParams['axes.titlesize'] = 8
mpl.rcParams['axes.labelsize'] = 8
mpl.rcParams['xtick.labelsize'] = 8
mpl.rcParams['ytick.labelsize'] = 8
mpl.rcParams['legend.fontsize'] = 8

if conf['stormDomain'] == 'storm':
    mpl.rcParams['figure.figsize'] = [6, 6]
    fig_name = fig_prefix+'.storm.'+'rhmidlev_hgt_wind.'+conf['fhhh'].lower()+'.png'
    cbshrink = 1.0
    lonmin = lon[int(nlat/2), int(nlon/2)]-3
    lonmax = lon[int(nlat/2), int(nlon/2)]+3
    lonint = 2.0
    latmin = lat[int(nlat/2), int(nlon/2)]-3
    latmax = lat[int(nlat/2), int(nlon/2)]+3
    latint = 2.0
    skip = 20
    wblength = 4.5
else:
    mpl.rcParams['figure.figsize'] = [8, 5.4]
    fig_name = fig_prefix+'.'+'rhmidlev_hgt_wind.'+conf['fhhh'].lower()+'.png'
    cbshrink = 1.0
    lonmin = np.min(lon)
    lonmax = np.max(lon)
    lonint = 10.0
    latmin = np.min(lat)
    latmax = np.max(lat)
    latint = 10.0
    skip = round(nlon/360)*10
    wblength = 4
   #skip = 40

cslevels=np.arange(210,330,3)

myproj = ccrs.PlateCarree(lon_offset)
transform = ccrs.PlateCarree(lon_offset)

# create figure and axes instances
fig = plt.figure()
ax = plt.axes(projection=myproj)
ax.axis('equal')

cflevels = [0,5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,99]
cfcolors = ['#996515','#a3742c','#ad8444','#b8935b','#c2a373','#ccb28a','#d6c1a1','#e0d1b9','#ebe0d0','#f5f0e8', # Brown https://colorswall.com/palette/26287
            '#ffffff','#d1e6cf','#bbdab7','#a4ce9f','#8dc287','#76b56e','#5fa956','#499d3e','#329026','#1b840e','#008000'] # Green https://colorswall.com/palette/1386
#           '#ffffff','#cce0cc','#b3d1b3','#99c199','#80b280','#66a266','#4d934d','#338333','#197419','#006400','#005000'] # Green https://colorswall.com/palette/1452

cf = ax.contourf(lon, lat, rhave, levels=cflevels, colors=cfcolors, extend='max', transform=transform)
cb = plt.colorbar(cf, orientation='vertical', pad=0.02, aspect=50, extend='max', extendfrac='auto', shrink=cbshrink, extendrect=True, ticks=cflevels)

wb = ax.barbs(lon[::skip,::skip], lat[::skip,::skip], ugrd[::skip,::skip], vgrd[::skip,::skip],
              length=wblength, linewidth=0.2, color='black', transform=transform)

try:
    cs = ax.contour(lon, lat, hgt, levels=cslevels, colors='black', linewidths=0.6, transform=transform)
    lb = plt.clabel(cs, levels=cslevels, inline_spacing=1, fmt='%d', fontsize=8)
except:
    print('ax.contour failed, continue anyway')

# Add borders and coastlines
#ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor='whitesmoke')
ax.add_feature(cfeature.BORDERS.with_scale('50m'), linewidth=0.3, facecolor='none', edgecolor='0.1')
ax.add_feature(cfeature.STATES.with_scale('50m'), linewidth=0.3, facecolor='none', edgecolor='0.1')
ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=0.3, facecolor='none', edgecolor='0.1')

#gl = ax.gridlines(crs=transform, draw_labels=True, linewidth=0.3, color='0.1', alpha=0.6, linestyle=(0, (5, 10)))
gl = ax.gridlines(draw_labels=True, linewidth=0.3, color='0.1', alpha=0.6, linestyle=(0, (5, 10)))
gl.top_labels = False
gl.right_labels = False
gl.xlocator = mticker.FixedLocator(np.arange(-180., 180.+1, lonint))
gl.ylocator = mticker.FixedLocator(np.arange(-90., 90.+1, latint))
gl.xlabel_style = {'size': 8, 'color': 'black'}
gl.ylabel_style = {'size': 8, 'color': 'black'}

print('lonlat limits: ', [lonmin, lonmax, latmin, latmax])
ax.set_extent([lonmin, lonmax, latmin, latmax], crs=transform)

title_center = '700-500 hPa Mean RH (%, shaded), '+'700 hPa Height (dam), Wind (kt)'
ax.set_title(title_center, loc='center', y=1.05)
title_left = conf['stormModel']+' '+conf['stormName']+conf['stormID']
ax.set_title(title_left, loc='left')
title_right = conf['initTime'].strftime('Init: %Y%m%d%HZ ')+conf['fhhh'].upper()+conf['validTime'].strftime(' Valid: %Y%m%d%HZ')
ax.set_title(title_right, loc='right')

#plt.show()
plt.savefig(fig_name, bbox_inches='tight')
plt.close(fig)
