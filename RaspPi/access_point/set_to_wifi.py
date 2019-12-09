import path
from subprocess import run

def set_to_wifi():
    config_path = path.join(path.dirname(__file__), "config_path")

    print("Setting up dhcpcd")
    result = run(["cp", f"{config_path}/dhcpcd.conf.orig", "/etc/dhcpcd.conf"])
    print("Set dhcpcd")

    # Setup hostapd call
    print("Setting up hostapd")
    result = run(["cp", f"{config_path}/default.hostapd.orig", "/etc/default/hostapd"])
    print("Set hostapd")

    # Setup sysctl
    print("Setting up sysctl")
    result = run(["cp", f"{config_path}/sysctl.conf.orig", "/etc/sysctl.conf"])
    print("Set sysctl")

    print("Rebooting")
    run("reboot")


if __name__ == "__main__":
    set_to_wifi()

