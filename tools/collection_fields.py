"""Deterministic synthetic application fields, with explicit physical semantics."""
import numpy as np


def seismic(nx=128,nt=384):
    x=np.linspace(0,12,nx);t=np.linspace(0,2.4,nt);dt=t[1]-t[0]
    reflectivity=np.zeros((nt,nx));fault=(x>=6)*.12
    horizons=[(.55+.018*x+fault,.85),(.95+.024*x+fault,-.70),
              (1.36+.010*x+fault,.16),(1.378+.010*x+fault,-.16),
              (1.91-.020*x+.02*np.sin(x)+fault,.045)]
    for times,amplitude in horizons:
        indices=np.rint(times/dt).astype(int)
        reflectivity[indices,np.arange(nx)]+=amplitude
    half_width=int(np.ceil(.08/dt));tw=np.arange(-half_width,half_width+1)*dt;frequency=25.
    a=(np.pi*frequency*tw)**2;wavelet=(1-2*a)*np.exp(-a)
    amplitudes=np.column_stack([np.convolve(reflectivity[:,i],wavelet,mode='same') for i in range(nx)])
    return {'x':x,'time':t,'data':amplitudes,'reflectivity':reflectivity,'wavelet':wavelet,'wavelet_time':tw,
            'wavelet_frequency_hz':frequency,'vmin':-1.,'vmax':1.,'center':0.,
            'x_unit':'km','time_unit':'s two-way time','amplitude_unit':'arbitrary signed amplitude',
            'positive_polarity':'positive reflectivity gives the positive central Ricker lobe',
            'thin_bed_separation_s':.018,'fault_x_km':6.,'fault_time_offset_s':.12,'synthetic':True}


def structure(nx=160,ny=112):
    x,z=np.meshgrid(np.linspace(0,12,nx),np.linspace(0,5,ny))
    velocity=2.+.50*z+.28*(z>2+.08*x)+.04*np.exp(-((x-8)**2+(z-3.4)**2)/.12)
    return {'x':x,'depth':z,'data':velocity,'vmin':2.,'vmax':5.,'unit':'km/s',
            'normalization':'linear','weak_anomaly_km_s':.04,'synthetic':True}


def terrain(nx=160,ny=120):
    x,y=np.meshgrid(np.linspace(0,80,nx),np.linspace(0,60,ny))
    coast=x-30+4*np.sin(y/8)
    elevation=40*coast+1600*np.exp(-((x-56)**2/110+(y-30)**2/180))
    elevation-=2100*np.exp(-((x-6)**2/130+(y-30)**2/320))
    elevation[:12,-16:]=np.nan
    return {'x':x,'y':y,'data':elevation,'sea_level_m':0.,'water_depth_range_m':(0.,4000.),
            'land_elevation_range_m':(0.,3000.),'unit':'m relative to sea level','missing':'NaN patch',
            'combined_profile_screened':False,'hillshade_profile_screened':False,'synthetic':True}


def atmosphere(nx=160,ny=112):
    x,y=np.meshgrid(np.linspace(0,1000,nx),np.linspace(0,700,ny))
    ridge=np.exp(-((y-340-80*np.sin(x/180))**2/9000))
    moisture=1.+15*ridge*np.exp(-((x-520)/650)**2)
    concentration=.01+90*np.exp(-((x-360)**2/22000+(y-310)**2/12000))
    concentration+=.05*np.exp(-((x-750)**2/8000+(y-520)**2/6000))
    concentration[:8,:18]=0.  # Explicit no-signal region; log display masks it.
    anomaly=4*np.exp(-((x-650)**2/36000+(y-330)**2/25000))-3*np.exp(-((x-300)**2/42000+(y-360)**2/25000))
    for field in (moisture,concentration,anomaly):field[-12:,-15:]=np.nan
    return {'x':x,'y':y,'moisture':moisture,'concentration':concentration,'anomaly':anomaly,
        'moisture_range':(0.,18.),'moisture_unit':'g/kg','concentration_range':(.01,100.),
        'concentration_unit':'arbitrary concentration units','concentration_normalization':'log10',
        'nonpositive_policy':'masked separately as no signal; missing cells remain distinct',
        'anomaly_range':(-4.,4.),'anomaly_center':0.,'anomaly_unit':'K','synthetic':True}
