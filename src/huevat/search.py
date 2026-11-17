"""Cancellable custom searches in a separate Python process."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from concurrent.futures import CancelledError,TimeoutError


class SearchJob:
    def __init__(self,family,options,progress=None):
        if family not in ('categorical','sequential','diverging','multihue','spectral','optimized'):
            raise ValueError('Unknown search family')
        if progress is not None and not callable(progress):raise ValueError('progress must be callable')
        self._work=tempfile.TemporaryDirectory(prefix='huevat-search-')
        self._root=Path(self._work.name);self._started=time.monotonic();self._callback=progress
        self._cancelled=False;self._last=0.;self._done=False;self._result=None
        if family=='optimized':
            options=dict(options);options['gradient']=options['gradient'].to_recipe()
        (self._root/'request.json').write_text(json.dumps({'family':family,'options':options},allow_nan=False),encoding='utf-8')
        flags={'creationflags':subprocess.CREATE_NO_WINDOW} if sys.platform=='win32' else {}
        self._process=subprocess.Popen([sys.executable,'-m','huevat.search',str(self._root)],
                                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**flags)

    @property
    def elapsed(self):return time.monotonic()-self._started
    @property
    def status(self):
        if self._cancelled:return 'cancelled'
        if self._process.poll() is not None:return 'finished'
        return 'searching' if (self._root/'started').exists() else 'starting'
    def poll(self):
        status={'stage':self.status,'elapsed_seconds':self.elapsed}
        if self._callback is not None and (self.elapsed-self._last>=.1 or self._process.poll() is not None):
            self._last=self.elapsed
            try:self._callback(status)
            except BaseException:self.cancel();raise
        return status
    def cancel(self):
        if self._process.poll() is not None:return False
        self._cancelled=True;self._process.terminate();self._process.wait();self._work.cleanup()
        return True
    def result(self,timeout=None):
        if timeout is not None:
            from .gradients import _finite
            if _finite(timeout,'timeout')<0:raise ValueError('timeout must be nonnegative')
        deadline=None if timeout is None else time.monotonic()+timeout
        while self._process.poll() is None:
            self.poll()
            if deadline is not None and time.monotonic()>=deadline:raise TimeoutError()
            time.sleep(.05)
        if self._cancelled:raise CancelledError('Huevat search cancelled')
        if self._done:return self._result
        self.poll()
        path=self._root/'result.json'
        if not path.exists():
            self._work.cleanup();raise RuntimeError('Search worker exited without a result')
        result=json.loads(path.read_text(encoding='utf-8'));self._work.cleanup()
        if 'error' in result:
            from . import gradients
            cls=getattr(gradients,result['error'],None)
            if cls and issubclass(cls,gradients.QualityError):raise cls(result['message'],result.get('report',{}))
            raise ValueError(result['message'])
        from . import load_recipe
        self._result=load_recipe(result['recipe']);self._done=True
        return self._result
    def __enter__(self):return self
    def __exit__(self,*args):self.cancel()


def start_search(family,*,progress=None,**options):
    """Start a custom search. poll/result report stages and elapsed time, not a guessed percentage."""
    return SearchJob(family,options,progress)


def _worker(root):
    import huevat as hv
    root=Path(root);request=json.loads((root/'request.json').read_text(encoding='utf-8'))
    (root/'started').write_text('searching',encoding='utf-8')
    try:
        options=request['options']
        if request['family']=='optimized':
            options['gradient']=hv.load_recipe(options['gradient']);result=hv.optimized_discrete(**options)
        else:result=getattr(hv,request['family'])(**options)
        output={'recipe':result.to_recipe()}
    except Exception as error:
        output={'error':type(error).__name__,'message':str(error)}
        if hasattr(error,'report'):output['report']=error.report.to_dict()
    (root/'result.json').write_text(json.dumps(output,allow_nan=False),encoding='utf-8')


if __name__=='__main__':_worker(sys.argv[1])
