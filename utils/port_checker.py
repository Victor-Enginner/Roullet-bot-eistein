import socket

def port_available(host: str, port: int) -> bool:
    """Check if port is available"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) != 0

def find_free_port(host: str = 'localhost', start_port: int = 8765, max_tries: int = 10) -> int:
    """Find first available port starting from start_port"""
    for port in range(start_port, start_port + max_tries):
        if port_available(host, port):
            return port
    raise RuntimeError(f"No free port found in range {start_port}-{start_port+max_tries-1}")

