
import sys
import re
import os
import subprocess
import queue
import threading
import time
import datetime

def get_bw(interface, msecs):
    avg_points = 10
    cmd = ["bwm-ng", "-I", interface, "-o", "csv", "-T", "avg", "-t", str((msecs/avg_points)-1), "-u", "bytes", "-c", str(avg_points), "-A", str(msecs/1000)]
    print(" ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    proc.wait()

    lines = proc.stdout.readlines()
    for line in reversed(lines):
        parts = line.decode("utf-8", errors='ignore').split(";")
        if parts[1] == interface:
            return (float(parts[3]), float(parts[4]))

def ping(host):
    cmd = ["ping", "-c", "1", host]
    print(" ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    proc.wait()

    return proc.returncode == 0

def line_busy(interface, traffic_cutoff):

    traffic = get_bw(interface, 10000)

    if(max(traffic) > traffic_cutoff):
        return True
    else:
        return False

def wifi_device_present(devices):
    for d in devices:
        # lookup ip address
        if ping(d):
            return True
    return False

def unit_spec(spec):
    if spec == "ms":
        return (1/1000.0, "s")
    if spec == "Mbit/s" or "Mbits/s":
        return (1024*1024, "bit/s")
    if spec == "kbit/s" or spec == "Kbit/s" or spec == "kbits/s" or spec == "Kbits/s":
        return (1024, "bit/s")
    return (1, spec)

def speed_test():
    cmd = ["speedtest-cli", "--simple"]
    print(" ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    proc.wait()

    out = {"connected": False}

    if proc.returncode == 0:

        out["connected"] = True
        for line in proc.stdout.readlines():
            parts = line.decode("utf-8", errors='ignore').split(" ")
            unit = unit_spec(parts[2].strip())
            out[parts[0].lower().replace(":", "").strip()] = float(parts[1]) * unit[0]

    return out
        

def is_night(night):
    now = datetime.datetime.now()
    if now.hour >= night[0] and now.hour < night[1]:
        return True

if __name__ == "__main__":
    
    import argparse
    parser = argparse.ArgumentParser(description='Bandwidth logger')

    parser.add_argument("--interface", "-i", help='network interface', required=True)
    parser.add_argument("--force", "-f", help='force test', action='store_true')

    traffic_cutoff = 100 * 1024 # bytes
    devices = [
        "30:07:4d:1c:af:60", # joern samsung s8
        "192.168.1.68", # joern samsung s8 rf
        "192.168.1.107", # joern xps rf
        "10.0.2.24", # joern xperia
        "10.0.2.48" # stine iphone
    ]
    night = [0, 7]
    db_file = "db.csv"

    args = parser.parse_args()

    test_line = line_busy(args.interface, traffic_cutoff)
    test_dev = wifi_device_present(devices)
    test_night = is_night(night)

    print("Line busy:", test_line)
    print("Devices present:", test_dev)
    print("Is night:", test_night)

    if args.force or ((not test_line) and (test_night or not test_dev)):
        print("Performing speed test")
        now = time.time()
        speed = speed_test()
        print(speed)
        with open(db_file, "a+") as fd:
            csv = ", ".join([str(x) for x in [now, 1 if speed["connected"] else 0, speed["ping"], speed["download"], speed["upload"]]])
            fd.write(csv + "\n")
    
    else:
        print("Not performing speed test")        
