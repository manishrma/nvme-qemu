# NVMe with Qemu
This repo holds the detail of setting up qemu with nvme support for nvme target understanding and debugging.

1. Setting up NVMe Target
2. Setting up NVMe Host with NVMe-OF support
3. Install Qemu packages for bridge Interface
4. Use run.py for running the host and target interfaces
5. Access the target NVMe-OF target from Host (TBD)
6. Run Wire-Shark (TBD)

## 1. Setting up NVMe Target:-
- Generate the rootfs image
  - Create 4GB raw file for rootfs, which will hold the rootfs.
    ```
    dd if=/dev/zero of=rootfs-target.img bs=1M count=4096
    ```
  - Then format with ext4 filesystem, e.g. for ext4 with 4096 bytes blocks
    ```
    mkfs.ext4 -b 4096 -F rootfs-target.img
    ```
  - Mount the filesystem
    ```
    mkdir ubuntu_xenial
    mount -o loop rootfs-target.img ubuntu_xenial/
    ``` 
  - Create root file system using debootstrap
    Install debootstrap
    ```
    sudo apt-get install qemu-user-static debootstrap binfmt-support
    debootstrap --arch=amd64 xenial ubuntu_xenial http://archive.ubuntu.com/ubuntu/
    ```
  - Change the root password
    ```
    sudo chroot ubuntu_xenial/
    root@ubuntu:/# sudo passwd root
    ```
  - Change the hostname as target
    ```
    root@ubuntu:/# cat /etc/hostname
    target
    ```
  - After changing password exit Ctrl-D
    unmount the rootfs
    ```
    umount ubuntu_xenial/
    ```
- Creating kernel image
  - Clone the linux kernel repo
    ```
    git clone https://github.com/torvalds/linux.git
    cd linux/# git checkout v4.13OR
    ```
  - Download a tar ball from here :- https://www.kernel.org/
    Copy your current config file from your kernel to the directory
    OR
    Use the one attached directly from repo i.e config-4.13.10
    After copying compile the kernel
    ```
    make menuconfig
    ```
  - Make sure below configs are set
    ```
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
    ```
  - Build the linux kernel
    ```
    make -j8
    ```
  - Find the bzImage and copy to local directory
    ```
    cp linux-4.13.10/arch/x86_64/boot/bzImage .
    ```
    
- Building QEMU with NVME support
  - Clone the Qemu git repo
    ```
    git clone https://github.com/OpenChannelSSD/qemu-nvme.git
    cd qemu-nvme/
    ```
  - Build the Qemu with nvme support
    ```
    ./configure --python=/usr/bin/python2 --enable-kvm --target-list=x86_64-softmmu --enable-linux-aio --prefix=/opt/qemu/qemu-nvme
    make -j8
    ```
  - Once compiled you will have below file
    ```
    ls -l x86_64-softmmu/qemu-system-x86_64
    ```
  - Create a 2GB NVMe Drive:-
    ```
    dd if=/dev/zero of=blknvme bs=1M count=2096 // 2GB
    ```
- Run and test the NVMe Drive
  - Check the available kernel and rootfs image in your current folder
    ```
    # ls
    blknvme  bzImage  linux-4.13.10  qemu-nvme  rootfs-target.img
    ```
  - Run following command for running the Qemu
    ```
    # ./qemu-nvme/x86_64-softmmu/qemu-system-x86_64 -nographic -no-reboot -m 512M -smp cpus=2 --enable-kvm -kernel ./bzImage -drive file=./rootfs-target.img,if=ide -drive file=./blknvme,if=none,id=mynvme -device nvme,drive=mynvme,serial=deadbeef,namespaces=1,lver=1,nlbaf=5,lba_index=3,mdts=10,lnum_lun=4,lnum_pln=2 -append "console=ttyS0 root=/dev/sda rw panic=1 earlyprintk=serial,ttyS0,115200"
    ```
    Once booted you can give root and password as set earlier and able to login
  - Check the nvme device availability
    ```
    # root@target:~# ls -l /dev/nvme0n1
    brw-rw---- 1 root disk 259, 0 Oct 31 09:56 /dev/nvme0n1
    ```
  - For more details on nvme driver copy/install the nvme-cli to the rootfs and try the following
    ```
    #root@target:/opt# ./nvme list
    Node             SN                   Model                                    Namespace Usage                      Format           FW Rev
    ---------------- -------------------- ---------------------------------------- --------- -------------------------- ---------------- --------
    /dev/nvme0n1     deadbeef             QEMU NVMe Ctrl                           1           2.19  GB /   2.19  GB      4 KiB +  0 B   1.0
    ```
- DEBUGGING NVME Driver
  - Run the following command to start qemu with -s optio
    ```
    #./qemu-nvme/x86_64-softmmu/qemu-system-x86_64 -nographic -no-reboot -m 512M -smp cpus=2 --enable-kvm -kernel ./bzImage -drive file=./rootfs-target.img,if=ide -drive file=./blknvme,if=none,id=mynvme -device nvme,drive=mynvme,serial=deadbeef,namespaces=1,lver=1,nlbaf=5,lba_index=3,mdts=10,lnum_lun=4,lnum_pln=2 -append "console=ttyS0 root=/dev/sda rw panic=1 earlyprintk=serial,ttyS0,115200" -s
    ```
  - In another terminal run the following
    ```
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
    ```
## 2. Setting up NVMe Host with NVMe-OF support
- Generate rootfs image
  - Using the first step above create another instance of rootfs image i.e rootfs-host.img.
    ```
    # ls
    blknvme  bzImage  linux-4.13.10  qemu-nvme  rootfs-target.img rootfs-host.img
    ```
## 3. Install Qemu packages for bridge interface
- Install Qemu packages
    ```
    sudo apt-get install qemu-kvm qemu virt-manager virt-viewer libvirt-bin
    ```
- Check the bridge Interface
    The above packages will create a new user Libvirt Qemu and a new bridge interface in your system
    ```
    # ifconfig
    virbr0    Link encap:Ethernet  HWaddr 00:00:00:00:00:00
              inet addr:192.168.122.1  Bcast:192.168.122.255  Mask:255.255.255.0
              UP BROADCAST MULTICAST  MTU:1500  Metric:1
              RX packets:0 errors:0 dropped:0 overruns:0 frame:0
              TX packets:0 errors:0 dropped:0 overruns:0 carrier:0
              collisions:0 txqueuelen:1000
              RX bytes:0 (0.0 B)  TX bytes:0 (0.0 B)
    ```
## 4. Use run.py for running the host and target interfaces.
  - run.py utility help
    ```
    # python run.py
    usage: run.py [-h] [--nonet] [--nonvme] [-k KERNEL] [-r ROOTFS]
                  [-qdir QEMUDIR] (--host | --target)
    run.py: error: one of the arguments --host --target is required
    ```
  - Running host [The -qdir is the directory of the nvme supported qemu we compile above]
    ```
    # sudo python ./run.py --host -qdir=/opt/repo/qemu/qemu-nvme/
    ```
    It will come up with the prompt
    ```
    Ubuntu 16.04 LTS host ttyS0

    host login: root
    Password:
    ```
  - Running target
    ```
    # sudo python ./run.py --target -qdir=/opt/repo/qemu/qemu-nvme/
    ```
    It will come up with the prompt
    ```
    Ubuntu 16.04 LTS host ttyS0

    target login: root
    Password:
    ```
  - Update the network interface in rootfs [target & host] so that it will restart everytime. [Note the ens3 interface name in your system and change mac address for host and target]
    ```
    # cat /root/.bash_profile
    ifconfig ens3 hw ether 52:54:00:12:34:57
    /etc/init.d/networking restart
    ```
## 5. Access the target NVMe-OF target from Host
  - Check the network ipaddress and interface in the host system
    After running the host and target there will be a tap interface for each system
    ```
    tap1      Link encap:Ethernet  HWaddr fe:96:87:63:79:89
              inet6 addr: fe80::fc96:87ff:fe63:7989/64 Scope:Link
              UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
              RX packets:28 errors:0 dropped:0 overruns:0 frame:0
              TX packets:77 errors:0 dropped:0 overruns:0 carrier:0
              collisions:0 txqueuelen:1000
              RX bytes:3468 (3.4 KB)  TX bytes:8508 (8.5 KB)

    tap3      Link encap:Ethernet  HWaddr fe:10:a7:b6:05:7e
              inet6 addr: fe80::fc10:a7ff:feb6:57e/64 Scope:Link
              UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
              RX packets:15 errors:0 dropped:0 overruns:0 frame:0
              TX packets:64 errors:0 dropped:0 overruns:0 carrier:0
              collisions:0 txqueuelen:1000
              RX bytes:1690 (1.6 KB)  TX bytes:7140 (7.1 KB)

    virbr0    Link encap:Ethernet  HWaddr fe:10:a7:b6:05:7e
              inet addr:192.168.122.1  Bcast:192.168.122.255  Mask:255.255.255.0
              UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
              RX packets:43 errors:0 dropped:0 overruns:0 frame:0
              TX packets:21 errors:0 dropped:0 overruns:0 carrier:0
              collisions:0 txqueuelen:1000
              RX bytes:4556 (4.5 KB)  TX bytes:3338 (3.3 KB)
    ```
  - Make sure you have loaded all of the below modules in target and host respt.
    use the scripts **setup_target.sh and setup_host.sh** for loading and configuring the host and target system
    List of Modules on Host side (in sequence)
    ```
    insmod  udp_tunnel.ko
    insmod  ip6_udp_tunnel.ko
    insmod  configfs.ko
    insmod  ib_core.ko
    insmod  nvme-core.ko
    insmod  nvme.ko
    insmod  nvme-fabrics.ko
    insmod  crc32_generic.ko
    insmod  rdma_rxe.ko
    insmod  ib_cm.ko
    insmod  iw_cm.ko
    insmod  rdma_cm.ko
    insmod  ib_uverbs.ko
    insmod  rdma_ucm.ko
    insmod  nvme-rdma.ko
    ```
    List of Modules on Target side (in sequence)
    ```
    insmod  udp_tunnel.ko
    insmod  ip6_udp_tunnel.ko
    insmod  configfs.ko
    insmod  ib_core.ko
    insmod  nvme-core.ko
    insmod  nvme.ko
    insmod  nvme-fabrics.ko
    insmod  crc32_generic.ko
    insmod  rdma_rxe.ko
    insmod  ib_cm.ko
    insmod  iw_cm.ko
    insmod  rdma_cm.ko
    insmod  ib_uverbs.ko
    insmod  rdma_ucm.ko
    insmod  nvmet.ko
    insmod  nvmet-rdma.ko
    ```
    > NOTE:- Use scp for copying the modules OR mounting the rootfs as explained above

  - Install the nvme cli on both host and target machines
    ```
    # apt-get install nvme-cli
    ```
  - Setup rdma core on both target and host side
    > Note:- we are explicitly performing this as the package libibverb is not proper with the apt-get repo
    > In case libibverb is already installed. Please remove the package.
    ```
    # apt-get install git build-essential cmake gcc libudev-dev libnl-3-dev libnl-route-3-dev ninja-build pkg-config
    # git clone git://github.com/linux-rdma/rdma-core
    # cd rdma-core
    # ./build.sh
    ```
    Add below path to ~/.bashrc
    export PATH=$PATH:/root/rdma-core/build/bin:/root/rdma-core/providers/rxe
    ```
    # echo $PATH
    /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/media/rdma-core/build/bin:/media/rdma-core/providers/rxe
    ```

  - Setup RXE on target and host.
    Compile *rxe_cfg* on base system and copy to target and host.
    Clone repo [librxe cfg](https://github.com/SoftRoCE/librxe-dev.git)
    > Compile in your base system as it needs other dependencies i.e not present in the target/host filesystem
    ```
    # scp ./rxe_cfg root@<target/host ip>:/<path>/
    ```
    Create a new RXE device/interface by coupling it with an Ethernet interface (Run in both target and host)
    > here ens3 is the network interface.
    ```
    # ./rxe_cfg add ens3
    # ./rxe_cfg status
       Name  Link  Driver      Speed  NMTU  IPv4_addr       RDEV  RMTU
       ens3  yes   virtio_net         1500  192.168.122.91  rxe0  1024  (3)#
    ```
    Following command will show the devices
    ```
    # ibv_devices
     device       node GUID
     ------    ----------------
     rxe0      505400fffe123456

    ```

  - Mount configfs (On both target and host)
    ```
    mount -t configfs none /sys/kernel/config
    ```

  - Configure Namespace on **Target**
    Create nvmet-rdma subsystem (select any name)
    > Using *mysubsystem* here
    ```
    # mkdir /sys/kernel/config/nvmet/subsystems/mysubsystem
    # cd /sys/kernel/config/nvmet/subsystems/mysubsystem
    ```
    Allow any host to be connected to this target.
    ```
    # echo 1 > attr_allow_any_host
    ```
    Create a namespace inside the subsystem
    ```
    # mkdir namespaces/10
    # cd namespaces/10
    ```
    Set the path to the NVMe device and enable the namespace
    > device name /dev/nvme0n1
    ```
    # echo -n /dev/nvme0n1> device_path
    ```
    Create the NVMe port
    ```
    # mkdir /sys/kernel/config/nvmet/ports/1
    # cd /sys/kernel/config/nvmet/ports/1
    ```
    Set the IP address on the network adapter
    > The address is of nvme target. current system
    ```
    # echo 192.168.122.91 > addr_traddr
    ```
    Set other port configuration
    ```
    # echo rdma > addr_trtype
    # echo 4420 > addr_trsvcid
    # echo ipv4 > addr_adrfam
    # cd /sys/kernel/config/nvmet/
    # ln -s subsystems/mysubsystem/ ports/1/subsystems/
    ```
    Check if the port has been enabled
    ```
    # dmesg | grep "enabling port"
      nvmet_rdma: enabling port 1 (192.168.122.91:4420)
    ```
  - After checking the RXE device on host as shown above Start NVME discovery from host.
    > Here 192.168.122.91 is the target IP
    ```
    # nvme discover -t rdma -a 192.168.122.91 -s 4420

      Discovery Log Number of Records 1, Generation counter 1
      =====Discovery Log Entry 0======
      trtype:  rdma
      adrfam:  ipv4
      subtype: nvme subsystem
      treq:    not specified
      portid:  1
      trsvcid: 4420

      subnqn:  mysubsystem
      traddr:  192.168.122.91

      rdma_prtype: not specified
      rdma_qptype: connected
      rdma_cms:    rdma-cm
      rdma_pkey: 0x0000
    ```
  - Connect to the discovered subsystems using the subsystem.
    ```
    # nvme connect -t rdma -n mysubsystem -a 192.168.122.91 -s 4420
    ```
  - Verify by checking the available block device.
    ```
    # lsblk
      NAME    MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT
      sr0      11:0    1 1024M  0 rom
      sda       8:0    0    4G  0 disk /
      nvme0n1 259:0    0    8G  0 disk
    ```
  - For disconnection.
    ```
    # nvme disconnect -d /dev/nvme0n1
    ```
## 6. Run Wire-Shark (TBD)
  - Install latest wireshark. NVMe-oF (over RDMA) was added in January 2017 to Version greater than 2.4.0rc1.
    let's run the below command for installing and compiling wireshark.
    Download wireshark 2.4.3 from [here](https://www.wireshark.org/download.html)
    ```
    # sudo apt-get build-dep wireshark
    # sudo apt-get install build-essential checkinstall libcurl4-openssl-dev
    # tar xaf wireshark-2.4.3.tar.xz
    # cd wireshark-2.4.3
    # ./configure
    # make
    # make install (OR run from the local directory)
    ```
  - Run the wireshark from the local directory on the virbr0 interface.
    ```
    # sudo ./wireshark -k -i virbr0
    ```
  - After running wireshark, start the trafic (discovery/ connect) on host.
    ```
    # nvme discover -t rdma -a 192.168.122.91 -s 4420
    ```
  - Check the NVMe RDMA packets in wireshark like this:
    ![alt text](https://github.com/manishrma/nvme-qemu/blob/master/NVMeOF-RDMA.png "Wireshark output")

Run the traffic and enjoy Debugging.

Special Thanks to Kapil Upadhayay, This wouldn't have been possible with out his help.
Please refer to [Kapil's NvmeOF Link](https://github.com/kapilupadhayay/Programs/tree/master/lab/nvmeof) for more scripts.
For more details OR any Question you can write me at:- manishrma@gmail.com
