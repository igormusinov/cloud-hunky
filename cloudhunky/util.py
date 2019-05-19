import sys
import hashlib
from _hashlib import HASH as Hash
from pathlib import Path
from typing import Union
import string
import random
import yaml


def md5_update_from_file(filename: Union[str, Path], hash: Hash) -> Hash:
    assert Path(filename).is_file()
    with open(str(filename), "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash.update(chunk)
    return hash


def md5_file(filename: Union[str, Path]) -> str:
    return str(md5_update_from_file(filename, hashlib.md5()).hexdigest())


def md5_update_from_dir(directory: Union[str, Path], hash: Hash) -> Hash:
    assert Path(directory).is_dir()
    for path in sorted(Path(directory).iterdir()):
        hash.update(path.name.encode())
        if path.is_file():
            hash = md5_update_from_file(path, hash)
        elif path.is_dir():
            hash = md5_update_from_dir(path, hash)
    return hash


def md5_dir(directory: Union[str, Path]) -> str:
    return str(md5_update_from_dir(directory, hashlib.md5()).hexdigest())


def logbar(current, total, name: str = 'Proccessing'):
    if total == 0:
        sys.stdout.write("\r%s [%s]" % (name, '=' * 50))
        sys.stdout.flush()
        return
    done = int(50.0 * current / total)
    sys.stdout.write("\r%s [%s%s]" % (name, '=' * done, ' ' * (50 - done)))
    if current == total:
        sys.stdout.write("\n")
    sys.stdout.flush()


def id_generator(size=12, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def get_afs_creds(path: Path = Path("~/.azure/afs_creds.yml")):
    path = Path(path).expanduser()
    with open(path, 'r') as ymlfile:
        afs_creds = yaml.load(ymlfile)
    assert afs_creds["AFS_NAME"], "Invalid afs_name"
    assert afs_creds["AFS_KEY"], "Invalid afs_name"
    assert afs_creds["AFS_SHARE"], "Invalid afs_name"
    return afs_creds

def get_azure_creds(path: Path = Path("~/.azure/azure_creds")):
    with open(path, 'r') as file:
        azure_creds = file.read()
    return azure_creds