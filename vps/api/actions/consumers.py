import asyncio
import uuid
import logging
import os
import traceback
from typing import List
from datetime import datetime

from celery_worker.start_worker import celery_app
from celery import signature
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from db.dals.projects import ProjectDAL
from db.dals.localizations import LocalizationDAL
from db.dals.languages import LanguagesDAL
from db.dals.users import UserDAL
from db.models import Project, Localization, Language, User
from db.session import async_session
from api.services import DubService, TransService, SyntService
from api.actions.email import send_localization_done
from core.file_processor import merge_audio_and_video, audio_from_video
from core.storages import ProjectFiles
from core.status import StatusEnum

logger = logging.getLogger("consumers")


async def get_user_by_id(user_id: uuid.UUID) -> User:
    session = async_session()
    async with session.begin():
        user_dal = UserDAL(session)
        res = await user_dal.get_by_id(user_id)
    return res

async def get_loc_by_id(loc_id: uuid.UUID) -> Localization:
    session = async_session()
    async with session.begin():
        loc_dal = LocalizationDAL(session)
        res = await loc_dal.get_by_id(loc_id)
    return res


async def get_prj_by_id(prj_id: uuid.UUID) -> Project:
    session = async_session()
    async with session.begin():
        project_dal = ProjectDAL(session)
        res = await project_dal.get_by_id(prj_id)
    return res


async def get_lang_by_id(lang_id: uuid.UUID) -> Language:
    session = async_session()
    async with session.begin():
        lang_dal = LanguagesDAL(session)
        res = await lang_dal.get_by_id(lang_id)
    return res


async def get_prj_locs(prj_id: uuid.UUID) -> List[Localization]:
    session = async_session()
    async with session.begin():
        loc_dal = LocalizationDAL(session)
        locs = await loc_dal.get_list_by_project_id(prj_id)
    return locs


async def update_prj_dub(prj_id: uuid.UUID, dubs) -> bool:
    session = async_session()
    async with session.begin():
        project_dal = ProjectDAL(session)
        await project_dal.update_speech_data(prj_id, dubs)
    return True


async def update_prj_status(prj_id: uuid.UUID, status: StatusEnum):
    session = async_session()
    async with session.begin():
        prj_dal = ProjectDAL(session)
        await prj_dal.update_status(prj_id, status)
    return True


async def update_prj_task_id(prj_id: uuid.UUID, task_id: uuid.UUID):
    session = async_session()
    async with session.begin():
        prj_dal = ProjectDAL(session)
        await prj_dal.update_task_id(prj_id, task_id)
    return True


async def update_loc_task_id(loc_id: uuid.UUID, task_id: uuid.UUID) -> bool:
    session = async_session()
    async with session.begin():
        loc_dal = LocalizationDAL(session)
        await loc_dal.update_task_id(loc_id, task_id)
    return True


async def update_loc_result_name(loc_id: uuid.UUID, result_name: str) -> bool:
    session = async_session()
    async with session.begin():
        loc_dal = LocalizationDAL(session)
        await loc_dal.update_result_path(loc_id, result_name)
    return True


async def update_loc_dub(loc_id: uuid.UUID, dubs) -> bool:
    session = async_session()
    async with session.begin():
        loc_dal = LocalizationDAL(session)
        await loc_dal.update_speech_data(loc_id, dubs)
    return True


async def update_loc_status(loc_id: uuid.UUID, status: StatusEnum):
    session = async_session()
    async with session.begin():
        loc_dal = LocalizationDAL(session)
        await loc_dal.update_status(loc_id, status)
    return True


@celery_app.task(name="process_video", ignore_result=True)
def process_video(prj_id):
    prj_status = StatusEnum.processing
    loop = asyncio.get_event_loop()
    try:
        logger.info(f"Start processing Project({prj_id})")
        loop.run_until_complete(update_prj_status(prj_id, prj_status))

        prj = loop.run_until_complete(get_prj_by_id(prj_id))
        prj_files = ProjectFiles(prj.id)
        wav_path = prj_files.get_file_path(f"{uuid.uuid4()}.wav", checks=False)
        audio_from_video(prj_files.get_file_path(prj.source_name), wav_path)
        dub_task_id = DubService.push(wav_path)
        prj_files.delete_file(os.path.basename(wav_path))
        dubs = DubService.await_result(dub_task_id)
        loop.run_until_complete(update_prj_dub(prj_id, dubs))

        locs = loop.run_until_complete(get_prj_locs(prj_id))
        for loc in locs:
            task = signature("process_subs", args=(loc.id,)).delay()
            loop.run_until_complete(update_loc_task_id(loc.id, task.id))

        prj_status = StatusEnum.processed
        logger.info(f"Project({prj_id}) source successfully processed")
    except Exception as e:
        prj_status = StatusEnum.failed
        logger.error(f"Error while processing project({prj_id})" + "\n" + traceback.format_exc())
    finally:
        loop.run_until_complete(update_prj_status(prj_id, prj_status))
        loop.run_until_complete(update_prj_task_id(prj_id, None))



@celery_app.task(name="process_subs", ignore_result=True)
def process_subs(loc_id):
    loc_status = StatusEnum.processing
    loop = asyncio.get_event_loop()
    try:
        logger.info(f"Start processing Localization({loc_id})")
        loop.run_until_complete(update_loc_status(loc_id, loc_status))

        loc = loop.run_until_complete(get_loc_by_id(loc_id))
        prj = loop.run_until_complete(get_prj_by_id(loc.project_id))

        lang = loop.run_until_complete(get_lang_by_id(loc.target_language_id))

        prj_files = ProjectFiles(prj.id)
        reformer = SRT_reformer()
        for item in prj.parsed_speech_data:
            reformer.add_fragment(SRT_fragment(item["start"], item["end"], item["text"]))

        translated_dubs = reformer.translate(lang.api_name)
        reformer.synthesize(prj_files, loc.target_voice_name)
        audio_name = reformer.combine(prj_files)

        
        result_path = prj_files.get_file_path(
            str(uuid.uuid4()) + os.path.splitext(prj.source_name)[1],
            checks=False
        )
        merge_audio_and_video(
            prj_files.get_file_path(prj.source_name),
            prj_files.get_file_path(audio_name),
            result_path
        )
        loop.run_until_complete(update_loc_dub(loc_id, translated_dubs))
        loop.run_until_complete(update_loc_result_name(loc_id, os.path.basename(result_path)))
        loc_status = StatusEnum.processed

        logger.info(f"Localization({loc_id}) source successfully processed")
    except Exception as e:
        loc_status = StatusEnum.failed
        logger.error(f"Error while processing localization({loc_id})\n{traceback.format_exc()}")
    finally:
        loop.run_until_complete(update_loc_status(loc_id, loc_status))
        loop.run_until_complete(update_loc_task_id(loc_id, None))
        if loc_status == StatusEnum.processed:
            loc = loop.run_until_complete(get_loc_by_id(loc_id))
            user = loop.run_until_complete(get_user_by_id(prj.user_id))
            loop.run_until_complete(send_localization_done(user, lang, loc, prj))
        reformer.cleanup(prj_files)



class SRT_fragment:
    def __init__(self, start_time, end_time, text):
        self.start_time = start_time
        self.end_time = end_time
        self.text = text
        self.audio = None


class SRT_reformer:
    frag_temp_name = "frag_{}.mp3"
    result_name = "result.wav"

    def __init__(self):
        self.srt_array: List[SRT_fragment] = []

    def _strip_silence(self, audio_segment, silence_thresh=-50, chunk_size=10):
        nonsilent_chunks = detect_nonsilent(audio_segment, min_silence_len=chunk_size, silence_thresh=silence_thresh)
        start_trim = nonsilent_chunks[0][0]
        end_trim = nonsilent_chunks[-1][1]
        trimmed_audio = audio_segment[start_trim:end_trim]
        return trimmed_audio

    def add_fragment(self, fragment: SRT_fragment):
        self.srt_array.append(fragment)

    def cleanup(self, prj_files: ProjectFiles):
        prj_files.delete_file(self.result_name)
        for i in range(len(self.srt_array)):
            prj_files.delete_file(self.frag_temp_name.format(i))

    def translate(self, target_lang: str):
        result = []
        for fragment in self.srt_array:
            task_id = TransService.push(fragment.text, target_lang)
            fragment.text = TransService.await_result(task_id)
            result.append({
                "text": fragment.text,
                "start": fragment.start_time,
                "end": fragment.end_time
            })
        return result

    def synthesize(self, prj_files: ProjectFiles, target_voice_name: str):
        for i, item in enumerate(self.srt_array):
            bytes = SyntService.synt(item.text, target_voice_name)
            prj_files.store_by_bytes(bytes, self.frag_temp_name.format(i))

    def combine(self, prj_files: ProjectFiles):
        first_start = int(self.srt_array[0].start_time * 1000)
        result = AudioSegment.silent(duration=first_start, frame_rate=48000)

        for i, item in enumerate(self.srt_array):
            fname = prj_files.get_file_path(self.frag_temp_name.format(i))

            aseg = AudioSegment.from_file(fname)
            aseg = self._strip_silence(aseg)
            dur_sil = int((item.end_time - item.start_time - aseg.duration_seconds) * 1000)
            if dur_sil > 0:
                self.srt_array[i].audio = aseg + AudioSegment.silent(duration=dur_sil, frame_rate=48000)
            else:
                self.srt_array[i].audio = aseg

        for i, item in enumerate(self.srt_array[:-1]):
            dur_sil = int((self.srt_array[i+1].start_time - self.srt_array[i].end_time) * 1000)
            self.srt_array[i].audio += AudioSegment.silent(duration=dur_sil, frame_rate=48000)

        for item in self.srt_array:
            result += item.audio

        result.export(prj_files.get_file_path(self.result_name, checks=False), format='wav')
        return self.result_name

