"""Declared H4b aesthetic controls; no optional dependencies or generated data."""
VERSION = 'h4b-free-knots-v1'


def sequential(label, route, domains, hues, chroma, knots, skew=0., orientation='background'):
    return dict(label=label,route=route,family='sequential',domains=domains,hues=hues,
                chroma=chroma,knots=knots,skew=skew,orientation=orientation)


def diverging(label, route, domains, left, right, chroma, skew=0.):
    return dict(label=label,route=route,family='diverging',domains=domains,
                left=left,right=right,chroma=chroma,knots=[0.,.02,.20,.45,.72,1.],
                skew=skew,orientation='negative-left / positive-right')


SPECS = {
    'ink': sequential('Ink','indigo – blue – ice',['general'],
        [280,275,260,245,225,220],[.030,.075,.130,.130,.080,.018],
        [0.,.15,.35,.60,.82,1.],.08),
    'lagoon': sequential('Lagoon','navy – teal – mint',['general','atmosphere'],
        [265,245,210,185,165,150],[.025,.070,.110,.110,.070,.020],
        [0.,.12,.33,.58,.82,1.],-.10),
    'rosewood': sequential('Rosewood','plum – rose – sand',['general'],
        [315,325,345,375,410,430],[.025,.065,.100,.120,.090,.025],
        [0.,.17,.39,.63,.84,1.],.12),
    'ember': sequential('Ember','charcoal – rust – amber – cream',['general','structure'],
        [25,30,40,55,75,90],[.020,.060,.110,.130,.080,.025],
        [0.,.13,.36,.61,.84,1.],-.06),
    'mineral': sequential('Mineral','slate – violet – blue – pale green',['structure','general'],
        [300,285,260,235,200,155],[.025,.075,.110,.100,.060,.018],
        [0.,.18,.40,.62,.85,1.],-.14),
    'bathymetry': sequential('Bathymetry','ice – azure – deep navy',['geography'],
        [280,265,250,230,205,190],[.030,.070,.115,.110,.060,.018],
        [0.,.13,.34,.58,.81,1.],.03,'depth-darkens'),
    'highland': sequential('Highland','forest – olive – ochre – stone',['geography'],
        [155,145,125,100,85,75],[.035,.060,.080,.100,.065,.015],
        [0.,.16,.38,.62,.83,1.],-.06,'elevation-lightens'),
    'aerosol': sequential('Aerosol','midnight plum – rose – amber',['atmosphere'],
        [285,305,330,380,420,435],[.025,.070,.100,.100,.065,.020],
        [0.,.15,.37,.60,.82,1.],.10),
    'balance': diverging('Balance','blue – neutral – coral',['general','seismic'],
        [250,250,255,255,250,250],[75,75,70,60,45,30],
        [0.,.003,.055,.090,.125,.125],.02),
    'estuary': diverging('Estuary','green teal – neutral – plum',['general','atmosphere'],
        [145,145,150,155,170,180],[315,315,315,315,320,325],
        [0.,.003,.055,.095,.115,.090],-.04),
    'strata': diverging('Strata','indigo – neutral – ochre',['seismic','structure'],
        [270,270,275,280,285,285],[90,90,90,85,80,75],
        [0.,.003,.055,.090,.115,.120],.08),
    'thermal': diverging('Thermal','slate blue – neutral – rose',['atmosphere','general'],
        [240,240,240,245,245,245],[70,70,65,50,35,15],
        [0.,.003,.055,.090,.105,.085],-.08),
}
SPECS['estuary']['dark_endpoint_factor']=.9
SPECS['thermal']['dark_endpoint_factor']=.85
SPECS['balance']['arm_offset_power']=1
