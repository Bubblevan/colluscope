import pathlib, subprocess, sys, time, urllib.request
root = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root)); sys.path.insert(0, str(root / 'src'))
from scripts.run_m1_p0_local_preflight import _assert_port_free, GpuSampler, _listener_snapshot
from colluscope.openai_compat_llamacpp import load_llamacpp_backend_config, llama_server_command
cfg = load_llamacpp_backend_config(root / 'runs/m1_p0_local/gguf-preflight-iteration-03/configs/m1-p0-8081-preflight.toml')
_assert_port_free(8081)
sampler = GpuSampler(root / 'runs/m1_p0_local/diagnostics-listener/gpu-sampler-025.jsonl', interval_seconds=0.25)
sampler.start()
p = subprocess.Popen(llama_server_command(cfg), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(pathlib.Path(cfg.server_binary_path).parent), creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
try:
    deadline = time.monotonic() + 60
    rows=[]
    while time.monotonic() < deadline and p.poll() is None:
        rows, raw = _listener_snapshot(8081)
        if rows and rows[0]['OwningProcess'] == p.pid: break
        time.sleep(0.5)
    print('pid', p.pid, 'listener', rows, 'raw', raw)
    time.sleep(5)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for endpoint in ('health','props','health'):
        try:
            start=time.monotonic()
            with opener.open('http://127.0.0.1:8081/'+endpoint, timeout=5) as r:
                body=r.read(2000).decode(errors='replace')
                print('http', endpoint, r.status, round(time.monotonic()-start,3), body[:300])
        except Exception as e: print('http_error',endpoint,type(e).__name__,str(e))
    print('gpu_samples',len(sampler.rows),'gpu_success',sum(x.get('returncode')==0 for x in sampler.rows))
finally:
    sampler.stop()
    if p.poll() is None: p.terminate()
    try: p.wait(timeout=10)
    except subprocess.TimeoutExpired: p.kill(); p.wait()
    out,err=p.communicate()
    print('server_exit',p.returncode,'stderr_tail',err.decode(errors='replace')[-2000:])
