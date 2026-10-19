import json, pathlib, subprocess, sys, time, socket, urllib.request, urllib.error
root = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root)); sys.path.insert(0, str(root / 'src'))
from scripts.run_m1_p0_local_preflight import _listener_snapshot, _process_image, _assert_port_free
from colluscope.openai_compat_llamacpp import load_llamacpp_backend_config, llama_server_command
cfg_path = root / 'runs/m1_p0_local/gguf-preflight-iteration-03/configs/m1-p0-8081-preflight.toml'
cfg = load_llamacpp_backend_config(cfg_path)
_assert_port_free(8081)
p = subprocess.Popen(llama_server_command(cfg), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(pathlib.Path(cfg.server_binary_path).parent), creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
try:
    time.sleep(15)
    print('pid', p.pid, 'poll', p.poll(), 'image', _process_image(p.pid))
    print('listener_snapshot', _listener_snapshot(8081))
    raw = subprocess.run(['netstat.exe','-ano','-p','tcp'], capture_output=True, text=True, timeout=10)
    print('raw_matching_lines', [repr(x) for x in raw.stdout.splitlines() if '8081' in x])
    try:
        with socket.create_connection(('127.0.0.1',8081), timeout=5) as sock:
            print('tcp_connect', 'PASS')
            sock.sendall(b'GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n')
            sock.settimeout(5)
            print('health_response', repr(sock.recv(4096)))
    except Exception as exc:
        print('tcp_http_error', type(exc).__name__, str(exc))
    for url in ('http://127.0.0.1:8081/health','http://127.0.0.1:8081/props'):
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=5) as response:
                print('url_result', url, response.status, response.read(1000).decode(errors='replace'))
        except Exception as exc:
            print('url_error', url, type(exc).__name__, str(exc))
finally:
    if p.poll() is None:
        p.terminate()
        try: p.wait(timeout=10)
        except subprocess.TimeoutExpired: p.kill(); p.wait()
    stdout, stderr = p.communicate()
    print('server_exit', p.returncode)
    print('server_stderr_tail', stderr.decode(errors='replace')[-12000:])
    print('server_stdout_tail', stdout.decode(errors='replace')[-4000:])
