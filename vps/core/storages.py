import os
import errno
import uuid
import subprocess
from typing import Union

from fastapi import UploadFile

from core.config import Config

ROOT = "./temp_folder"


class ProjectFiles:
    def __init__(self, id: uuid.UUID):
        self._root_path = os.path.join(ROOT, str(id))
        if not os.path.isdir(self._root_path):
            os.mkdir(self._root_path)

    def store_by_path(self, file_path: str) -> str:
        _, ext = os.path.splitext(file_path)
        new_path = os.path.join(self._root_path, str(uuid.uuid4()) + ext)
        with open(file_path, "rb") as file:
            with open(new_path, "wb") as f:
                while chunk := file.read(Config.CHUNK_SIZE):
                    f.write(chunk)
        return os.path.basename(new_path)

    async def store_by_obj(self, file: UploadFile) -> str:
        _, ext = os.path.splitext(file.filename)
        new_path = os.path.join(self._root_path, str(uuid.uuid4()) + ext)
        with open(new_path, "wb") as f:
            while chunk := await file.read(Config.CHUNK_SIZE):
                f.write(chunk)
        return os.path.basename(new_path)
    
    def store_by_bytes(self, bytes: bytes, basename: str) -> str:
        new_path = os.path.join(self._root_path, basename)
        with open(new_path, "wb") as f:
            f.write(bytes)
        return os.path.basename(new_path)

    def store_by_youtube_url(self, url: str) -> str:
        file_name = str(uuid.uuid4())
        download_path = os.path.join(self._root_path, file_name)
        cmd = [
            "yt-dlp",
            "--merge-output-format",
            "mp4",
            "-o",
            download_path,
            url,
        ]
        subprocess.Popen(cmd).wait()
        download_path += '.mp4'
        if not os.path.isfile(download_path):
            raise Exception(
                "ProjectFiles: cannot download video from {}".format(url))
        return os.path.basename(download_path)

    def delete_file(self, file_name: str) -> bool:
        file_path = self.get_file_path(file_name)
        try:
            os.remove(file_path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
        return True

    def delete_files(self) -> bool:
        for file_name in os.listdir(self._root_path):
            self.delete_file(file_name)
        os.rmdir(self._root_path)
        return True        
    
    def get_file_link(self, file_name: str, checks: bool = True) -> str:
        path = self.get_file_path(file_name, checks)
        if not path:
            return None
        link = os.path.join(
            Config.FILES_URL,
            path.replace(f"{ROOT}/", "")
        )
        return link

    def get_file_path(self, file_name: str, checks: bool = True) -> Union[str, None]:
        if not file_name:
            if checks:
                raise Exception(
                    "ProjectFiles: Wrong file name requested '{}'".format(file_name)
                )
            else:
                return None
        file_path = os.path.join(self._root_path, file_name)
        if checks and not os.path.isfile(file_path):
            raise Exception(
                "ProjectFiles: File isn't exist '{}'".format(file_path)
            )
        return file_path
