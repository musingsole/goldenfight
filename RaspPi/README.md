# GoldenFight RaspPi

This module configures a Raspberry Pi as a GoldenFight scale.

## Raspberry Pi Configuration

```
sudo apt install dnsmasq hostapd
sudo systemctl unalias hostapd
sudo systemctl enable hostapd
sudo systemctl stop dnsmasq
sudo systemctl stop hostapd
# Call a python script
sudo reboot
```

