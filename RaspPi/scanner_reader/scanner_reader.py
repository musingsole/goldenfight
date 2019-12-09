#!/usr/bin/python3


usb_path = "/dev/hidraw0"


def read_scanner(path=usb_path):
    read = input("Enter UPC: ")
    if read is None:
        raise ValueError("Invalid Read")
    for c in read:
        try:
            int(c)
        except ValueError:
            raise ValueError("Invalid Read")
    return read


if __name__ == "__main__":
    while True:
        try:
            read = read_scanner()
            with open("reads.txt", "a") as f:
                f.write(read + "\n||||\n")
            print("Accepted: " + read)
        except ValueError as e:
            print("ValueError: " + str(e))

