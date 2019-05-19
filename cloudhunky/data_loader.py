import os
import logging
import time
from pathlib import Path
from multiprocessing import cpu_count

from azure.storage.file import FileService

from .util import logbar, md5_dir, get_afs_creds


class AFSLoader():

    def __init__(self, local_root: Path, afs_creds: dict=None):
        if afs_creds is None:
            afs_creds = get_afs_creds()
        self.afs_name = afs_creds["AFS_NAME"]
        self.afs_key = afs_creds["AFS_KEY"]
        self.afs_share = afs_creds["AFS_SHARE"]
        self.file_service = FileService(account_name=self.afs_name,
                                        account_key=self.afs_key)
        self.local_root = Path(local_root)

    def get_afs_creds(self):
        return self.afs_name, self.afs_key, self.afs_share

    def upload_data_afs(self, data_path: Path, push_data: bool=False):
        """
        Copy data to the AFS directory.

        :param data_path: <Path>. Specify your path to the local data folder.
        :param push_data. If True upload data if it already exists.
        :return: path of the directory in the AFS share.
        """
        logging.info("Sending data to AFS")
        checksum = md5_dir(data_path)[:10]
        afs_path = time.strftime("%Y-%m-%d-%H.%M") + '-' + checksum

        list_folder = self.file_service.list_directories_and_files(self.afs_share)
        for folder in list_folder:
            if checksum == folder.name[-10:]:
                logging.info("Folder for data already exist!")
                afs_path = folder.name
                logging.info("Data is in the AFS {}".format(folder.name))
                if push_data:
                    logging.warning("Rewriting data")
                    afs_path = folder.name
                else:
                    return afs_path
        self.file_service.create_directory(share_name=self.afs_share,
                                           directory_name=afs_path)

        for file in Path(data_path).iterdir():
            progress_callback = lambda current, total: logbar(current, total,
                                                              f"Uploading {file.name}")
            self.file_service.create_file_from_path(share_name=self.afs_share,
                                                    directory_name=afs_path,
                                                    file_name=file.name,
                                                    local_file_path=str(file),
                                                    max_connections=cpu_count(),
                                                    progress_callback=progress_callback
                                                    )
        logging.info("Sending is over")
        return afs_path

    def download_data_afs(self, afs_path: Path, dst_path: Path=None):
        afs_path = Path(afs_path)
        if not dst_path:
            assert self.local_root is not None
            dst_path = self.local_root

        list_folder = self.file_service.list_directories_and_files(self.afs_share,
                                                                   directory_name=afs_path)
        try:
            os.mkdir(self.local_root / afs_path)
        except FileExistsError:
            print(f"Directory {self.local_root / afs_path} was rewritten ")
        for file in list_folder:
            progress_callback = lambda current, total: logbar(current, total,
                                                              f"Downloading {file.name}")
            self.file_service.get_file_to_path(share_name=self.afs_share,
                                               directory_name=afs_path,
                                               file_name=file.name,
                                               file_path=str(dst_path / afs_path / file.name),
                                               progress_callback=progress_callback)
