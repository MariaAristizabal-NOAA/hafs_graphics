#!/usr/bin/env python3

"""This script is to plot out HAFS temperature anomaly, geopotential height and wind."""

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

levstr=str(conf['standardLayer'])+' mb'
print('Extracting TMP, HGT, UGRD, VGRD, at '+levstr)
hgt = grb.select(shortName='HGT', level=levstr)[0].data()
hgt.data[hgt.mask] = np.nan
hgt = np.asarray(hgt) * 0.1 # convert meter to decameter
hgt = gaussian_filter(hgt, 5)

tmp = grb.select(shortName='TMP', level=levstr)[0].data()
tmp.data[tmp.mask] = np.nan
tmp[tmp<0.] = np.nan
tmp = np.asarray(tmp) - 273.15
#tmp = gaussian_filter(tmp, 2)

print('Calculate temperature anomaly at'+levstr)
tmp_mean = np.nanmean(tmp)
tmp_anomaly = tmp - tmp_mean

ugrd = grb.select(shortName='UGRD', level=levstr)[0].data()
ugrd.data[ugrd.mask] = np.nan
ugrd = np.asarray(ugrd) * 1.94384 # convert m/s to kt

vgrd = grb.select(shortName='VGRD', level=levstr)[0].data()
vgrd.data[vgrd.mask] = np.nan
vgrd = np.asarray(vgrd) * 1.94384 # convert m/s to kt

#===================================================================================================
print('Plotting HGT, TMP anomaly, UGRD, VGRD, at '+levstr)
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
    fig_name = fig_prefix+'.storm.'+'tempanomaly_hgt_wind.'+str(conf['standardLayer'])+'mb.'+conf['fhhh'].lower()+'.png'
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
    fig_name = fig_prefix+'.'+'tempanomaly_hgt_wind.'+str(conf['standardLayer'])+'mb.'+conf['fhhh'].lower()+'.png'
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

if conf['standardLayer'] == 200:
    cslevels=np.arange(1080,1290,12)
elif conf['standardLayer'] == 300:
    cslevels=np.arange(780,1020,12)
elif conf['standardLayer'] == 500:
    cslevels=np.arange(480,600,6)
elif conf['standardLayer'] == 700:
    cslevels=np.arange(210,330,3)
elif conf['standardLayer'] == 850:
    cslevels=np.arange(60,180,3)
else:
    cslevels=np.arange(-50,4000,5)

myproj = ccrs.PlateCarree(lon_offset)
transform = ccrs.PlateCarree(lon_offset)

# create figure and axes instances
fig = plt.figure()
ax = plt.axes(projection=myproj)
ax.axis('equal')

#cflevels = [-12.,-10.,-8.,-6.,-4.,-2.,0.,2.,4.,6.,8.,10.,12.]
#cfcolors = ['darkblue','mediumblue','dodgerblue','deepskyblue','lightskyblue','aliceblue',
#            'seashell','peachpuff','salmon','tomato','red','firebrick','darkred']
#cflevels = [-32.,-16.,-8.,-4.,-2.,-1.,0.,1.,2.,4.,8.,16.,32.]

#cflevels = [-16.,-12.,-8.,-4.,-2.,-1.,0.,1.,2.,4.,8.,12.,16.]
#cfcolors = ['darkblue','mediumblue','dodgerblue','deepskyblue','lightskyblue','white',
#            'white','salmon','tomato','red','firebrick','darkred']
#cf = ax.contourf(lon, lat, tmp_anomaly, levels=cflevels, colors=cfcolors, extend='both', transform=transform)
#cb = plt.colorbar(cf, orientation='vertical', pad=0.02, aspect=50, shrink=cbshrink, extendrect=True, ticks=cflevels)

cflevels = np.arange(-16,17,1)
ticks = np.arange(-16,17,2)
cmap = 'RdBu_r'

cf = ax.contourf(lon, lat, tmp_anomaly, levels=cflevels, cmap=cmap, extend='both', transform=transform)
cb = plt.colorbar(cf, orientation='vertical', pad=0.02, aspect=50, shrink=cbshrink, extendrect=True, ticks=ticks)

#cflevels = np.linspace(-20.,20.,41)
#cmap = plt.get_cmap('bwr')
#cf = ax.contourf(lon, lat, tmp_anomaly, levels=cflevels, cmap=cmap, extend='both', transform=transform)
#cb = plt.colorbar(cf, orientation='vertical', pad=0.02, aspect=50, shrink=cbshrink, extendrect=True)

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

title_center = str(conf['standardLayer'])+' hPa Temperature Anomaly (${^{o}}$C, shaded), Height (dam), Wind (kt)'
ax.set_title(title_center, loc='center', y=1.05)
title_left = conf['stormModel']+' '+conf['stormName']+conf['stormID']
ax.set_title(title_left, loc='left')
title_right = conf['initTime'].strftime('Init: %Y%m%d%HZ ')+conf['fhhh'].upper()+conf['validTime'].strftime(' Valid: %Y%m%d%HZ')
ax.set_title(title_right, loc='right')

#plt.show()
plt.savefig(fig_name, bbox_inches='tight')
#plt.close(fig)
