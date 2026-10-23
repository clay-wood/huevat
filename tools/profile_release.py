"""Small host-specific release measurements; no timing acceptance threshold."""
import json
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = '''
import json,time,sys,tracemalloc
t=time.perf_counter();import huevat as h
import_s=time.perf_counter()-t
tracemalloc.start();t=time.perf_counter();ids=h.design_ids();discovery_s=time.perf_counter()-t
discovery_peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
identifier=h.design_ids(family='sequential',background='light',role='default')[0]
t=time.perf_counter();g=h.get_design(identifier);first_s=time.perf_counter()-t
t=time.perf_counter()
for _ in range(1000):h.get_design(identifier)
cached_s=(time.perf_counter()-t)/1000
t=time.perf_counter();out=h.export(g);export_s=time.perf_counter()-t
print(json.dumps(dict(import_s=import_s,discovery_s_traced=discovery_s,discovery_peak_bytes=discovery_peak,
 first_lookup_s=first_s,cached_lookup_s=cached_s,compact_export_s=export_s,compact_bytes=len(out.text.encode()),
 full_evidence_bytes=len(g.to_json().encode()),optional_loaded=[n for n in ('numpy','scipy','colorspacious','matplotlib','plotly','ultraplot') if n in sys.modules])))
'''


def main():
    import platform
    runs=[json.loads(subprocess.check_output([sys.executable,'-I','-c',SCRIPT],text=True)) for _ in range(3)]
    result={'date':'2026-10-23','python':platform.python_version(),'host':platform.platform(),
            'method':'three fresh processes; traced discovery measured separately from first/cached lookup; no timing gate',
            'runs':runs,'medians':{k:statistics.median(r[k] for r in runs) for k in runs[0] if k!='optional_loaded'}}
    path=ROOT/'artifacts/release-benchmarks.json';path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result['medians'],indent=2))


if __name__=='__main__':main()
