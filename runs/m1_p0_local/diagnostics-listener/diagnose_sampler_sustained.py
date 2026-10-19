import pathlib, socket, subprocess, sys, time, urllib.request
root=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root)); sys.path.insert(0,str(root/'src'))
from scripts.run_m1_p0_local_preflight import GpuSampler
from colluscope.openai_compat_llamacpp import load_llamacpp_backend_config,llama_server_command
cfg=load_llamacpp_backend_config(root/'runs/m1_p0_local/gguf-preflight-iteration-03/configs/m1-p0-8081-preflight.toml')
probe=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):probe.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
probe.bind(('127.0.0.1',8081));probe.close()
sampler=GpuSampler(root/'runs/m1_p0_local/diagnostics-listener/gpu-sampler-45s.jsonl',interval_seconds=0.25)
sampler.start()
p=subprocess.Popen(llama_server_command(cfg),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=str(pathlib.Path(cfg.server_binary_path).parent),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0))
try:
    time.sleep(45)
    print('pid',p.pid,'poll',p.poll(),'gpu_samples',len(sampler.rows),'gpu_success',sum(r.get('returncode')==0 for r in sampler.rows))
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for endpoint in ('health','props'):
        try:
            started=time.monotonic()
            with opener.open('http://127.0.0.1:8081/'+endpoint,timeout=5) as r:
                body=r.read(4096).decode(errors='replace')
                print('http',endpoint,r.status,round(time.monotonic()-started,3),body[:500])
        except Exception as exc: print('http_error',endpoint,type(exc).__name__,str(exc))
finally:
    sampler.stop()
    if p.poll() is None:p.terminate()
    try:p.wait(timeout=10)
    except subprocess.TimeoutExpired:p.kill();p.wait()
    out,err=p.communicate()
    print('server_exit',p.returncode,'stderr_tail',err.decode(errors='replace')[-1200:])
