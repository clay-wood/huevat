"""Measure common warmed operations; no generation or performance pass claims."""
import argparse
import json
from pathlib import Path
import platform
import statistics
import time
import tracemalloc

import huevat as hv


def measure(operation, number):
    values=[]
    for _ in range(5):
        start=time.perf_counter()
        for _ in range(number):operation()
        values.append((time.perf_counter()-start)/number)
    return statistics.median(values)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--compare',type=Path);parser.add_argument('--legacy',action='store_true');args=parser.parse_args()
    spectral,gradient=hv.spectral,hv.gradient
    if args.legacy:
        from huevat.families import spectral
        from huevat.catalog import gradient
    s=spectral();g=gradient('strata');s.report;g.report;s.discrete(7)
    from huevat.adapters._common import checked
    operations={'spectral_lookup':spectral,'spectral_reverse':s.reversed,'spectral_report':lambda:s.report,
        'spectral_adapter_check':lambda:checked(s,hv.Gradient),'spectral_7_bins':lambda:s.discrete(7),
        'named_lookup':lambda:gradient('strata'),'named_report':lambda:g.report,
        'compact_export':lambda:hv.export(s),'scalar_4096':lambda:[s.at(i/4095) for i in range(4096)]}
    values={k:measure(f,1 if k=='scalar_4096' else 20) for k,f in operations.items()}
    tracemalloc.start();views=[s.reversed() for _ in range(25)]
    retained,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    record={'python':platform.python_version(),'host':platform.platform(),'seconds':values,'legacy':args.legacy,
            'reverse_25_views_traced_bytes':{'retained':retained,'peak':peak},
            'method':'five warmed medians; immutable report caches primed; first audit access is still a separate cost'}
    if args.compare:
        before=json.loads(args.compare.read_text());before=before.get('seconds',before)
        record['comparison']={k:{'before_ms':1000*before[k],'after_ms':1000*v,'speedup':before[k]/v} for k,v in values.items()}
    path=Path('artifacts/runtime-profile-legacy.json' if args.legacy else 'artifacts/runtime-profile.json');path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(record,indent=2))


if __name__=='__main__':main()
