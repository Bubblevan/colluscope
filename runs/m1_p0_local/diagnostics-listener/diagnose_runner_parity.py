import json, pathlib, socket, subprocess, sys, time, urllib.request
root=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root));sys.path.insert(0,str(root/'src'))
from scripts.run_m1_p0_local_preflight import GpuSampler,_build_probes,_listener_snapshot,_process_image
from colluscope.gguf_tokenizer import GGUFChatTokenCounter
from colluscope.m1_runtime import load_runtime_config
from colluscope.openai_compat_llamacpp import load_llamacpp_backend_config,llama_server_command
cfgpath=root/'runs/m1_p0_local/gguf-preflight-iteration-03/configs/m1-p0-8081-preflight.toml'
cfg=load_llamacpp_backend_config(cfgpath); runtime=load_runtime_config(root/'configs/m1-r-offline-v2.toml')
probes,evidence=_build_probes(cfg,root/'configs/m1-r-offline-v2.toml')
token=GGUFChatTokenCounter(pathlib.Path(cfg.artifact_path),expected_artifact_sha256=cfg.artifact_sha256)
print('prepared',len(probes),'tokenizer',token.tokenizer_sha256)
probe=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):probe.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
probe.bind(('127.0.0.1',8081));probe.close()
out=root/'runs/m1_p0_local/diagnostics-listener'; logs=out/'runner-parity-logs';logs.mkdir(exist_ok=True)
sampler=GpuSampler(out/'runner-parity-gpu-samples.jsonl',interval_seconds=0.25);sampler.start()
stdout=(logs/'llama.stdout.log').open('wb');stderr=(logs/'llama.stderr.log').open('wb')
p=subprocess.Popen(llama_server_command(cfg),stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,cwd=str(pathlib.Path(cfg.server_binary_path).parent),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0),close_fds=True)
try:
    print('pid',p.pid,'image',_process_image(p.pid))
    time.sleep(15)
    print('after15',p.poll(),'listener',_listener_snapshot(8081),'gpu_samples',len(sampler.rows))
    try:
        with socket.create_connection(('127.0.0.1',8081),timeout=5) as s:
            s.sendall(b'GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n');s.settimeout(5);print('socket_health',repr(s.recv(4096)))
    except Exception as e:print('socket_error',type(e).__name__,str(e))
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8081/health',timeout=5) as r:print('urllib_health',r.status,r.read(1024))
    except Exception as e:print('urllib_error',type(e).__name__,str(e))
finally:
    sampler.stop()
    if p.poll() is None:p.terminate()
    try:p.wait(timeout=10)
    except subprocess.TimeoutExpired:p.kill();p.wait()
    stdout.close();stderr.close()
    print('exit',p.returncode)
