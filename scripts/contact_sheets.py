# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Create frame-location boards; inspect original frames for small text or motion claims."""
import argparse
import json
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--index',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--per-page',type=int,default=4)
    a=p.parse_args()
    if a.per_page<1 or a.per_page>8:p.error('--per-page must be 1..8')
    rows=[]
    for item in json.loads(a.index.read_text())['items']:
        for video in item.get('videos',[]):
            folder=video.get('frames_path');frames=sorted(Path(folder).glob('*.jpg')) if folder else []
            if frames:
                chosen=[frames[round((len(frames)-1)*j/3)] for j in range(4)]
                rows.append((f"{item['number']} | {item['id']} | sampled video frames",chosen))
        photos=item.get('image_paths',[])
        # All image attachments are included, not merely four per photo post.
        for offset in range(0,len(photos),4):
            rows.append((f"{item['number']} | {item['id']} | images {offset+1}-{min(offset+4,len(photos))}",photos[offset:offset+4]))
        if not item.get('videos') and not photos:rows.append((f"{item['number']} | {item['id']} | missing media",[]))
    a.output.mkdir(parents=True,exist_ok=True)
    for start in range(0,len(rows),a.per_page):
        page=Image.new('RGB',(760,355*a.per_page),'white');draw=ImageDraw.Draw(page)
        for row,(label,files) in enumerate(rows[start:start+a.per_page]):
            y=row*355;draw.text((8,y+4),label,fill='black')
            for col,f in enumerate(files):
                with Image.open(f) as im:pic=ImageOps.contain(im.convert('RGB'),(185,325))
                page.paste(pic,(col*190,y+25))
        page.save(a.output/f'board-{start//a.per_page+1:03d}.jpg',quality=90)
    print(json.dumps(dict(rows=len(rows),boards=(len(rows)+a.per_page-1)//a.per_page)))


if __name__=='__main__':main()
