import sys
import os
from . import cloudhunky_logger
from pathlib import Path
import time

from azure.common.client_factory import get_client_from_auth_file
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerinstance.models import (ContainerGroup,
                                                 Container,
                                                 ContainerState,
                                                 ContainerGroupRestartPolicy,
                                                 GpuResource,
                                                 EnvironmentVariable,
                                                 ResourceRequests,
                                                 ResourceRequirements,
                                                 OperatingSystemTypes,
                                                 AzureFileVolume,
                                                 Volume,
                                                 VolumeMount)
from msrestazure.azure_exceptions import CloudError
from azure.mgmt.containerinstance.models import ImageRegistryCredential

from cloudhunky.util import id_generator


class ACIWorker:
    def __init__(self, resource_group_name):
        auth_file_path = os.getenv('AZURE_AUTH_LOCATION', None)
        if auth_file_path is not None:
            cloudhunky_logger.info("Authenticating with Azure using credentials in file at {0}"
                         .format(auth_file_path))

            self.aci_client = get_client_from_auth_file(
                ContainerInstanceManagementClient)
            res_client = get_client_from_auth_file(ResourceManagementClient)
            self.resource_group = res_client.resource_groups.get(resource_group_name)
        else:
            cloudhunky_logger.warning("\nFailed to authenticate to Azure. Have you set the"
                            " AZURE_AUTH_LOCATION environment variable?\n")

    def run_task_based_container(self, container_image_name: str,
                                 command: list = None,
                                 memory_in_gb: int = 1,
                                 cpu: float = 1.0,
                                 gpu_count: int=0,
                                 gpu_type: str='K80',
                                 envs: dict = {},
                                 timeout: int=600,
                                 volume_mount_path: str = "/input",
                                 afs_name: str = None,
                                 afs_key: str = None,
                                 afs_share: str = None,
                                 afs_mount_subpath: str = '',
                                 image_registry_server: str = None,
                                 image_registry_username: str = None,
                                 image_registry_pwd: str = None,
                                 tag: str = ""):

        """Creates a container group with a single task-based container who's
           restart policy is 'Never'. If specified, the container runs a custom
           command line at startup.
        Arguments:
            container_image_name {str}
                        -- The container image name and tag, for example:
                           microsoft\aci-helloworld:latest
            command {list}
                        -- The command line that should be executed when the
                           container starts. This value can be None.
        """
        container_group_name = str(id_generator()) + "-" + tag
        envs['DATA'] = str(Path(volume_mount_path) / afs_mount_subpath)

        if command is not None:
            cloudhunky_logger.info("Creating container group '{0}' with start command '{1}'"
                         .format(container_group_name, command))

        gpu = None
        if gpu_count > 0:
            gpu = GpuResource(count=gpu_count, sku=gpu_type)
        container_resource_requests = ResourceRequests(memory_in_gb=memory_in_gb,
                                                       cpu=cpu,
                                                       gpu=gpu)
        container_resource_requirements = ResourceRequirements(
            requests=container_resource_requests)

        environment_variables = []
        if envs is not None:
            for env, val in envs.items():
                environment_variables.append(EnvironmentVariable(name=env, value=val))

        volume_mounts = None
        volumes = None
        if afs_mount_subpath is not None:
            volumes, volume_mounts = self.prepare_azure_volumes(afs_name=afs_name,
                                                                afs_key=afs_key,
                                                                afs_share=afs_share,
                                                                volume_mount_path=volume_mount_path)
        image_registry_credentials = None
        if image_registry_username is not None or image_registry_pwd is not None:
            if image_registry_username is None:
                raise ValueError("insert image_registry_username")
            if image_registry_pwd is None:
                raise ValueError("insert image_registry_pwd")
            if image_registry_server is None:
                raise ValueError("insert image_registry_server")
            image_registry_credentials = [ImageRegistryCredential(server=image_registry_server,
                                                                 username=image_registry_username,
                                                                 password=image_registry_pwd)]


        container = Container(name=container_group_name,
                              image=container_image_name,
                              resources=container_resource_requirements,
                              command=command,
                              environment_variables=environment_variables,
                              volume_mounts=volume_mounts,
                              ports=None)

        group = ContainerGroup(location=self.resource_group.location,
                               containers=[container],
                               os_type=OperatingSystemTypes.linux,
                               restart_policy=ContainerGroupRestartPolicy.never,
                               volumes=volumes,
                               image_registry_credentials=image_registry_credentials)

        for i in range(2):
            try:
                result = self.aci_client.container_groups.create_or_update(
                        self.resource_group.name,
                        container_group_name,
                        group)
            except CloudError as exp:
                cloudhunky_logger.exception(exp)
                cloudhunky_logger.info("Try to reduce the required resources")
                if i == 1:
                    raise exp
            else:
                cloudhunky_logger.info("Azure is provisioning container group")
                break

        # Wait for the container create operation to complete. The operation is
        # "done" when the container group provisioning state is one of:
        # Succeeded, Canceled, Failed
        cloudhunky_logger.info("Container Group is pending")
        while result.done() is False:
            time.sleep(30)
        try:
            container_group = self.aci_client.container_groups.get(
                self.resource_group.name,
                container_group_name)
            if str(container_group.provisioning_state).lower() == 'succeeded':
                cloudhunky_logger.info("Creation of container group '{}' succeeded."
                             .format(container_group_name))
            else:
                cloudhunky_logger.warning("\nCreation of container group '{}' failed. Provisioning state"
                      "is: {}. Deleting the container group.".format(container_group_name,
                                      container_group.provisioning_state))
                self.aci_client.container_groups.delete(self.resource_group.name,
                                                        container_group_name)
                return
        except Exception as exp:
            cloudhunky_logger.exception(exp)

        try:
            start = time.time()
            while timeout > (time.time() - start):
                container_group = self.aci_client.container_groups.get(self.resource_group.name,
                                                        container_group_name)
                container_state = container_group.containers[0].instance_view.current_state.state
                if container_state.lower() == "terminated":
                    cloudhunky_logger.info("Container terminated")
                    break
                time.sleep(1)
            if timeout < (time.time() - start):
                cloudhunky_logger.warning(f"Timeout {timeout} was exceeded!")
        except Exception as exp:
            cloudhunky_logger.exception(exp)

        try:
            logs = self.aci_client.container.list_logs(self.resource_group.name,
                                                       container_group_name,
                                                       container.name)
            self.aci_client.container_groups.delete(self.resource_group.name,
                                                    container_group_name)
        except Exception as exp:
            cloudhunky_logger.exception(exp)
        return container_group_name, logs

    def prepare_azure_volumes(self, afs_name: str, afs_key: str, afs_share: str,
                              volume_mount_path: str):
        assert afs_name is not None
        assert afs_key is not None
        assert afs_share is not None
        assert volume_mount_path is not None

        az_volume = AzureFileVolume(share_name=afs_share,
                                    storage_account_name=afs_name,
                                    storage_account_key=afs_key)
        volumes = [Volume(name="azure-volume",
                          azure_file=az_volume)]
        volume_mount = [VolumeMount(name="azure-volume",
                                    mount_path=volume_mount_path)]
        return volumes, volume_mount
