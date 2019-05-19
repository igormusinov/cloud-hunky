# Installation (for users)

```
pip install -e .
```

# ACI-worker
1. Install az cli (https://docs.microsoft.com/ru-ru/cli/azure/install-azure-cli?view=azure-cli-latest)
With apt
```
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

2. Get the Azure credentials and set env AZURE_AUTH_LOCATION
```
az login
az ad sp create-for-rbac --sdk-auth > my.azureauth
export AZURE_AUTH_LOCATION=/home/yourusername/.azure/azure_creds
```

# Kubernetes-worker (job-controller)

1. Get the cluster config and put it in the '$HOME/.kube/config'.

2. Install kubectl https://kubernetes.io/docs/tasks/tools/install-kubectl/  (Optionally)
```
sudo apt-get update && sudo apt-get install -y apt-transport-https
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee -a /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update
sudo apt-get install -y kubectl
```

# AFS both for ACI and k8s

1. Create .yml file with your afs creds
```
echo 'AFS_NAME: <afs_name>
AFS_KEY: <afs_key>
AFS_SHARE: <afs_share>
AZURE_SECRET: <azure_secret>' > ~/.azure/afs_creds.yml
```

Mount AFS into your local directory.
https://docs.microsoft.com/ru-ru/azure/storage/files/storage-how-to-use-files-linux
```
sudo apt-get install cifs-utils
sudo apt install smbclient

export STORAGE_KEY=<storage-account-key>
export MOUNT_AZURE=<mount-point>
export STORAGE_NAME="kubeocean"
export AZURE_SHARE="datalake"
mkdir $MOUNT_AZURE
ssh -L 8081:$STORAGE_NAME.file.core.windows.net:445 <user>@<Azure-VM-IP>
sudo mount -t cifs //127.0.0.1/$AZURE_SHARE $MOUNT_AZURE -o vers=3.0,port=8081,username=$STORAGE_NAME,password=$STORAGE_KEY,dir_mode=0777,file_mode=0777,serverino

```



## Set up a cluster (for admins)
### AKS (https://docs.microsoft.com/en-us/azure/aks/cluster-autoscaler)
```
# First create a resource group
az group create --name myResourceGroup --location westeurope

# Now create the AKS cluster and enable the cluster autoscaler
az aks create \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --kubernetes-version 1.12.6 \
  --node-count 1 \
  --enable-vmss \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 3
```

### Azure File Storage
https://docs.microsoft.com/ru-ru/azure/aks/azure-files-volume
```
kubectl create secret generic azure-secret --from-literal=azurestorageaccountname=$AKS_PERS_STORAGE_ACCOUNT_NAME --from-literal=azurestorageaccountkey=$STORAGE_KEY
```


### Docker registry
Set your own docker registry.
```
kubectl create secret docker-registry gitlab-registry \
  --docker-server=$DOCKER_REGISTRY_SERVER \
  --docker-username=$DOCKER_USER \
  --docker-password=$DOCKER_PASSWORD \
  --docker-email=$DOCKER_EMAIL
   ```

### Monitoring with kubernetes-dashboard
```
kubectl create -f ./config/dashboard.yml
kubectl proxy &
curl http://127.0.0.1:8001/api/v1/namespaces/kube-system/services/http:kubernetes-dashboard:/proxy/
```

or with az cli
```
az login
az aks browse --resource-group <rg-name> --name <aks-name>
```
