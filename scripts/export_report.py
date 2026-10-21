"""Render supplied research and notes as a searchable offline HTML report. Does not invent analysis."""
import argparse
import html
import json
from pathlib import Path
from urllib.parse import urlparse


def esc(value):return html.escape(str(value or ''),quote=True)

def source_link(url,label='原作品'):
    if urlparse(url or '').scheme not in ('https','http'):return '<span>无可用原链接</span>'
    return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{label}</a>'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--index',required=True,type=Path)
    p.add_argument('--notes',required=True,type=Path)
    p.add_argument('--synthesis',type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();index=json.loads(a.index.read_text());notes=json.loads(a.notes.read_text())
    synth=json.loads(a.synthesis.read_text()) if a.synthesis else {}
    title=synth.get('title') or '博主账号内容研究';parts=[]
    parts.append(f'<h1>{esc(title)}</h1>')
    if synth.get('scope'):parts.append(f'<p class="scope">{esc(synth["scope"])}</p>')
    summary=index['summary'];items=index['items']
    # Determine coverage from the supplied notes, not stale audit metadata.
    from audit_account import reviewed
    covered=sum(reviewed(notes.get(x['id']),x['media_kind']) for x in items)
    parts.append(f'<p>清单 {len(items)} 条 · 本地媒体处理完整 {summary["machine_complete"]} 条 · 笔记显式核对 {covered} 条</p>')
    parts.append('<p class="scope">完整转写与关键画面抽查不等同于逐帧人工审片。以下只呈现提供的笔记，未自动补写；来源中的增长与业绩不因收录而得到验证。</p>')
    for chapter in synth.get('chapters',[]):
        parts.append(f'<section><h2>{esc(chapter.get("title"))}</h2>')
        for para in chapter.get('paragraphs',[]):parts.append(f'<p>{esc(para)}</p>')
        ids=chapter.get('source_ids',[])
        if ids:parts.append('<p class="scope">相关作品 '+ ' '.join(f'<a href="#s-{esc(i)}">{esc(i)}</a>' for i in ids)+'</p>')
        parts.append('</section>')
    parts.append('<h2>逐条作品索引</h2><label class="search">搜索方法 标题 案例或建议<input id="search" type="search" placeholder="输入关键词" autocomplete="off"></label><p id="count" aria-live="polite"></p>')
    for x in items:
        n=notes.get(x['id'],{});checked=reviewed(n,x['media_kind']);problems=x.get('problems',[])
        label='已按笔记声明核对' if checked else '待核对或笔记未齐'
        parts.append(f'<article id="s-{esc(x["id"])}"><h3>{esc(x["number"])} {esc(n.get("method") or x["title"])}</h3>')
        parts.append(f'<p class="meta">{esc(x.get("published_at"))} · {esc(x["media_kind"])} · {source_link(x.get("source_url"))} · {label}</p>')
        parts.append(f'<p class="caption">原配文 {esc(x["title"])}</p>')
        if problems:parts.append(f'<p class="pending">资料缺口 {esc(", ".join(problems))}</p>')
        for key,label in [('details','原片内容'),('example','片中案例'),('action','本次应用建议')]:
            parts.append(f'<p><strong>{label}</strong> {esc(n.get(key) or "尚未填写")}</p>')
        if n.get('evidence'):
            evidence='；'.join(f"{e.get('start','?')}–{e.get('end','?')}秒 {e.get('note','')}" for e in n['evidence'])
            parts.append(f'<p class="meta">定位 {esc(evidence)}</p>')
        if n.get('uncertainties'):parts.append(f'<p class="pending">待确认 {esc("；".join(n["uncertainties"]))}</p>')
        if n.get('review',{}).get('visual_scope'):parts.append(f'<p class="meta">画面核对范围 {esc(n["review"]["visual_scope"])}</p>')
        parts.append('</article>')
    css='''body{font-family:system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;color:#20252a;line-height:1.8;max-width:980px;margin:0 auto;padding:40px 24px;background:#fff}h1{font-size:30px;line-height:1.3}h2{margin-top:38px;font-size:23px}h3{font-size:19px;line-height:1.5}p{white-space:pre-wrap}article{border-top:1px solid #d9dfe5;padding:20px 0;scroll-margin-top:20px}a{color:#175a88;overflow-wrap:anywhere}.meta,.caption,.scope{font-size:14px;color:#55616e}.pending{color:#805400}.search{display:block;font-weight:600}input{display:block;width:100%;box-sizing:border-box;margin:8px 0 12px;padding:12px;border:1px solid #8795a4;border-radius:4px;font:inherit}input:focus{outline:3px solid #b8dbf2}article[hidden]{display:none}@media print{.search,#count{display:none}body{max-width:none;padding:0}article{break-inside:avoid}a{color:inherit}}'''
    js='''const input=document.getElementById('search'),articles=[...document.querySelectorAll('article')],count=document.getElementById('count');function filter(){const q=input.value.trim().toLocaleLowerCase();let n=0;for(const a of articles){a.hidden=!a.textContent.toLocaleLowerCase().includes(q);if(!a.hidden)n++}count.textContent=`显示 ${n} / ${articles.length} 条`;}input.addEventListener('input',filter);filter();'''
    output=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{css}</style><body>'+''.join(parts)+f'<script>{js}</script></body></html>'
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(output,encoding='utf-8');print(str(a.output.resolve()))


if __name__=='__main__':main()
