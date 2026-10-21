"""Join public sources, local media and processing evidence. Does not mark human review complete."""
import argparse
import hashlib
import json
from pathlib import Path

VIDEO={'.mp4','.mov','.mkv','.webm','.avi','.m4v'}
AUDIO={'.mp3','.wav','.m4a','.aac','.flac','.ogg','.aiff'}
IMAGE={'.jpg','.jpeg','.png','.webp','.gif'}


def reviewed(note, kind):
    if not note or not all(str(note.get(k,'')).strip() for k in ['method','details','example','action']): return False
    r=note.get('review',{})
    if kind=='video': return r.get('full_transcript_read') is True and r.get('keyframes_checked') is True
    if kind=='image': return r.get('all_images_checked') is True
    return False


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True,type=Path)
    p.add_argument('--media-dir',required=True,type=Path)
    p.add_argument('--processed',required=True,type=Path)
    p.add_argument('--notes',type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    records=json.loads(a.manifest.read_text());notes=json.loads(a.notes.read_text()) if a.notes else {}
    if not isinstance(records,list):p.error('Manifest must be an array')
    normalized={}
    for row in records:
        ident=str(row.get('id') or row.get('aweme_id') or '')
        if not ident:p.error('Every source requires a stable id')
        if ident in normalized:p.error(f'Duplicate source id: {ident}')
        normalized[ident]=row
    files=sorted(f.resolve() for f in a.media_dir.rglob('*') if f.suffix.lower() in VIDEO|AUDIO|IMAGE)
    processed={};digests={}
    for f in a.processed.rglob('status.json'):
        s=json.loads(f.read_text());s['_dir']=str(f.parent.resolve())
        if s.get('source_file'):processed[str(Path(s['source_file']).resolve())]=s
        if s.get('sha256'):digests[s['sha256']]=s
    items=[]
    for i,(ident,row) in enumerate(sorted(normalized.items(),key=lambda x:(str(x[1].get('published_at') or x[1].get('create_time') or ''),x[0])),1):
        paths=[]
        for path in row.get('media_paths') or []:
            f=Path(path);f=f if f.is_absolute() else a.manifest.parent/f
            if f.exists():paths.append(f.resolve())
        if not paths:
            prefix=row.get('file_prefix')
            paths=[f for f in files if (prefix and f.name.startswith(prefix+'_')) or ident in f.stem.split('_')]
        paths=list(dict.fromkeys(paths))
        vids=[f for f in paths if f.suffix.lower() in VIDEO|AUDIO]
        images=[f for f in paths if f.suffix.lower() in IMAGE]
        kind=row.get('media_kind')
        if not kind:kind='image' if row.get('aweme_type')==68 else 'video' if row.get('aweme_type')==0 else 'unknown'
        if kind=='unknown':kind='video' if vids else 'image' if images else 'unknown'
        problems=[];videos=[]
        if not paths:problems.append('missing_media')
        if kind=='video' and not vids:problems.append('missing_video')
        if kind=='image' and not images:problems.append('missing_images')
        for f in vids:
            s=processed.get(str(f))
            if s is None and digests:
                with f.open('rb') as fh: digest=hashlib.file_digest(fh,'sha256').hexdigest()
                s=digests.get(digest)
            if s is None:
                problems.append('unprocessed_video');videos.append(dict(path=str(f),processing_status='missing'));continue
            d=Path(s['_dir']);legacy=s.get('status')=='transcribed'
            asr=s.get('transcription_status')=='complete' or legacy
            asr=asr and all((d/name).exists() for name in ['transcript.json','transcript.txt','transcript.srt'])
            fs=sorted((d/'frames').glob('*.jpg'))
            need_frames=f.suffix.lower() in VIDEO
            frame_ok=(s.get('frames_status')=='complete' or (legacy and s.get('frames_requested'))) and bool(fs)
            if s.get('frame_count') is not None:frame_ok=frame_ok and len(fs)==s['frame_count']
            if not asr:problems.append('incomplete_transcription')
            if need_frames and not frame_ok:problems.append('incomplete_frames')
            videos.append(dict(path=str(f),processing_status='complete' if asr and (frame_ok or not need_frames) else 'incomplete',
                duration_seconds=s.get('duration_seconds'),transcript_path=str(d/'transcript.txt') if (d/'transcript.txt').exists() else None,
                segments_path=str(d/'transcript.json') if (d/'transcript.json').exists() else None,
                frames_path=str(d/'frames') if fs else None,frame_count=len(fs),review_flags=s.get('review_flags',[])))
        note=notes.get(ident,{})
        items.append(dict(id=ident,number=f'{i:03d}',platform=row.get('platform','douyin' if 'aweme_id' in row else ''),
            account_url=row.get('account_url'),title=row.get('title') or row.get('desc_raw') or row.get('desc') or '',
            published_at=row.get('published_at') or row.get('create_time'),source_url=row.get('source_url'),media_kind=kind,
            media_paths=[str(f) for f in paths],image_paths=[str(f) for f in images],videos=videos,
            problems=sorted(set(problems)),human_review_complete=reviewed(note,kind)))
    summary=dict(sources=len(items),video_sources=sum(x['media_kind']=='video' for x in items),
        image_sources=sum(x['media_kind']=='image' for x in items),
        machine_complete=sum(not x['problems'] for x in items),
        duration_seconds=sum(v.get('duration_seconds') or 0 for x in items for v in x['videos']),
        frame_count=sum(v.get('frame_count',0) for x in items for v in x['videos']),
        note_coverage=sum(x['human_review_complete'] for x in items),
        note_status='checked' if a.notes else 'not_supplied',
        items_with_review_flags=sum(any(v.get('review_flags') for v in x['videos']) for x in items))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(dict(summary=summary,items=items),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
