from ftplib import FTP
from os import listdir
from os.path import isdir
import argparse


def send_directory(ftp, path='.', ignore=[]):
    for file_path in listdir(path):
        full_file_path = "{}/{}".format(path, file_path)

        ignored = False
        for ignore_pattern in ignore:
            if ignore_pattern in full_file_path:
                ignored = True
                break

        if ignored:
            continue

        if isdir(file_path):
            try:
                ftp.mkd(file_path)
            except Exception:
                # Assume directory exists
                pass

            send_directory(ftp, path=full_file_path, ignore=ignore)
            continue

        print("Sending {}".format(full_file_path))
        with open(full_file_path, "rb") as binary:
            ftp.storbinary(cmd="STOR {}".format(full_file_path),
                           fp=binary)
        print("{} transfer complete".format(full_file_path))


def send_files(server="192.168.1.23",
               user="micro",
               passwd="python",
               ignore_list=[]):
    print("Attempting to connect to {}".format(server))
    with FTP(host=server,
             user=user,
             passwd=passwd) as ftp:
        print("Connected... configuring and moving to Flash directory")
        ftp.set_pasv(True)
        ftp.cwd("flash")

        send_directory(ftp, ignore=ignore_list)

    ftp.close()
    print("Transfers complete")


def main(*args, **kwargs):
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--server", help="WiPy FTP Hostname or IP", default="192.168.1.9")
    parser.add_argument("-u", "--user", help="WiPy FTP username", default="micro")
    parser.add_argument("-p", "--passwd", help="WiPy FTP password", default="python")
    parser.add_argument("-i", "--ignore", help="Files not to upload", action="append", default=['send_commands.py', 'Device.md', '.swp' , 'swo'])
    args = parser.parse_args()

    send_files(args.server, args.user, args.passwd, args.ignore)


if __name__ == "__main__":
    main()
