import requests
import time
import os
import datetime
from typing import Tuple
from uuid import UUID

from elevenlabs import set_api_key, generate, voices
from pyairtable import Api
from api import pydantic_models as models

from cent import Client, PublishRequest
from cent.exceptions import CentError

from core.config import Config


class DubService:
    URL = Config.DUB_API_URL
    
    @classmethod
    def push(cls, file_path: str) -> str:
        response = requests.post(
            cls.URL + "transcribe/files",
            params={
                "language": "unknown",
                "model_size": "medium",
                "diarize": False,
                "device": "cuda",
                "batch_size": 4,
                "compute_type": "float32",
                "interpolate_method": "nearest",
                "min_speakers": 1,
                "max_speakers": 10,
                "return_type": "segments",
            },
            files=[("files", open(file_path, 'rb'))],
            auth=("abobus", "amogus"),
        )

        return response.json()[os.path.basename(file_path)]

    @classmethod
    def get_result(cls, task_id) -> dict:
        response = requests.post(
            cls.URL + "tasks/status",
            params={
                "task_id": task_id
            },
            auth=("abobus", "amogus"),
        )

        return response.json()

    @classmethod
    def await_result(cls, task_id) -> Tuple[str, str]:
        while True:
            ans = cls.get_result(task_id)
            if ans["status"] == "SUCCESS":
                result_text = ans["result"]["speakers"]
                break

            time.sleep(Config.REQUEST_STATUS_DELAY)

        return result_text["unknown"]


class TransService:
    URL = Config.TRANS_API_URL

    @classmethod
    def push(cls, text, target_lang) -> str:
        response = requests.post(
            cls.URL + "translation/text",
            params={
                "text": text,
                "source_language": None,
                "target_language": target_lang,
                "translator": "deepl",
            },
            auth=("abobus", "amogus"),
        )

        return response.json()["task_id"]

    @classmethod
    def get_result(cls, task_id) -> dict:
        response = requests.post(
            cls.URL + "tasks/status",
            params={
                "task_id": task_id,
            },
            auth=("abobus", "amogus"),
        )

        return response.json()

    @classmethod
    def await_result(cls, task_id):
        while True:
            ans = cls.get_result(task_id)
            if ans["status"] == "SUCCESS":
                result_text = ans["result"]["result"]
                break

            time.sleep(Config.REQUEST_STATUS_DELAY)
        
        return result_text
    

class SyntService:
    set_api_key(Config.SYNT_API_KEY)

    @classmethod
    def synt(cls, text: str, voice: str) -> bytes:
        return generate(
            text=text.replace("\n\n", " ").replace("\\", "")  ,
            voice=voice
        )


class CastdevService:
    api = Api(Config.AIRTABLE_API_KEY)
    table = api.table(
        Config.AIRTABLE_BASE_ID,
        Config.AIRTABLE_TABLE_NAME
    )

    @classmethod
    def create(cls, name: str, email: str, id: UUID) -> None:
        now = datetime.datetime.now()
        time = now.strftime('%Y-%m-%d')

        cls.table.create(
            {"Name": name,
             "Email": email,
             "ID": str(id),
             "Дата добавления в базу": time
             })

    @classmethod
    def get(cls, id) -> object:
        return cls.table.get(id)

    @classmethod
    def delete(cls, id) -> bool:
        response = cls.table.delete(id)
        return response['deleted']


class WebsocketService:
    url = f'http://centrifugo:{Config.CENTRIFUGO_PORT}/api'
    key = Config.CENTRIFUGO_API_KEY

    @classmethod
    def publish(cls, user_id: str, body: models.EventInfo) -> None:
        try:
            cent = Client(cls.url, cls.key)
            r = PublishRequest(channel=user_id, data=body.data.__dict__)
            cent.publish(r)

        except CentError as e:
            pass
        
        finally:
            cent.close()