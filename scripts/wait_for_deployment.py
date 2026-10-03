"""
Health Polling Script for Post-Deployment Verification.
Polls the live Load Balancer URL health endpoint until HTTP 200 is confirmed.
"""
import sys
import time
import urllib.request
import urllib.error


def poll_health(base_url: str, max_attempts: int = 30, delay: int = 10) -> bool:
    health_url = f"{base_url.rstrip('/')}/health"
    print(f"[*] Starting health checks against: {health_url}")

    for attempt in range(1, max_attempts + 1):
        try:
            req = urllib.request.Request(
                health_url,
                headers={"User-Agent": "CI-CD-Health-Poller/1.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    print(f"[+] Service is healthy and responding with HTTP 200! (Attempt {attempt})")
                    return True
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, Exception) as err:
            print(f"[-] Attempt {attempt}/{max_attempts}: Service not ready yet ({err}). Retrying in {delay}s...")

        time.sleep(delay)

    print("[!] Error: Timeout exceeded waiting for service to report healthy.")
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python wait_for_deployment.py <BASE_URL>")
        sys.exit(1)

    target_url = sys.argv[1]
    is_healthy = poll_health(target_url)
    sys.exit(0 if is_healthy else 1)
