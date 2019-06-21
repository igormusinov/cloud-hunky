
# coding: utf-8

# In[1]:


import azure.common
import azure.mgmt.containerinstance
import azure.mgmt.resource

print(azure.common.__version__)
print(azure.mgmt.containerinstance.__version__)
print(azure.mgmt.resource.__version__)
# azure-common>=1.1.18
# azure-mgmt-containerinstance>=1.4.1
# azure-mgmt-resource>=2.1.0

from cloudhunky.aci_worker import ACIWorker
from cloudhunky.util import get_afs_creds


# In[6]:


import logging

logging.basicConfig(level=logging.INFO)

resource_group_name = "ACI"   
aci_worker = ACIWorker(resource_group_name)

container_image_name="alpine:3.6"
command = ["/bin/sh", "-c", "echo HELLO WORLD from busybox && ls /input"]
volume_mount_path = "/input"
afs_creds = get_afs_creds()
afs_name = afs_creds["AFS_NAME"]
afs_key = afs_creds["AFS_KEY"]
afs_share = afs_creds["AFS_SHARE"]

container_group_name, logs = aci_worker.run_task_based_container(container_image_name=container_image_name,
                      command=command,
                      volume_mount_path=volume_mount_path,
                      afs_name=afs_name,
                      afs_key=afs_key,
                      afs_share=afs_share,
                      afs_mount_subpath='')

print("Logs for container '{0}':".format(container_group_name))
print("{0}".format(logs.content))

