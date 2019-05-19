import pytest

from cloudhunky.aci_worker import ACIWorker
from cloudhunky.util import get_afs_creds

def test_aci_worker():
    resource_group_name = "ACI"
    aci_worker = ACIWorker(resource_group_name)
    container_group_name = "testcontainer"
    container_image_name = "busybox"
    command = ["/bin/sh", "-c", "echo HELLO WORLD from busybox"]

    aci_worker.run_task_based_container(container_group_name=container_group_name,
                                        container_image_name=container_image_name,
                                        command=command)

def test_aci_worker_with_afs():
    resource_group_name = "ACI"
    aci_worker = ACIWorker(resource_group_name)
    container_group_name = "testcontainer"
    container_image_name = "busybox"
    command = ["/bin/sh", "-c", "echo HELLO WORLD from busybox && cat /input/test_file"]
    afs_name, afs_key, afs_share = get_afs_creds()

    aci_worker.run_task_based_container(container_group_name=container_group_name,
                                        container_image_name=container_image_name,
                                        command=command,
                                        afs_name=afs_name,
                                        afs_key=afs_key,
                                        afs_share=afs_share,
                                        afs_mount_subpath='/')
