import pathlib, socket, subprocess, sys, time, urllib.request
root=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root));sys.path.insert(0,str(root/'src'))
from scripts.run_m1_p0_local_preflight import GpuSampler,_build_probes,_listener_snapshot,_process_image,_assert_port_free
from colluscope.gguf_tokenizer import GGUFChatTokenCounter
from colluscope.m1_runtime import load_runtime_config
from colluscope.openai_compat_llamacpp import load_llamacpp_backend_config,llama_server_command
cfgpath=root/'runs/m1_p0_local/gguf-preflight-iteration-03/configs/m1-p0-8081-preflight.toml'
cfg=load_llamacpp_backend_config(cfgpath);runtime=load_runtime_config(root/'configs/m1-r-offline-v2.toml')
probes,evidence=_build_probes(cfg,root/'configs/m1-r-offline-v2.toml')
token=GGUFChatTokenCounter(pathlib.Path(cfg.artifact_path),expected_artifact_sha256=cfg.artifact_sha256)
print('prepared',len(probes),'tokenizer',token.tokenizer_sha256)
_assert_port_free(8081);print('prelaunch_owner_query=completed')
out=root/'runs/m1_p0_local/diagnostics-listener';logs=out/'prelaunch-query-logs';logs.mkdir(exist_ok=True)
sampler=GpuSampler(out/'prelaunch-query-gpu-samples.jsonl',interval_seconds=0.25);sampler.start()
stdout=(logs/'llama.stdout.log').open('wb');stderr=(logs/'llama.stderr.log').open('wb')
p=subprocess.Popen(llama_server_command(cfg),stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,cwd=str(pathlib.Path(cfg.server_binary_path).parent),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0),close_fds=True)
try:
    print('pid',p.pid,'image',_process_image(p.pid));time.sleep(15)
    print('after15',p.poll(),'listener',_listener_snapshot(8081),'gpu_samples',len(sampler.rows))
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8081/health',timeout=5) as r:print('health',r.status,r.read(1024))
    except Exception as e:print('health_error',type(e).__name__,str(e))
finally:
    sampler.stop()
    if p.poll() is None:p.terminate()
    try:p.wait(timeout=10)
    except subprocess.TimeoutExpired:p.kill();p.wait()
    stdout.close();stderr.close();print('exit',p.returncode)
