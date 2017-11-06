# This code is just the helper script to run Qemu target and host on the local system 
# using the repo :- https://github.com/manishrma/nvme
# Any improvments will be appreciated. All options are not yet tested.
# you can write me (Manish Sharma) at
# email   :- manishrma@gmail.com
# Subject :- [Nvme Repo] <subject>

import os, sys, subprocess
import argparse


# global variables
kernel = ['-kernel', './bzImage']
qemu_dir = '/opt/repo/qemu/qemu-nvme'
qemu_bin = '/x86_64-softmmu/qemu-system-x86_64'
network = ""
nvme = ""
# Update these Arguments 
# in case your system doesnt have KVM module inserted or cpu doesnt have support remove --enable-kvm
# Update the memory and the cpu as per your need
ARGS = ['-nographic', '-no-reboot', '-m', '1G', '-smp', 'cpus=2', '--enable-kvm']
serial = ['-append', "console=ttyS0 root=/dev/sda panic=1  earlyprintk=serial,ttyS0,115200"]

# argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('--nonet', help='start qemu with no network interface', action="store_true")
parser.add_argument('--nonvme', help='start qemu with no nvme device', action="store_true")
parser.add_argument('-k', '--kernel', type = str, help='kernel Image for VM', action="store")
parser.add_argument('-r', '--rootfs', type = str, help='rootfs for VM', action="store")
parser.add_argument('-qdir', '--qemudir', type = str, help='directory for qemu with nvme support', action="store")

# Add mutually exclusive group
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--host', help='start qemu as nvme host system', action="store_true")
group.add_argument('--target', help='start qemu as nvme target system', action="store_true")

args = parser.parse_args()

if args.host:
    print "host selected"
    rootfs = ['-drive', 'file=./rootfs-host.img,if=ide']
    nvme_dev = [] 
elif args.target:
    print "target selected"
    rootfs = ['-drive', 'file=./rootfs-target.img,if=ide']
    nvme_dev = ['-drive', 'file=./blknvme,if=none,id=mynvme', '-device', 'nvme,drive=mynvme,serial=deadbeef,namespaces=1,lver=1,nlbaf=5,lba_index=3,mdts=10']

if args.qemudir:
   qemu_dir = args.qemudir
   print "qemu dir %s " % qemu_dir

if not args.nonet:
    print "network selected"
    network = ['-net', 'nic,model=virtio', '-net', 'tap,script=no,downscript=no,vhost=on', '-net', 'bridge,br=virbr0,helper='+qemu_dir+'qemu-bridge-helper']

if args.nonvme:
    print "No nvme selected"
    nvme_dev = ['']

if args.kernel:
   kernel = ['-kernel', args.kernel]
   print "kernel selected %s" % kernel

if args.rootfs:
   rootfs = ['-drive', 'file=' + args.rootfs + ',if=ide']
   print "rootfs selected %s" % kernel

qemu_path = [qemu_dir + qemu_bin]

cmdline = qemu_path + ARGS + kernel + rootfs + network + nvme_dev + serial

#print "cmdline = %s" % (cmdline)
fd = subprocess.Popen(cmdline)
fd.communicate()
