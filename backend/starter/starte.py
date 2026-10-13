import subprocess
import sys

def main():
    command = [
        "cloudflared",
        "tunnel",
        "run",
        "fresh_laptop_tunnel",
    ]

    print("Starting Cloudflare Tunnel: fresh_laptop_tunnel")
    print("Press Ctrl+C to stop.\n")

    try:
        subprocess.run(command, check=True)
    except FileNotFoundError:
        print("Error: cloudflared was not found. Ensure it is installed and on PATH.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStopping Cloudflare Tunnel...")
    except subprocess.CalledProcessError as exc:
        print(f"Cloudflare Tunnel exited with code {exc.returncode}")
        sys.exit(exc.returncode)

if __name__ == "__main__":
    main()