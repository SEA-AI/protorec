"""Installation script for ProtoRec service."""

import argparse
import getpass
import os
import sys
from pathlib import Path

SERVICE_NAME = "protorec.service"


def install_service() -> None:
    """Install ProtoRec as a systemd service."""
    # Check if running as root
    if os.geteuid() != 0:
        print("This script must be run as root (sudo)")
        sys.exit(1)

    # Get the real user who ran sudo
    user = os.environ.get("SUDO_USER")
    if not user:
        user = getpass.getuser()

    # Get the real user's home directory
    real_home = Path(os.path.expanduser(f"~{user}"))

    parser = argparse.ArgumentParser(
        description="Install ProtoRec as a systemd service"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=(real_home / "cameras_config.json").as_posix(),
        help="Path to camera configuration file",
    )
    parser.add_argument(
        "--recdir",
        type=str,
        default=(
            real_home / "POWER_Data" / "SDCard" / "DataSink" / "prototype_recordings"
        ).as_posix(),
        help="Path to recording directory",
    )
    args = parser.parse_args()

    # Read service template
    template_path = Path(__file__).parent / SERVICE_NAME
    with open(template_path, "r") as f:
        service_content = f.read()

    # Format service file
    service_content = service_content.format(
        user=user,
        config_path=args.config,
        recdir=args.recdir,
    )

    # Write service file
    service_path = Path("/etc/systemd/system") / SERVICE_NAME
    with open(service_path, "w") as f:
        f.write(service_content)
    print(f"Service file written to {service_path}")

    # Set permissions
    os.chmod(service_path, 0o644)

    # Reload systemd and enable service
    os.system("systemctl daemon-reload")
    os.system(f"systemctl enable {SERVICE_NAME}")
    os.system(f"systemctl restart {SERVICE_NAME}")
    print(f"{SERVICE_NAME} has been installed, enabled and (re)started")
    print(f"To check status, run: sudo systemctl status {Path(SERVICE_NAME).stem}")
    print(f"To check logs, run: sudo journalctl -u {Path(SERVICE_NAME).stem} -f")
