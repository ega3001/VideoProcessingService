import subprocess
import os


def preview_from_video(video_path: str, result_path: str) -> bool:
    cmd = [
        "ffmpeg",
        "-ss",
        "00:00:01.00",
        "-i",
        video_path,
        "-vframes",
        "1",
        result_path,
    ]
    subprocess.Popen(cmd).wait()
    if not os.path.exists(result_path):
        raise RuntimeError(f"Could not make preview from video({video_path})")
    return True


def audio_from_video(video_path: str, result_path: str) -> bool:
    cmd = ["ffmpeg", "-i", video_path, result_path]
    subprocess.Popen(cmd).wait()
    if not os.path.exists(result_path):
        raise RuntimeError(f"Could not extract audio from video({video_path})")
    return True


def merge_audio_and_video(video_path: str, audio_path: str, result_path: str) -> bool:
    audio_ratio = source_duration(audio_path) / source_duration(video_path)
    cmd = [
        "ffmpeg",
        "-i",
        video_path,
        "-filter_complex",
        f'amovie={audio_path}:loop=0,asetpts=N/SR/TB,volume=5.0,atempo={audio_ratio}[audio];[0:a]volume=0.05[sa];[sa][audio]amix[fa]',
        "-map",
        "0:v",
        "-map",
        "[fa]",
        "-c:v",
        "copy",
        "-ac",
        "2",
        "-shortest",
        result_path,
    ]
    subprocess.Popen(cmd).wait()
    if not os.path.exists(result_path):
        raise RuntimeError(f"Could not replace audio in video({video_path})")
    return True


def source_duration(source_path: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        source_path,
    ]
    return float(subprocess.check_output(cmd).strip())
