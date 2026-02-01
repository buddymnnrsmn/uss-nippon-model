#!/usr/bin/env python3
"""
Dashboard Runner Script
========================

Starts the Streamlit dashboard with proper configuration for development/testing.

Usage:
    python scripts/run_dashboard.py [--port PORT] [--no-browser]

Options:
    --port PORT     Port to run on (default: 8501)
    --no-browser    Don't open browser automatically
    --background    Run in background and return
"""

import subprocess
import sys
import time
import argparse
import signal
import os


def start_dashboard(port=8501, open_browser=True, background=False):
    """Start the Streamlit dashboard."""

    # Change to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)

    cmd = [
        sys.executable, "-m", "streamlit", "run",
        "interactive_dashboard.py",
        "--server.port", str(port),
    ]

    if not open_browser:
        cmd.extend(["--server.headless", "true"])

    print(f"Starting dashboard on port {port}...")
    print(f"URL: http://localhost:{port}")

    if background:
        # Run in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )
        print(f"Dashboard started in background (PID: {process.pid})")

        # Wait for it to be ready
        for _ in range(10):
            time.sleep(1)
            try:
                import urllib.request
                urllib.request.urlopen(f"http://localhost:{port}", timeout=2)
                print(f"Dashboard is ready at http://localhost:{port}")
                return process.pid
            except:
                pass

        print("Warning: Dashboard may not be ready yet")
        return process.pid
    else:
        # Run in foreground
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\nDashboard stopped.")


def stop_dashboard(port=8501):
    """Stop any dashboard running on the specified port."""
    try:
        result = subprocess.run(
            ["fuser", "-k", f"{port}/tcp"],
            capture_output=True,
            text=True
        )
        print(f"Stopped dashboard on port {port}")
    except Exception as e:
        print(f"Could not stop dashboard: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the financial model dashboard")
    parser.add_argument("--port", type=int, default=8501, help="Port to run on")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    parser.add_argument("--background", action="store_true", help="Run in background")
    parser.add_argument("--stop", action="store_true", help="Stop running dashboard")

    args = parser.parse_args()

    if args.stop:
        stop_dashboard(args.port)
    else:
        start_dashboard(
            port=args.port,
            open_browser=not args.no_browser,
            background=args.background
        )
