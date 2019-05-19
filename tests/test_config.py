import pytest

import os
from cloudhunky.util import get_afs_creds
from azure.common.client_factory import get_client_from_auth_file
from azure.mgmt.containerinstance import ContainerInstanceManagementClient

def test_azure_config():
    auth_file_path = os.getenv('AZURE_AUTH_LOCATION', None)
    if auth_file_path is not None:
        print("Authenticating with Azure using credentials in file at {0}"
              .format(auth_file_path))
        aci_client = get_client_from_auth_file(ContainerInstanceManagementClient)
    else:
        print("\nFailed to authenticate to Azure. Have you set the"
              " AZURE_AUTH_LOCATION environment variable?\n")
    assert aci_client is not None


def test_afs_config():
    afs_creds = get_afs_creds()
    print(afs_creds)