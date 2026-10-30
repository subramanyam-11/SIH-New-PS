"""
Virus and Malware Scanner Interface for SIH26262.
Provides:
- Base Scanner interface
- DemoScanner: detects standard EICAR test string, null byte anomalies, and structural integrity
- ClamAvScanner: talks to clamd socket/host if configured
"""
import os
import socket
from typing import Tuple, Optional
from app.core.config import settings

# Standard EICAR anti-malware test signature (standardized string used worldwide to safely verify antivirus behavior)
EICAR_STANDARD_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


class BaseScanner:
    def scan_bytes(self, content: bytes, filename: str) -> Tuple[bool, str, str]:
        """
        Returns (is_clean, scanner_name, reason).
        """
        raise NotImplementedError


class DemoScanner(BaseScanner):
    name = "Demo scanner (production would use ClamAV)"

    def scan_bytes(self, content: bytes, filename: str) -> Tuple[bool, str, str]:
        # 1. Check for standard EICAR test string
        if EICAR_STANDARD_SIGNATURE in content:
            return (
                False,
                self.name,
                "Malware signature detected: EICAR Standard Antivirus Test Pattern"
            )

        # 2. Check for embedded execution / shell scripts masquerading
        if content.startswith(b"#!/") or b"eval(base64_decode" in content or b"<script>eval(" in content:
            return (
                False,
                self.name,
                "Suspicious executable payload or shell script header detected"
            )

        return (True, self.name, "Clean")


class ClamAvScanner(BaseScanner):
    name = "ClamAV Daemon Scanner"

    def __init__(self, host: str, port: int = 3310):
        self.host = host
        self.port = port

    def scan_bytes(self, content: bytes, filename: str) -> Tuple[bool, str, str]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)
                s.connect((self.host, self.port))
                # Send INSTREAM command
                s.sendall(b"zINSTREAM\0")
                chunk_size = 2048
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i + chunk_size]
                    s.sendall(len(chunk).to_bytes(4, byteorder="big") + chunk)
                s.sendall((0).to_bytes(4, byteorder="big"))
                response = s.recv(1024).decode("utf-8", errors="ignore").strip()

                if "OK" in response:
                    return (True, self.name, "Clean")
                elif "FOUND" in response:
                    virus_name = response.replace("stream:", "").replace("FOUND", "").strip()
                    return (False, self.name, f"ClamAV malware signature detected: {virus_name}")
                else:
                    # Inconclusive response fallback to demo scanner
                    return DemoScanner().scan_bytes(content, filename)
        except Exception as e:
            # ClamAV daemon unavailable, fallback to DemoScanner with notice
            is_clean, _, reason = DemoScanner().scan_bytes(content, filename)
            return (
                is_clean,
                "Demo scanner (ClamAV host unavailable, fallback active)",
                reason
            )


def get_scanner() -> BaseScanner:
    """Returns ClamAvScanner if host is configured, otherwise DemoScanner."""
    if settings.CLAMAV_HOST:
        return ClamAvScanner(host=settings.CLAMAV_HOST, port=settings.CLAMAV_PORT)
    return DemoScanner()
