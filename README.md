# NVMe with Qemu
This repo holds the detail of setting up qemu with nvme support for nvme target understanding and debugging.

1. Setting up NVMe Target with NVMe Support
2. Setting up NVMe Host with NVMe-OF support (TBD)
3. Access the target NVMe-OF target from Host (TBD)
4. Run Wire-Shark (TBD)

1. Setting up NVMe Target with NVMe Support:-
a. Generate the image
    Create 4GB raw file for rootfs, which will hold the rootfs.
    #dd if=/dev/zero of=rootfs.img bs=1M count=4096

    Then format with ext4 filesystem, e.g. for ext4 with 4096 bytes blocks
    #mkfs.ext4 -b 4096 -F rootfs.img

    Mount the filesystem
    #mkdir ubuntu_xenial
    #mount -o loop rootfs.img ubuntu_xenial/
     
    Create root file system using debootstrap
    Install debootstrap
    #sudo apt-get install qemu-user-static debootstrap binfmt-support
    #debootstrap --arch=amd64 xenial ubuntu_xenial http://archive.ubuntu.com/ubuntu/

    Change the root password
    #sudo chroot ubuntu_xenial/
    #root@ubuntu:/# sudo passwd root
    After changing password exit Ctrl-D
    unmount the rootfs
    #umount ubuntu_xenial/

b. Creating kernel image

    Clone the linux kernel repo
    #git clone https://github.com/torvalds/linux.git 
    # cd linux/# git checkout v4.13OR
    Download a tar ball from here :- https://www.kernel.org/

    Copy your current config file from your kernel to the directory
    OR
    Use the one attached directly from here :- config-4.13.10

    After copying compile the kernel
    #make menuconfig

    Make sure below configs are set
    CONFIG_CONFIGFS_FS=y
    CONFIG_NVME_CORE=y
    CONFIG_BLK_DEV_NVME=y
    CONFIG_NVME_TARGET=y
    CONFIG_RTC_NVMEM=y
    CONFIG_NVMEM=y
    CONFIG_KGDB =y
    [*] KGDB: kernel debugger  --->
       <*>   KGDB: use kgdb over the serial console
            -> Compile-time checks and compiler options
                   [*] Compile the kernel with debug info
    Build the linux kernel
    #make -j8

    Find the bzImage and copy to local directory
    #cp linux-4.13.10/arch/x86_64/boot/bzImage .

c. Building QEMU with NVME support

    Clone the Qemu git repo
    #git clone https://github.com/OpenChannelSSD/qemu-nvme.git
    cd qemu-nvme/

    Build the Qemu with nvme support
    # ./configure --python=/usr/bin/python2 --enable-kvm --target-list=x86_64-softmmu --enable-linux-aio --prefix=/opt/qemu/qemu-nvme
    # make -j8

    Once compiled you will have below file
    # ls -l x86_64-softmmu/qemu-system-x86_64

    Create a 2GB NVMe Drive:-
    #dd if=/dev/zero of=blknvme bs=1M count=2096 // 2GB

d. Run and test the NVMe Drive
    Check the available kernel and rootfs image in your current folder
    # ls
    blknvme  bzImage  linux-4.13.10  qemu-nvme  rootfs.img

    Run following command for running the Qemu
    # ./qemu-nvme/x86_64-softmmu/qemu-system-x86_64 -nographic -no-reboot -m 512M -smp cpus=2 --enable-kvm -kernel ./bzImage -drive file=./rootfs.img,if=ide -drive file=./blknvme,if=none,id=mynvme -device nvme,drive=mynvme,serial=deadbeef,namespaces=1,lver=1,nlbaf=5,lba_index=3,mdts=10,lnum_lun=4,lnum_pln=2 -append "console=ttyS0 root=/dev/sda rw panic=1 earlyprintk=serial,ttyS0,115200"

    Once booted you can give root and password as set earlier and able to login

    Check the nvme device availability
    #root@ubuntu:~# ls -l /dev/nvme0n1
    brw-rw---- 1 root disk 259, 0 Oct 31 09:56 /dev/nvme0n1

    For more details on nvme driver copy/install the nvme-cli to the rootfs and try the following
    #root@ubuntu:/opt# ./nvme list
    Node             SN                   Model                                    Namespace Usage                      Format           FW Rev
    ---------------- -------------------- ---------------------------------------- --------- -------------------------- ---------------- --------
    /dev/nvme0n1     deadbeef             QEMU NVMe Ctrl                           1           2.19  GB /   2.19  GB      4 KiB +  0 B   1.0

e. DEBUGGING NVME Driver
    Run the following command to start qemu with -s optio
    #./qemu-nvme/x86_64-softmmu/qemu-system-x86_64 -nographic -no-reboot -m 512M -smp cpus=2 --enable-kvm -kernel ./bzImage -drive file=./rootfs.img,if=ide -drive file=./blknvme,if=none,id=mynvme -device nvme,drive=mynvme,serial=deadbeef,namespaces=1,lver=1,nlbaf=5,lba_index=3,mdts=10,lnum_lun=4,lnum_pln=2 -append "console=ttyS0 root=/dev/sda rw panic=1 earlyprintk=serial,ttyS0,115200" -s

    In another terminal run the following
    #cd linux-4.13.10/
    gdb ./vmlinux
    ...
    (gdb) target remote :1234
    Remote debugging using :1234
    io_serial_out (p=0xffffffff82234cc0 <serial8250_ports>, offset=0, value=107) at drivers/tty/serial/8250/8250_port.c:437
    437    }

    Put the breakpoint on the nvme functions
    (gdb) b nvme_core_init
    Breakpoint 1 at 0xffffffff820089a1: file drivers/nvme/host/core.c, line 2820.
    (gdb) c
    Continuing.
    Thread 1 hit Breakpoint 1, nvme_core_init () at drivers/nvme/host/core.c:2820
    2820    {
    (gdb) bt
    #0  nvme_core_init () at drivers/nvme/host/core.c:2820
    #1  0xffffffff81002193 in do_one_initcall (fn=0xffffffff820089a1 <nvme_core_init>) at init/main.c:817
    #2  0xffffffff81fad20f in do_initcall_level (level=<optimized out>) at init/main.c:883
    #3  do_initcalls () at init/main.c:891
    #4  do_basic_setup () at init/main.c:909
    #5  kernel_init_freeable () at init/main.c:1057
    #6  0xffffffff81908eee in kernel_init (unused=<optimized out>) at init/main.c:984
    #7  0xffffffff81916e35 in ret_from_fork () at arch/x86/entry/entry_64.S:425
    #8  0x0000000000000000 in ?? ()
    (gdb)

2. Setting up NVMe Host with NVMe-OF support (TBD)
