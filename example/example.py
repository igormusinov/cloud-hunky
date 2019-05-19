
# coding: utf-8

# # Loading data to/from AFS
# 
# ## README
# 
# Set your AFS_NAME, AFS_KEY and AFS_SHARE envs
# 
# Specify your "local_root" directory where to download data

# In[1]:


from cloudhunky.data_loader import AFSLoader


local_root="./shared_folder"
data_folder="./data"
afs_loader = AFSLoader(local_root=local_root)
afs_path = afs_loader.upload_data_afs(data_folder)
afs_loader.download_data_afs(afs_path)


# In[2]:


from k8scontroller.kubernetes_job import KubeWorker

local_root="./shared_folder"
kube_worker = KubeWorker(local_root=local_root)
api_response = kube_worker.kube_create_job(container_image="busybox",
                                          command=["/bin/sh", "-c", "echo 'IM HERE'"])
# api_response = kube_worker.kube_create_job(container_image="busybox",
#                                           command=["/bin/sh", "-c", "while :; do echo 'IM HERE'; sleep 1; done"])


# In[3]:


job_name = api_response.metadata.labels['job-name']
print(f"Job's name is {job_name}")


# In[4]:


kube_worker.kube_test_credentials()
print("Starting cleaning")
kube_worker.kube_cleanup_finished_jobs()
print("Jobs were Cleaned")
kube_worker.kube_delete_empty_pods()


# ## Pipeline

# In[ ]:


from skopt import Optimizer
from skopt.learning import GaussianProcessRegressor
from skopt.learning.gaussian_process.kernels import RBF, ConstantKernel, Product
from tqdm import tqdm_notebook as tqdm
from skopt import gp_minimize
from time import sleep
import docker
import random
import os
import string
import sys


# In[ ]:


# первые n_initial_points модель не обучается
n_initial_points = 5

# число итераций цикла
n_calls = 3

# оптимизация на кубе [low_constraint, high_constraint]^dim
low_constraint, high_constraint = 2., 301.
dim = 1

# столько контейнеров вызываются для параллельной работы
batch_size = 2

# директория на сервере, хранит директории, которые будут монтироваться в контейнеры
folder_local = '/home/matyushinleonid/lhcb_ecal/feb_meeting/folder_local'
folder_local = '/home/igor/LAMBDA/lhcb_repo'
ptint("Ваш путь до директории с данными {} ".format(folder_local))

# директория для файлов input и output внутри контейнера
folder_container = '/home/nb_user/logs'

# python-клиент докера
client = docker.from_env()

# имя образа
image = "calorbuild"

# имена директорий, каждая соответствует своей копии образа
worker_names = ['first_worker', 'second_worker']

###
first_loop_legal_upper_bounds = [i for i in range(3, 301, 3)]
#second_loop_legal_upper_bounds = [i // 3 * 4 for i in first_loop_legal_upper_bounds]
#space_size = len(first_loop_legal_upper_bounds)
#total_amount_of_inner_part = [first_loop_legal_upper_bounds[i] * second_loop_legal_upper_bounds[i] \
#                              for i in range(space_size)]

def crop_number(n):
    return min(first_loop_legal_upper_bounds, key=lambda t:abs(t-n))
###


# In[ ]:


kernel = Product(ConstantKernel(1), RBF(1)) + ConstantKernel(1)

model = GaussianProcessRegressor(alpha=0, 
                                 normalize_y=True, 
                                 noise='gaussian', 
                                 n_restarts_optimizer=10, 
                                 kernel=kernel)

optimizer = Optimizer([[low_constraint, high_constraint]]*dim,
                      model,
                      n_initial_points=n_initial_points,
                      acq_func='EI',
                      acq_optimizer='lbfgs',
                      random_state=None)


# In[ ]:


def get_folder(folder_local):
    list_dir = os.listdir(folder_local)
    for _ in range(3):
        new_folder ='{}/{}'.format(folder_local,
                                   ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10)))
        if new_folder not in list_dir:
            os.mkdir(new_folder)
            return new_folder
    raise Exception("Cannot create uniq folder")   


def write_input_file(input_data):
    job_folder = get_folder(folder_local)
    file_to_write = '{}/input.txt'.format(job_folder)
    string_to_write = '\n'.join(map(str, input_data))
    with open(file_to_write, "w") as file:
        print(string_to_write,
              file=file)
    return job_folder

def new_point(x):
    croped_x = min(first_loop_legal_upper_bounds, key=lambda t:abs(t-x))
    return (croped_x, croped_x // 3 * 4) 

def create_job(job_folder, **kwargs):
    client.containers.run(privileged=True,
                          remove=False,
                          detach=False,
                          hostname='dev',
                          tty=True,
                          stdin_open=True,
                          volumes={job_folder: {'bind': folder_container,
                                                     'mode': 'rw'}},
                          **kwargs)
    

def read_output_file(job_folder):
    file_to_read = '{}/output.txt'.format(job_folder)
    with open(file_to_read, 'r') as myfile:
        data = myfile.read()
    return float(data)

def get_price(params, lamb=1):
    param1 = crop_number(params[0])
    param2 = param1 // 3 * 4
    return lamb * param1 * param2


# In[ ]:


from multiprocessing import Queue, Pool, Manager
import traceback
import logging

def test_worker(q_in, q_out):
    while True:         
        try:
            data = q_in.get()            
            in_dir = write_input_file(data)
            logging.info('Start Job {}'.format(in_dir))
            create_job(in_dir, 
                       image='busybox', 
                       command="/bin/sh -c 'head -1 input.txt > output.txt'",
                       working_dir='/home/nb_user/logs')  
            result = read_output_file(in_dir)
            q_out.put(( data, result ))   
        except:
            logging.error("Unexpected error:", sys.exc_info()[0])
            logging.error(traceback.format_exc())
            raise
        logging.info('Job {} is done'.format(in_dir))
    return   

def worker(q_in, q_out):
    while True:         
        try:
            data = q_in.get()            
            in_dir = write_input_file(data)
            logging.info('Start Job {}'.format(in_dir))
            create_job(in_dir, image='calorbuild')   
            result = read_output_file(in_dir)
            q_out.put(( data, result ))   
        except:
            logging.error("Unexpected error:", sys.exc_info()[0])
            logging.error(traceback.format_exc())
            raise
        logging.info('Job {} is done'.format(in_dir))
    return   


# In[ ]:


def optimize(optimizer, worker, num_workers, n_calls):
    pool = Pool(num_workers) 
    m = Manager()
    q_in = m.Queue()
    q_out = m.Queue()
    pool.starmap_async(worker, [(q_in, q_out)]*num_workers)

    X = optimizer.ask(n_points=num_workers)
    for i in range(num_workers):
        point = new_point(X[i][0])
        q_in.put(point)

    for _ in tqdm(range(n_calls-num_workers)): 
        x, y = q_out.get()
        optimizer.tell([x[0]], y) 
        point = new_point(optimizer.ask()[0])
        q_in.put(point)

    for _ in range(num_workers):
        x, y  = q_out.get()
        optimizer.tell([x[0]], y)      

    pool.terminate()
    return optimizer


# In[ ]:


# logging.basicConfig(level=logging.DEBUG)

optimizer = Optimizer([[low_constraint, high_constraint]]*dim,
                      model,
                      n_initial_points=n_initial_points,
                      acq_func='EI',
                      acq_optimizer='lbfgs',
                      random_state=None)


optimizer = optimize(optimizer, worker, 1, 1)
print(optimizer.Xi, optimizer.yi)

