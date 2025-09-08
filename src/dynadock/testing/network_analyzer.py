#!/usr/bin/env python3
"""
Network connectivity analysis module for DynaDock testing
"""

import socket
import ssl
from urllib.parse import urlparse
from typing import Dict, Any


def analyze_network_connectivity(url: str, verbose: bool = False) -> Dict[str, Any]:
    """Detailed network analysis for a URL with enhanced logging"""
    parsed = urlparse(url)
    hostname = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    analysis = {
        "hostname": hostname,
        "port": port,
        "scheme": parsed.scheme,
        "tcp_connect": False,
        "dns_resolution": None,
        "port_scan": {},
        "ssl_cert_info": None,
        "logs": [],
        "timing": {},
    }

    def log(message: str):
        """Add verbose logging"""
        if verbose:
            print(f"   [NETWORK] {message}")
        analysis["logs"].append(message)

    log(f"Rozpoczynanie analizy sieciowej dla {url}")
    log(f"Parsed: {hostname}:{port} ({parsed.scheme})")

    # DNS resolution test
    log("Testowanie rozwiązywania DNS...")
    import time

    start_time = time.time()
    try:
        ip = socket.gethostbyname(hostname)
        dns_time = time.time() - start_time
        analysis["dns_resolution"] = {"success": True, "ip": ip, "time": dns_time}
        analysis["timing"]["dns"] = dns_time
        log(f"DNS SUCCESS: {hostname} → {ip} ({dns_time:.3f}s)")
    except Exception as e:
        dns_time = time.time() - start_time
        analysis["dns_resolution"] = {
            "success": False,
            "error": str(e),
            "time": dns_time,
        }
        analysis["timing"]["dns"] = dns_time
        log(f"DNS FAILED: {e} ({dns_time:.3f}s)")

    # TCP connection test
    log(f"Testowanie połączenia TCP na port {port}...")
    start_time = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((hostname, port))
        tcp_time = time.time() - start_time
        analysis["tcp_connect"] = result == 0
        analysis["timing"]["tcp"] = tcp_time
        if result == 0:
            log(f"TCP SUCCESS: Port {port} dostępny ({tcp_time:.3f}s)")
        else:
            log(f"TCP FAILED: Port {port} niedostępny, kod: {result} ({tcp_time:.3f}s)")
        sock.close()
    except Exception as e:
        tcp_time = time.time() - start_time
        analysis["tcp_connect"] = False
        analysis["timing"]["tcp"] = tcp_time
        log(f"TCP EXCEPTION: {e} ({tcp_time:.3f}s)")

    # Port scan common ports
    log("Skanowanie popularnych portów...")
    common_ports = [80, 443, 8000, 8001, 8025, 5432, 6379]
    scan_start = time.time()
    for p in common_ports:
        port_start = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((hostname, p))
            port_time = time.time() - port_start
            is_open = result == 0
            analysis["port_scan"][p] = is_open
            status = "OPEN" if is_open else "CLOSED"
            log(f"Port {p}: {status} ({port_time:.3f}s)")
            sock.close()
        except Exception as e:
            port_time = time.time() - port_start
            analysis["port_scan"][p] = False
            log(f"Port {p}: ERROR - {e} ({port_time:.3f}s)")

    scan_time = time.time() - scan_start
    analysis["timing"]["port_scan"] = scan_time
    open_ports = [p for p, open in analysis["port_scan"].items() if open]
    log(
        f"Port scan complete: {len(open_ports)}/{len(common_ports)} open ({scan_time:.3f}s)"
    )

    # SSL certificate info for HTTPS
    if parsed.scheme == "https":
        log("Testowanie certyfikatu SSL...")
        ssl_start = time.time()
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    ssl_time = time.time() - ssl_start
                    analysis["ssl_cert_info"] = {
                        "subject": dict(x[0] for x in cert["subject"]),
                        "issuer": dict(x[0] for x in cert["issuer"]),
                        "version": cert["version"],
                        "notAfter": cert["notAfter"],
                        "time": ssl_time,
                    }
                    analysis["timing"]["ssl"] = ssl_time

                    subject_cn = analysis["ssl_cert_info"]["subject"].get(
                        "commonName", "Unknown"
                    )
                    issuer_org = analysis["ssl_cert_info"]["issuer"].get(
                        "organizationName", "Unknown"
                    )
                    log(
                        f"SSL SUCCESS: CN='{subject_cn}', Issuer='{issuer_org}' ({ssl_time:.3f}s)"
                    )
        except Exception as e:
            ssl_time = time.time() - ssl_start
            analysis["ssl_cert_info"] = {"error": str(e), "time": ssl_time}
            analysis["timing"]["ssl"] = ssl_time
            log(f"SSL FAILED: {e} ({ssl_time:.3f}s)")

    total_time = sum(analysis["timing"].values())
    analysis["timing"]["total"] = total_time
    log(f"Analiza sieciowa zakończona - łączny czas: {total_time:.3f}s")

    return analysis
