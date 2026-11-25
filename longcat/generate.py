"""Prepare and run LongCat Avatar 1.6 jobs on an already configured GPU host."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import uuid

ROOT = Path(__file__).resolve().parent
RUNTIME = Path(os.environ.get("LONGCAT_RUNTIME", ROOT / "runtime")).resolve()
FIRST_SECONDS = 93 / 25
NEXT_SECONDS = 80 / 25


def segments_for(duration):
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("O áudio precisa ter duração positiva e finita.")
    return 1 + max(0, math.ceil((duration - FIRST_SECONDS) / NEXT_SECONDS))


def audio_duration(path):
    result = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=duration:format=duration", "-of", "json", str(path),
    ], text=True)
    metadata = json.loads(result)
    if not metadata.get("streams"):
        raise ValueError("O arquivo não contém áudio.")
    duration = float(metadata["format"]["duration"])
    segments_for(duration)
    return duration


def make_job(image, audio, prompt, *, test=False, resolution="480p", runtime=None):
    runtime = Path(runtime or RUNTIME).resolve()
    image, audio = Path(image).resolve(), Path(audio).resolve()
    for path in (image, audio):
        if not path.is_file():
            raise ValueError(f"Arquivo não encontrado: {path}")
    if not prompt.strip():
        raise ValueError("Descreva a pessoa e a cena em inglês.")
    if resolution not in ("480p", "720p"):
        raise ValueError("Resolução inválida.")
    duration = audio_duration(audio)
    count = 1 if test else segments_for(duration)
    work = runtime / "jobs" / uuid.uuid4().hex
    work.mkdir(parents=True)
    request = work / "request.json"
    request.write_text(json.dumps({
        "prompt": prompt.strip(), "cond_image": str(image),
        "cond_audio": {"person1": str(audio)},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    upstream = runtime / "LongCat-Video"
    command = [
        "torchrun", "--standalone", "--nproc_per_node=1",
        "run_demo_avatar_single_audio_to_video.py", "--context_parallel_size=1",
        "--stage_1=ai2v", f"--checkpoint_dir={upstream / 'weights/LongCat-Video-Avatar-1.6'}",
        f"--input_json={request}", f"--output_dir={work / 'raw'}",
        f"--num_segments={count}", "--model_type=avatar-v1.6", "--use_distill",
        "--use_int8", "--lora_path=loraB/lora.safetensors",
        "--mix_steps=4", "--mix_alpha=1.0", f"--resolution={resolution}",
    ]
    return {
        "work": work, "cwd": upstream, "command": command, "audio": audio,
        "duration": min(duration, FIRST_SECONDS) if test else duration,
        "segments": count, "output": work / "video.mp4",
    }


def run_job(job, report=print):
    if not (job["cwd"] / "run_demo_avatar_single_audio_to_video.py").is_file():
        raise RuntimeError("Execute bash longcat/setup.sh na máquina com GPU primeiro.")
    if not shutil.which("torchrun"):
        raise RuntimeError("Ative o ambiente Conda indicado pelo instalador.")
    # One generation per GPU, including across browser sessions/processes.
    import fcntl
    with (job["cwd"].parent / "generation.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("A GPU já está gerando outro vídeo. Aguarde terminar.") from exc
        log_path = job["work"] / "generation.log"
        with log_path.open("w", encoding="utf-8") as log:
            with subprocess.Popen(job["command"], cwd=job["cwd"], stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, bufsize=1) as process:
                for line in process.stdout:
                    log.write(line)
                    log.flush()
                    report(line.rstrip())
                code = process.wait()
            if code:
                raise RuntimeError(f"A geração falhou. Consulte {log_path}")
        raw_name = "ai2v_demo_1.mp4" if job["segments"] == 1 else f"video_continue_{job['segments']}.mp4"
        raw = job["work"] / "raw" / raw_name
        if not raw.is_file():
            raise RuntimeError(f"O modelo não produziu o vídeo esperado: {raw}")
        subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-i", str(raw), "-i", str(job["audio"]),
            "-map", "0:v:0", "-map", "1:a:0", "-t", str(job["duration"]),
            "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(job["output"]),
        ], check=True)
    return job["output"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--test", action="store_true", help="Gera apenas o primeiro trecho (até 3,72 s).")
    parser.add_argument("--dry-run", action="store_true", help="Prepara o pedido sem usar GPU.")
    parser.add_argument("--resolution", choices=["480p", "720p"], default="480p")
    args = parser.parse_args()
    job = make_job(args.image, args.audio, args.prompt, test=args.test, resolution=args.resolution)
    print(json.dumps({k: str(v) if isinstance(v, Path) else v for k, v in job.items()}, indent=2))
    if not args.dry_run:
        print(run_job(job))


if __name__ == "__main__":
    main()
