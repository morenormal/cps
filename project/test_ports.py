import socket
import os
from rich.progress import Progress, BarColumn, TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn

HOST = "portquiz.net"
PORTS = range(1, 10000)
TIMEOUT = 0.4  # seconds for reliability
RESULTS_FILE = "scan_results.txt"

def scan_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(TIMEOUT)
        try:
            sock.connect((HOST, port))
            return "OPEN"
        except ConnectionRefusedError as e:
            print(f"Port {port} ConnectionRefusedError: {e} (errno={getattr(e, 'errno', None)})")
            return "REFUSED"
        except OSError as e:
            err_code = getattr(e, "errno", None)
            msg = str(e)
            print(f"Port {port} OSError: {e} (errno={err_code})")
            # Treat "timed out" in OSError as BLOCKED
            if err_code in [61, 111]:
                return "REFUSED"
            elif err_code in [101, 113]:
                return "BLOCKED"
            elif "timed out" in msg:  # macOS: OSError("timed out", errno=None)
                return "BLOCKED"
            elif err_code is not None:
                return f"ERROR-{err_code}"
            else:
                return f"ERROR-{type(e).__name__}:{msg}"
        except socket.timeout:
            print(f"Port {port} socket.timeout")
            return "BLOCKED"
        except Exception as e:
            print(f"Port {port} Exception: {e} ({type(e).__name__})")
            return f"ERROR-{type(e).__name__}:{str(e)}"

def load_results(filename):
    results = {}
    if os.path.exists(filename):
        with open(filename, "r") as f:
            for line in f:
                if line.startswith("Testing port "):
                    try:
                        port_str = line.split("Testing port ")[1].split("...")[0].strip()
                        result_str = line.split("...")[1].strip()
                        port = int(port_str)
                        results[port] = result_str
                    except Exception:
                        continue
    return results

def save_results(filename, results):
    with open(filename, "w") as f:
        for port in sorted(results):
            line = f"Testing port {port}... {results[port]}"
            f.write(line + "\n")

def main():
    results = load_results(RESULTS_FILE)
    already_scanned = set(results.keys())
    ports_to_scan = [port for port in PORTS if port not in already_scanned]

    print(f"Loaded {len(already_scanned)} results from previous scan. {len(ports_to_scan)} ports left to scan.")

    try:
        with Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task_id = progress.add_task("Scanning ports", total=len(ports_to_scan))
            for port in ports_to_scan:
                result = scan_port(port)
                results[port] = result
                progress.update(task_id, advance=1)
                # Save every 50 ports to minimize loss on interruption
                if len(results) % 50 == 0:
                    save_results(RESULTS_FILE, results)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Saving progress...")

    save_results(RESULTS_FILE, results)
    print(f"Progress saved. {len(results)} ports scanned so far. Resume by running again.")

    for port in sorted(results):
        print(f"Testing port {port}... {results[port]}")
    print(f"\nResults saved to {RESULTS_FILE}")

if __name__ == "__main__":
    main()