#!/usr/bin/env python3
"""
EDR Lite - Single Command Startup Script

This script starts both the backend and frontend servers.
"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path

def run_command(command, cwd, name):
    """Run a command in a subprocess"""
    print(f"\n[STARTING] {name}...")
    print(f"Command: {command}")
    print(f"Directory: {cwd}\n")
    
    return subprocess.Popen(
        command,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        preexec_fn=os.setsid if sys.platform != 'win32' else None
    )

def print_output(process, name):
    """Print output from a process"""
    for line in process.stdout:
        print(f"[{name}] {line}", end='')

def main():
    """Main startup function"""
    base_dir = Path(__file__).parent.absolute()
    backend_dir = base_dir / "backend"
    frontend_dir = base_dir / "frontend"
    
    print("=" * 70)
    print("EDR Lite - Endpoint Detection and Response System")
    print("=" * 70)
    
    # Check if directories exist
    if not backend_dir.exists():
        print(f"Error: Backend directory not found at {backend_dir}")
        sys.exit(1)
    
    if not frontend_dir.exists():
        print(f"Error: Frontend directory not found at {frontend_dir}")
        sys.exit(1)
    
    processes = []
    
    try:
        # Start backend
        if sys.platform == 'win32':
            backend_cmd = f"cd {backend_dir} && python -m venv venv && venv\\Scripts\\pip install -r requirements.txt && venv\\Scripts\\python main.py"
        else:
            backend_cmd = f"cd {backend_dir} && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt && ./venv/bin/python main.py"
        
        backend_proc = run_command(backend_cmd, str(backend_dir), "Backend")
        processes.append((backend_proc, "Backend"))
        
        # Wait a bit for backend to start
        time.sleep(3)
        
        # Start frontend
        frontend_cmd = "npm install && npm run dev"
        frontend_proc = run_command(frontend_cmd, str(frontend_dir), "Frontend")
        processes.append((frontend_proc, "Frontend"))
        
        print("\n" + "=" * 70)
        print("All services started!")
        print("- Backend API: http://localhost:8000")
        print("- API Docs: http://localhost:8000/docs")
        print("- Dashboard: http://localhost:3000")
        print("=" * 70)
        print("\nPress Ctrl+C to stop all services\n")
        
        # Monitor processes
        while True:
            for proc, name in processes:
                retcode = proc.poll()
                if retcode is not None:
                    print(f"\n[WARN] {name} process exited with code {retcode}")
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] Stopping all services...")
        for proc, name in processes:
            print(f"[STOPPING] {name}...")
            try:
                if sys.platform != 'win32':
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()
        print("[DONE] All services stopped")

if __name__ == "__main__":
    main()