import subprocess, sys, time, pathlib
root = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / 'src'))
from scripts.run_m1_p0_local_preflight import _listener_snapshot
child = subprocess.Popen([sys.executable, '-m', 'http.server', '8081', '--bind', '127.0.0.1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
try:
    time.sleep(1)
    raw = subprocess.run(['netstat.exe', '-ano', '-p', 'tcp'], capture_output=True, text=True, timeout=10)
    print('child_pid', child.pid, 'child_poll', child.poll(), 'netstat_exit', raw.returncode)
    for line in raw.stdout.splitlines():
        if '8081' in line:
            print('matching_line_repr', repr(line), 'fields', line.split())
    print('helper_result', _listener_snapshot(8081))
finally:
    child.terminate()
    try: child.wait(timeout=5)
    except subprocess.TimeoutExpired: child.kill(); child.wait()
    stdout, stderr = child.communicate()
    print('child_stdout', stdout.decode(errors='replace'))
    print('child_stderr', stderr.decode(errors='replace'))
