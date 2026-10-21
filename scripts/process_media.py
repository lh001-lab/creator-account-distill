# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "imageio-ffmpeg", "numpy",
#   "mlx-whisper; sys_platform == 'darwin' and platform_machine == 'arm64'",
#   "faster-whisper; sys_platform != 'darwin' or platform_machine != 'arm64'",
# ]
# ///
"""Local ASR and independently resumable frame extraction. Never uploads source media."""
import argparse
import hashlib
import json
import platform
import subprocess
import tempfile
import wave
from pathlib import Path

VIDEO = {'.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v'}
AUDIO = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.aiff'}


def write_json(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def stamp(seconds):
    ms = max(0, round(seconds * 1000))
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    seconds, ms = divmod(ms, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'


def sequence_path(folder):
    # image2 parses percent signs throughout the output path, not just the filename.
    return str(folder.resolve()).replace('%', '%%') + '/%05d.jpg'


def run_ffmpeg(ffmpeg, args):
    result = subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', *args],
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-1600:].strip() or 'ffmpeg failed')


def process(path, output, backend, model, language, interval, frames_only=False):
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    with path.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    target = output / digest[:16]
    target.mkdir(parents=True, exist_ok=True)
    meta = target / 'status.json'
    old = json.loads(meta.read_text()) if meta.exists() else {}
    if old.get('sha256') not in (None, digest):
        raise RuntimeError('Output hash prefix collision; choose a new output directory')
    status = dict(old)
    status.update(source_file=str(path.resolve()), sha256=digest, human_verified=False)
    status.setdefault('audio_status', 'pending')
    status.setdefault('transcription_status', 'pending')
    status.setdefault('frames_status', 'pending')
    status.setdefault('errors', {})
    same_asr = all(old.get(k) == v for k, v in
                   [('backend', backend), ('model', model), ('language', language)])
    artifacts = ['transcript.json', 'transcript.txt', 'transcript.srt']
    asr_ok = same_asr and old.get('transcription_status') == 'complete' and all((target/f).exists() for f in artifacts)
    if not frames_only and not asr_ok:
        status.update(backend=backend, model=model, language=language,
                      transcription_status='processing', review_flags=[])
        write_json(meta, status)
        try:
            with tempfile.TemporaryDirectory(prefix='creator-asr-') as temp:
                wav = Path(temp) / 'audio.wav'
                run_ffmpeg(ffmpeg, ['-i', str(path), '-vn', '-ac', '1', '-ar', '16000',
                                   '-c:a', 'pcm_s16le', str(wav)])
                with wave.open(str(wav), 'rb') as f:
                    duration = f.getnframes() / f.getframerate()
                    pcm = f.readframes(f.getnframes())
                status.update(audio_status='complete', duration_seconds=duration)
                status['errors'].pop('audio', None)
                write_json(meta, status)
                if backend == 'mlx':
                    import numpy as np
                    import mlx_whisper
                    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768
                    raw = mlx_whisper.transcribe(samples, path_or_hf_repo=model,
                            language=language, temperature=0, condition_on_previous_text=False, verbose=False)
                    segments = [{k:s[k] for k in ['start', 'end', 'text']} for s in raw.get('segments', [])]
                    text = raw.get('text', '')
                else:
                    from faster_whisper import WhisperModel
                    engine = WhisperModel(model, device='cpu', compute_type='int8')
                    generated, _ = engine.transcribe(str(wav), language=language,
                        temperature=0, condition_on_previous_text=False)
                    segments = [dict(start=s.start, end=s.end, text=s.text) for s in generated]
                    text = ''.join(s['text'] for s in segments)
            result = dict(text=text, segments=segments, language=language)
            write_json(target/'transcript.json', result)
            (target/'transcript.txt').write_text(text, encoding='utf-8')
            (target/'transcript.srt').write_text('\n\n'.join(
                f"{i}\n{stamp(s['start'])} --> {stamp(s['end'])}\n{s['text'].strip()}"
                for i,s in enumerate(segments,1)), encoding='utf-8')
            flags = []
            if not segments: flags.append('no_recognized_speech')
            else:
                if segments[0]['start'] > 10: flags.append('late_first_segment_check_intro')
                if duration-segments[-1]['end'] > 15: flags.append('tail_gap_check_ending')
                if duration > 60 and len(text.strip()) < 100: flags.append('short_transcript_check_audio')
            status.update(transcription_status='complete', segment_count=len(segments), review_flags=flags)
            status['errors'].pop('transcription', None)
        except Exception as e:
            if status.get('audio_status') != 'complete': status['audio_status'] = 'failed'
            status['transcription_status'] = 'failed'
            status['errors']['transcription'] = f'{type(e).__name__}: {e}'
        write_json(meta, status)
    if interval > 0 and path.suffix.lower() in VIDEO:
        frames = target/'frames'
        count = len(list(frames.glob('*.jpg'))) if frames.exists() else 0
        frames_ok = old.get('frames_status') == 'complete' and old.get('frame_interval') == interval and count == old.get('frame_count') and count > 0
        if not frames_ok:
            status['frames_status'] = 'processing'
            write_json(meta, status)
            try:
                # Build a complete replacement before discarding any earlier frames.
                with tempfile.TemporaryDirectory(prefix='creator-frames-', dir=target) as temp:
                    temp = Path(temp)
                    run_ffmpeg(ffmpeg, ['-i', str(path), '-an', '-vf',
                        f'scale=540:960:force_original_aspect_ratio=decrease,pad=540:960:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=1/{interval}',
                        sequence_path(temp)])
                    generated = sorted(temp.glob('*.jpg'))
                    if not generated: raise RuntimeError('No extracted frames; try a shorter interval')
                    frames.mkdir(exist_ok=True)
                    for f in frames.iterdir():
                        if f.is_file() and f.suffix in {'.jpg', '.json'}: f.unlink()
                    for f in generated: f.replace(frames/f.name)
                status.update(frames_status='complete', frame_interval=interval, frame_count=len(generated))
                status['errors'].pop('frames', None)
            except Exception as e:
                status['frames_status'] = 'failed'
                status['errors']['frames'] = f'{type(e).__name__}: {e}'
        write_json(meta, status)
    elif path.suffix.lower() not in VIDEO:
        status['frames_status'] = 'not_applicable'
        write_json(meta, status)
    print(json.dumps(dict(source=path.name, output=str(target),
        transcription=status['transcription_status'], frames=status['frames_status']), ensure_ascii=False), flush=True)
    return status['transcription_status'] == 'failed' or (interval > 0 and path.suffix.lower() in VIDEO and status['frames_status'] == 'failed')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('files', nargs='*', type=Path)
    p.add_argument('--input-dir', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--backend', choices=['auto', 'mlx', 'faster'], default='auto')
    p.add_argument('--model')
    p.add_argument('--language', default='zh')
    p.add_argument('--frame-interval', type=float, default=3)
    p.add_argument('--frames-only', action='store_true')
    a = p.parse_args()
    if a.frame_interval < 0: p.error('--frame-interval must be zero or positive')
    backend = a.backend
    if backend == 'auto': backend = 'mlx' if platform.system() == 'Darwin' and platform.machine() == 'arm64' else 'faster'
    model = a.model or ('mlx-community/whisper-small-mlx' if backend == 'mlx' else 'small')
    files = a.files + (sorted(f for f in a.input_dir.rglob('*') if f.suffix.lower() in VIDEO|AUDIO) if a.input_dir else [])
    files = list(dict.fromkeys(f.resolve() for f in files))
    if not files: p.error('Provide files or an --input-dir containing media')
    a.output.mkdir(parents=True, exist_ok=True)
    failed = 0
    for f in files:
        try: failed += bool(process(f,a.output,backend,model,a.language,a.frame_interval,a.frames_only))
        except Exception as e:
            failed += 1
            print(json.dumps(dict(source=f.name, error=f'{type(e).__name__}: {e}'), ensure_ascii=False), flush=True)
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__': main()
