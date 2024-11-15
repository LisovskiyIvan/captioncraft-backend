import os
import wave
import json
import subprocess
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment




def transcribe_audio_to_srt(audio_path, vosk, output_srt, unique_id):
    model = Model(vosk)
   
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_channels(1).set_frame_rate(16000)

    wav_path = f"temp{unique_id}.wav"
    audio.export(wav_path, format="wav")

    wf = wave.open(wav_path, "rb")
    recognizer = KaldiRecognizer(model, wf.getframerate())
    recognizer.SetWords(True)
    
    with open(output_srt, 'w', encoding='utf-8') as srt_file:
        idx = 1
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                for word in result.get('result', []):
                    start_time = word['start']
                    end_time = word['end']
                    start_srt = format_timestamp(start_time)
                    end_srt = format_timestamp(end_time)
                    text = word['word']

                    srt_file.write(f"{idx}\n")
                    srt_file.write(f"{start_srt} --> {end_srt}\n")
                    srt_file.write(f"{text}\n\n")
                    idx += 1
        final_result = json.loads(recognizer.FinalResult())
        for word in final_result.get('result', []):
            start_time = word['start']
            end_time = word['end']
            start_srt = format_timestamp(start_time)
            end_srt = format_timestamp(end_time)
            text = word['word']

            srt_file.write(f"{idx}\n")
            srt_file.write(f"{start_srt} --> {end_srt}\n")
            srt_file.write(f"{text}\n\n")
            idx += 1

    wf.close()
    os.remove(wav_path)
    print(f"SRT file saved at: {output_srt}")

def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format: hh:mm:ss,ms"""
    millis = int((seconds - int(seconds)) * 1000)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02}:{m:02}:{s:02},{millis:03}"

def add_subtitles_to_video(video_file, audio_file, srt_file='subtitles.srt', output_file='output_shorts.mp4'):
    if not os.path.exists(video_file):
        print(f"Видеофайл '{video_file}' не найден")
        return

    if not os.path.exists(audio_file):
        print(f"Аудиофайл '{audio_file}' не найден")
        return

    if not os.path.exists(srt_file):
        print(f"Файл субтитров '{srt_file}' не найден")
        return
    command = [
        "ffmpeg",
        "-y",
        "-i", video_file,
        "-i", audio_file,
        "-vf", f"subtitles={srt_file}:force_style='Alignment=2,Fontsize=22,MarginV=35'",
        "-c:v", "h264",
        "-c:a", "aac",
        "-preset", "fast",
        output_file
    ]

    subprocess.run(command, check=True)
    print(f"Видео с субтитрами сохранено как: {output_file}")



def extract_audio_from_video(video_file, output_audio_file):
    if not video_file:
        print(f"Видеофайл '{video_file}' не найден")
        return

    command = [
        "ffmpeg",
        "-y",
        "-i", video_file,
        "-vn",
        "-acodec", "pcm_s16le",
        "-q:a", "4",
        output_audio_file
    ]

    subprocess.run(command, check=True)
    print(f"Аудио из видео сохранено как: {output_audio_file}")



def create_shorts_video(video_file, audio_file, vosk='vosk-model-small-en-us-0.15', output_file="output_shorts.mp4", srt_file='subtitles.srt'):
    transcribe_audio_to_srt(audio_file, vosk, srt_file, output_file )
    add_subtitles_to_video(video_file, audio_file, srt_file, output_file)
    if os.path.exists(srt_file):
        os.remove(srt_file)
        print(f"Временный файл {srt_file} удален.")


