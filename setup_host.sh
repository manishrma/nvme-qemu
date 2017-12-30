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

echo "Configuring Network"
cd /media/
./rxe_cfg add ens3
./rxe_cfg status
ibv_devices

