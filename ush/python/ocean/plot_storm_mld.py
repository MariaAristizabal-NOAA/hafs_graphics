"""

 plot_storm_mld.py
 -------------
    read a HYCOM 3z .nc file,
    extract footprint MLD and plot in time series (R<=500km)


 ************************************************************************
 usage: python plot_storm_mld.py stormModel stormName stormID YMDH trackon COMhafs graphdir
 -----
 ************************************************************************


 HISTORY
 -------
    modified to implement new filenames and hycom domains, as well as
        improve graphics -JS & MA 06/2022
    modified to comply the convention of number of input argument and 
       graphic filename. -hsk 8/2020
    modified to take global varibles from kick_graphics.py -hsk 9/20/2018
    modified to fit for RT run by Hyun-Sook Kim 5/17/2017
    edited by Hyun-Sook Kim 9/18/2015
    modified by Hyun-Sook Kim 11/18/2016
---------------------------------------------------------------
"""

from utils4HWRF import readTrack6hrly
from geo4HYCOM import haversine

import os
import sys
import glob
import xarray as xr
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

import cartopy
import cartopy.crs as ccrs
import cartopy.feature as cfeature

plt.switch_backend('agg')

#================================================================
model = sys.argv[1]
storm = sys.argv[2]
tcid = sys.argv[3]
cycle = sys.argv[4]
trackon = sys.argv[5]
COMOUT = sys.argv[6]
graphdir = sys.argv[7]

if not os.path.isdir(graphdir):
      p=Path(graphdir)
      p.mkdir(parents=True)

print("code:   plot_storm_mld.py")

atcf = COMOUT+'/' + tcid + '.' + cycle + '.' + model + '.trak.atcfunix'

adt,aln,alt,pmn,vmx = readTrack6hrly(atcf)
#aln_hycom = np.asarray([ln+360 if ln<74.16 else ln for ln in aln])
#alt_hycom = alt

# Set Cartopy data_dir location
cartopy.config['data_dir'] = os.getenv('cartopyDataDir')

#   ------------------------------------------------------------------------------------
Rkm=500    # search radius [km]

# - get SST  *_3z_*.[nc] files
afiles = sorted(glob.glob(os.path.join(COMOUT,'*3z*.nc')))

ncfile0 = xr.open_dataset(afiles[0])

var0 = ncfile0['mixed_layer_thickness']
lon = np.asarray(ncfile0.Longitude)
lat = np.asarray(ncfile0.Latitude)

var_name = 'mld'
units = '(m)'

lns,lts = np.meshgrid(lon,lat)
dummy = np.ones(lns.shape)

#if np.logical_or(np.min(lon) > 0,np.max(lon) > 360):
#    aln = aln_hycom
#    alt = alt_hycom

count = len(adt)        
for k in range(count):

    if alt[k] < (np.max(lat)+5.0):
        dR=haversine(lns,lts,aln[k],alt[k])/1000.
        dumb=dummy.copy()
        dumb[dR>Rkm]=np.nan
         
        ncfile = xr.open_dataset(afiles[k])

        varr = ncfile['mixed_layer_thickness']
        var = np.asarray(varr[0])*dumb
        dvar = np.asarray(varr[0]-np.squeeze(var0))*dumb

        # define forecast hour
        fhr=k*6
        
        # create figure and axes instances
        fig = plt.figure(figsize=(6,6))
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.axis('scaled')
        
        cflevels = np.linspace(0, 100, 21)
        cmap = plt.get_cmap('RdYlBu_r')
        cf = ax.contourf(lon, lat, var, levels=cflevels, cmap=cmap, extend='max', transform=ccrs.PlateCarree())
        ax.contour(lon, lat, var, cflevels, colors='grey',alpha=0.5, transform=ccrs.PlateCarree())
        cb = plt.colorbar(cf, orientation='vertical', pad=0.02, aspect=30, shrink=0.75, extendrect=True, ticks=cflevels[::4])
        cb.ax.tick_params(labelsize=8)
        if trackon[0].lower()=='y':
              plt.plot(aln,alt,'-ok',linewidth=3,alpha=0.6,markersize=2)
              plt.plot(aln[k],alt[k],'ok',markerfacecolor='none',markersize=10,alpha=0.6)
        mnmx="(min,max)="+"(%6.1f"%np.nanmin(var)+","+"%6.1f)"%np.nanmax(var)
        plt.text(aln[k]-2.15,alt[k]-4.75,mnmx,fontsize=8,color='DarkOliveGreen',fontweight='bold',bbox=dict(boxstyle="round",color='w',alpha=0.5))
        plt.axis([aln[k]-5.5,aln[k]+5.5,alt[k]-5,alt[k]+5])
     
        # Add gridlines and labels
        #gl = ax.gridlines(crs=transform, draw_labels=True, linewidth=0.3, color='0.1', alpha=0.6, linestyle=(0, (5, 10)))
        gl = ax.gridlines(draw_labels=True, linewidth=0.3, color='0.1', alpha=0.6, linestyle=(0, (5, 10)))
        gl.top_labels = False
        gl.right_labels = False
        gl.xlocator = mticker.FixedLocator(np.arange(-180., 180.+1, 2))
        gl.ylocator = mticker.FixedLocator(np.arange(-90., 90.+1, 2))
        gl.xlabel_style = {'size': 8, 'color': 'black'}
        gl.ylabel_style = {'size': 8, 'color': 'black'}
        
        # Add borders and coastlines
        #ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor='whitesmoke')
        ax.add_feature(cfeature.BORDERS.with_scale('50m'), linewidth=0.3, facecolor='none', edgecolor='0.1')
        ax.add_feature(cfeature.STATES.with_scale('50m'), linewidth=0.3, facecolor='none', edgecolor='0.1')
        ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=0.3, facecolor='none', edgecolor='0.1')
     
        title_center = 'Mixed Layer Depth (m)'
        ax.set_title(title_center, loc='center', y=1.05, fontsize=8)
        title_left = model.upper()+' '+storm.upper()+tcid.upper()
        ax.set_title(title_left, loc='left', fontsize=8)
        title_right = 'Init: '+cycle+'Z '+'F'+"%03d"%(fhr)
        ax.set_title(title_right, loc='right', fontsize=8)
      
        pngFile=os.path.join(graphdir,storm.upper()+tcid.upper()+'.'+cycle+'.'+model.upper()+'.ocean.storm.'+var_name+'.f'+"%03d"%(fhr)+'.png')
        plt.savefig(pngFile,bbox_inches='tight',dpi=150)
        plt.close("all")
     
        # create figure and axes instances for change plot
        fig = plt.figure(figsize=(6,6))
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.axis('scaled')
     
        cflevels = np.linspace(-30, 30, 31)
        cmap = plt.get_cmap('RdBu_r')
        cf = ax.contourf(lon, lat, dvar, levels=cflevels, cmap=cmap, extend='both', transform=ccrs.PlateCarree())
        ax.contour(lon, lat, dvar, cflevels[::2], colors='grey',alpha=0.5, transform=ccrs.PlateCarree())
        cb = plt.colorbar(cf, orientation='vertical', pad=0.02, aspect=30, shrink=0.75, extendrect=True, ticks=cflevels[::5])
        cb.ax.tick_params(labelsize=8)
        if trackon[0].lower()=='y':
              plt.plot(aln,alt,'-ok',linewidth=3,alpha=0.6,markersize=2)
              plt.plot(aln[k],alt[k],'ok',markerfacecolor='none',markersize=10,alpha=0.6)
        mnmx="(min,max)="+"(%6.1f"%np.nanmin(dvar)+","+"%6.1f)"%np.nanmax(dvar)
        plt.text(aln[k]-2.15,alt[k]-4.75,mnmx,fontsize=8,color='DarkOliveGreen',fontweight='bold',bbox=dict(boxstyle="round",color='w',alpha=0.5))
        plt.axis([aln[k]-5.5,aln[k]+5.5,alt[k]-5,alt[k]+5])
     
        # Add gridlines and labels
     #  gl = ax.gridlines(crs=transform, draw_labels=True, linewidth=0.3, color='0.1', alpha=0.6, linestyle=(0, (5, 10)))
        gl = ax.gridlines(draw_labels=True, linewidth=0.3, color='0.1', alpha=0.6, linestyle=(0, (5, 10)))
        gl.top_labels = False
        gl.right_labels = False
        gl.xlocator = mticker.FixedLocator(np.arange(-180., 180.+1, 2))
        gl.ylocator = mticker.FixedLocator(np.arange(-90., 90.+1, 2))
        gl.xlabel_style = {'size': 8, 'color': 'black'}
        gl.ylabel_style = {'size': 8, 'color': 'black'}
     
        # Add borders and coastlines
        #ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor='whitesmoke')
        ax.add_feature(cfeature.BORDERS.with_scale('50m'), linewidth=0.3, facecolor='none', edgecolor='0.1')
        ax.add_feature(cfeature.STATES.with_scale('50m'), linewidth=0.3, facecolor='none', edgecolor='0.1')
        ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=0.3, facecolor='none', edgecolor='0.1')
     
        title_center = 'Mixed Layer Depth Change (m)'
        ax.set_title(title_center, loc='center', y=1.05, fontsize=8)
        title_left = model.upper()+' '+storm.upper()+tcid.upper()
        ax.set_title(title_left, loc='left', fontsize=8)
        title_right = 'Init: '+cycle+'Z '+'F'+"%03d"%(fhr)
        ax.set_title(title_right, loc='right', fontsize=8)
     
        pngFile=os.path.join(graphdir,storm.upper()+tcid.upper()+'.'+cycle+'.'+model.upper()+'.ocean.storm.'+var_name+'.change.f'+"%03d"%(fhr)+'.png')
        plt.savefig(pngFile,bbox_inches='tight',dpi=150)
        plt.close("all")

# --- successful exit
sys.exit(0)

