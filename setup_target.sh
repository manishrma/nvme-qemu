echo "Inserting modules"
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

echo "Configuring Network"
cd /media/
./rxe_cfg add ens3
./rxe_cfg status
ibv_devices

echo "Configuring Namespace"
mkdir /sys/kernel/config/nvmet/subsystems/mysubsystem
cd /sys/kernel/config/nvmet/subsystems/mysubsystem
echo 1 > attr_allow_any_host
mkdir namespaces/10
cd namespaces/10
echo -n /dev/nvme0n1> device_path
echo 1 > enable
mkdir /sys/kernel/config/nvmet/ports/1
cd /sys/kernel/config/nvmet/ports/1
echo 192.168.122.91 > addr_traddr
echo rdma > addr_trtype
echo 4420 > addr_trsvcid
echo ipv4 > addr_adrfam
cd /sys/kernel/config/nvmet/
ln -s subsystems/mysubsystem/ ports/1/subsystems/

dmesg | grep "enabling port"
