import pathlib, subprocess, sys, time
root=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root)); sys.path.insert(0,str(root/'src'))
from scripts.run_m1_p0_local_preflight import _assert_port_free, _listener_snapshot
from colluscope.openai_compat_llamacpp import load_llamacpp_backend_config,llama_server_command
cfg=load_llamacpp_backend_config(root/'runs/m1_p0_local/gguf-preflight-iteration-03/configs/m1-p0-8081-preflight.toml')
_assert_port_free(8081)
p=subprocess.Popen(llama_server_command(cfg),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=str(pathlib.Path(cfg.server_binary_path).parent),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0))
try:
    time.sleep(15)
    print('pid',p.pid,'poll',p.poll(),'netstat',_listener_snapshot(8081))
    ps_cmd="$ErrorActionPreference='Stop'; $x=Get-NetTCPConnection -LocalPort 8081 -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess; ConvertTo-Json -InputObject @($x) -Compress"
    ps=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps_cmd],capture_output=True,text=True,timeout=10)
    print('powershell_query_exit',ps.returncode,'stdout',repr(ps.stdout),'stderr',repr(ps.stderr))
finally:
    if p.poll() is None:p.terminate()
    try:p.wait(timeout=10)
    except subprocess.TimeoutExpired:p.kill();p.wait()
    out,err=p.communicate()
    print('server_exit',p.returncode)
