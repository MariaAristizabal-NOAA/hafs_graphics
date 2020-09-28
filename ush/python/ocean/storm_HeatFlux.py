"""

 storm_HeatFlux.py
 -----------------
    read a set of FV3 phyf*.nc file,
    extract latent heat fluxs,
    and reurn a series of graphics.


 *********************************************************************************
 usage: python storm_HeatFlux.py stormModel stormName stormID YMDH trackon COMhafs
 -----
 *********************************************************************************

 HISTORY
 -------
    modified to comply the convention of number of input argument and
       graphic filename. -hsk 8/2020
    modified so to read in a set of phyf*.nc files. -hsk 7/17/2020
    modified to take global varibles from kick_graphics.py -hsk 9/20/2018
    modified to fit for RT run by Hyun-Sook Kim 5/17/2017
    edited by Hyun-Sook Kim 9/18/2015
    modified by Hyun-Sook Kim 11/18/2016
---------------------------------------------------------------
"""

from utils4HWRF import readTrack, readTrack6hrly
from utils import coast180
from geo4HYCOM import haversine

import os, shutil
import sys
import glob
import xarray as xr

from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
  
from pathlib import Path

import socket

#plt.switch_backend('agg')

def ZoomIndex(var,aln,alt):
   """ find indices of the lower-left corner and the upper-right corner 
       of an area encompassing the predicted storm track.

       var: an xarray with longitude and latitude coordinate names
       aln,alt: a set of predicted TC locations (longitude,latitude).
   """

   # find an index for the lower-left corner
   abslat=np.abs(var.latitude-min(alt)-18)
   abslon=np.abs(var.longitude-min(aln)-18)
   c=np.maximum(abslon,abslat)
   ([xll],[yll])=np.where(c==np.min(c))

   # find an index for the upper-right corner
   abslon=np.abs(var.longitude-max(aln)+18)
   abslat=np.abs(var.latitude-max(alt)+18)
   c=np.maximum(abslon,abslat)
   ([xur],[yur])=np.where(c==np.min(c))

   xindx=np.arange(min(xll,xur),max(xll,xur),1)
   yindx=np.arange(min(yll,yur),max(yll,yur),1)
   
   return (xindx,yindx)

#================================================================
model =sys.argv[1]
storm = sys.argv[2]
tcid = sys.argv[3]
cycle = sys.argv[4]
trackon = sys.argv[5]
COMOUT = sys.argv[6]

graphdir = sys.argv[7]
if not os.path.isdir(graphdir):
      p=Path(graphdir)
      p.mkdir(parents=True)

print("code:   storm_HeatFlux.py")

cx,cy=coast180()
if tcid[-1].lower() == 'l' or tcid[-1].lower() == 'e' or tcid[-1].lower() == 'c':
    cx=cx+360

if tcid[-1].lower()=='l':
   nprefix=model.lower()+tcid.lower()+'.'+cycle+'.hafs_hycom_hat10'
if tcid[-1].lower()=='e':
   nprefix=model.lower()+tcid.lower()+'.'+cycle+'.hafs_hycom_hep20'
if tcid[-1].lower()=='w':
   nprefix=model.lower()+tcid.lower()+'.'+cycle+'.hafs_hycom_hwp30'
if tcid[-1].lower()=='c':
   nprefix=model.lower()+tcid.lower()+'.'+cycle+'.hafs_hycom_hcp70'

aprefix=storm.lower()+tcid.lower()+'.'+cycle
atcf = os.path.join(COMOUT,aprefix+'.trak.'+model.lower()+'.atcfunix')

# ------------------------------------------------------------------------------------
# - preprocessing: subset and convert wgrib2 to netcdf

#
Rkm=500 	# search radius

scrubbase='./tmp/'

part=nprefix.partition('.'+model.lower()+'_')[0]
nctmp=os.path.join(scrubbase,part)
if os.path.isdir(nctmp):
   shutil.rmtree(nctmp)
p=Path(nctmp)
p.mkdir(parents=True)

# track
adt,aln,alt,pmn,vmx=readTrack6hrly(atcf)
if tcid[-1].lower()=='l' or tcid[-1].lower()=='e':
    aln=[-1*a + 360. for a in aln]

#afiles = sorted(glob.glob(os.path.join(COMOUT,nprefix+'phyf*.nc')))
if model.lower()=='hafs':
   afiles = sorted(glob.glob(os.path.join(COMOUT,'*'+model.lower()+'prs.synoptic*.grb2')))
if model.lower()=='hwrf':
   #afiles = sorted(glob.glob(os.path.join(COMOUT,'*'+model.lower()+'prs.synoptic.*.grb2')))
   afiles = sorted(glob.glob(os.path.join(COMOUT,'*'+model.lower()+'prs.storm.*.grb2')))
if model.lower()=='hmon':
   afiles = sorted(glob.glob(os.path.join(COMOUT,'*'+model.lower()+'prs.d2.*.grb2')))

afiles=afiles[::2]   # subset to 6 hourly intervals
flxvar=':(LHTFL|SHTFL):surface:'
for k,A in enumerate(afiles):
    fhr=int(A.partition('.grb2')[0][-3:])
    if fhr==0:
      xvars=flxvar+'anl:'
    else:
      xvars=flxvar+"%g"%(fhr)
   
    ncout=os.path.join(nctmp,'heatflx_f'+"%03g"%fhr+'.nc')
    cmd='sh ./xgrb2nc.sh '+'"'+xvars+'"'+' '+A+' '+ncout
    os.system(cmd)

nfiles=sorted(glob.glob(os.path.join(nctmp,'heatflx_*.nc')))
#xnc=xr.open_mfdataset(nfiles)

#if model.lower()=='hafs':
#  xii,yii=ZoomIndex(xnc.isel(time=[0]),aln,alt)
#  xindx=xii[::2]
#  yindx=yii[::2]
#
#  var1=xnc['LHTFL_surface'].isel(longitude=xindx,latitude=yindx)
#  var2=xnc['SHTFL_surface'].isel(longitude=xindx,latitude=yindx)
#else:
#  var1=xnc['LHTFL_surface']
#  var2=xnc['SHTFL_surface']
#
#del nfiles
#del xnc

for k in range(min(len(aln),len(afiles))):
   fnc=xr.open_dataset(nfiles[k])
   var1=np.squeeze(fnc['LHTFL_surface'])
   var2=np.squeeze(fnc['SHTFL_surface'])

   lns,lts=np.meshgrid(var1['longitude'],var1['latitude'])
   dummy=np.ones(lns.shape)

   dR=haversine(lns,lts,aln[k],alt[k])/1000.0
   dumb=dummy.copy()
   dumb[dR>Rkm]=np.nan

   fhr=k*6
   
   #--- latent heat flux 
   fig=plt.figure(figsize=(19,5))
   plt.suptitle(model.upper()+': '+storm.upper()+tcid.upper()+'  '+'Ver Hr '+"%03d"%(fhr)+'  (IC='+cycle+'):  Heat Flux [W/m$^2$]',fontsize=15)
   plt.subplot(131)
   (var1*dumb).plot.contourf(levels=np.arange(0,850,50),cmap='RdBu_r')
   plt.plot(cx,cy,color='gray')
   if trackon[0].lower()=='y':
        plt.plot(aln,alt,'-ok',linewidth=3,alpha=0.6,markersize=2)
        plt.plot(aln[k],alt[k],'ok',markerfacecolor='none',markersize=10,alpha=0.6)
   mnmx="(min,max)="+"(%6.1f"%np.nanmax(var1*dumb)+","+"%6.1f)"%np.nanmin(var1*dumb)
   plt.text(aln[k]-5.2,alt[k]+4.3,'(A) Latent',fontsize=14,fontweight='bold')
   plt.text(aln[k]-4.25,alt[k]-4.75,mnmx,fontsize=14,color='DarkOliveGreen',fontweight='bold')
   plt.axis([aln[k]-5.5,aln[k]+5.5,alt[k]-5,alt[k]+5])

   plt.subplot(132)
   #--- sensible heat flux
   (var2*dumb).plot.contourf(levels=np.arange(-50,275,25),cmap='RdBu_r')
   plt.plot(cx,cy,color='gray')
   if trackon[0].lower()=='y':
        plt.plot(aln,alt,'-ok',linewidth=3,alpha=0.6,markersize=2)
        plt.plot(aln[k],alt[k],'ok',markerfacecolor='none',markersize=10,alpha=0.6)
   mnmx="(min,max)="+"(%6.1f"%np.nanmax(var2*dumb)+","+"%6.1f)"%np.nanmin(var2*dumb)
   plt.text(aln[k]-5.2,alt[k]+4.3,'(B) Sensible',fontsize=14,fontweight='bold')
   plt.text(aln[k]-4.25,alt[k]-4.75,mnmx,fontsize=14,color='r',fontweight='bold')
   plt.axis([aln[k]-5.5,aln[k]+5.5,alt[k]-5,alt[k]+5])

   # --- total heat flux
   plt.subplot(133)
   var0=var1+var2
   (var0*dumb).plot.contourf(levels=np.arange(0,1150,50),cmap='RdBu_r')
   plt.plot(cx,cy,color='gray')
   if trackon[0].lower()=='y':
        plt.plot(aln,alt,'-ok',linewidth=3,alpha=0.6,markersize=2)
        plt.plot(aln[k],alt[k],'ok',markerfacecolor='none',markersize=10,alpha=0.6)
   mnmx="(min,max)="+"(%6.1f"%np.nanmax(var0*dumb)+","+"%6.1f)"%np.nanmin(var0*dumb)
   plt.text(aln[k]-5.2,alt[k]+4.3,'(C) (A)+(B)',fontsize=14,fontweight='bold')
   plt.text(aln[k]-4.25,alt[k]-4.75,mnmx,fontsize=14,color='DarkOliveGreen',fontweight='bold')
   plt.axis([aln[k]-5.5,aln[k]+5.5,alt[k]-5,alt[k]+5])

   pngFile=os.path.join(graphdir,aprefix.upper()+'.'+model.upper()+'.storm.HeatFlux.f'+"%03d"%(fhr)+'.png')
   plt.savefig(pngFile,bbox_inches='tight')

   plt.close('all')

# remove temporary directory
#shutil.rmtree(nctmp)

# --- successful exit
sys.exit(0)
#end of script


