"""F2 Douyin adapter. Requires F2, PyYAML and optionally browser-cookie3 in its Python environment."""
import argparse
import contextlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


def atomic_json(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def domain_allowed(domain):
    domain = domain.lstrip('.').lower()
    return domain == 'douyin.com' or domain.endswith('.douyin.com')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url', required=True)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--max-items', type=int, default=0)
    p.add_argument('--metadata-only', action='store_true')
    p.add_argument('--browser', choices=['chrome', 'edge', 'firefox'])
    p.add_argument('--reuse-authorized', action='store_true')
    a = p.parse_args()
    u = urlparse(a.url)
    if u.scheme != 'https' or u.hostname not in ('www.douyin.com', 'douyin.com') or not u.path.startswith('/user/') or not u.path.removeprefix('/user/').strip('/'):
        p.error('Use a confirmed https://www.douyin.com/user/... account homepage')
    if a.max_items < 0: p.error('--max-items cannot be negative')
    if a.browser and not a.reuse_authorized: p.error('Browser reuse requires existing user authorization and --reuse-authorized')
    account_url = 'https://www.douyin.com' + u.path.rstrip('/')
    root = a.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    manifest = root/'source_manifest.json'
    records = {}
    if manifest.exists():
        for item in json.loads(manifest.read_text()):
            if item.get('account_url') != account_url:
                p.error('Output manifest belongs to a different or unconfirmed account; choose a new directory')
            records[item['id']] = item
    cookie = ''
    if a.browser:
        import browser_cookie3
        jar = getattr(browser_cookie3, a.browser)(domain_name='douyin.com')
        cookie = '; '.join(f'{c.name}={c.value}' for c in jar if domain_allowed(c.domain))
        if not cookie: raise RuntimeError('No Douyin cookie found in the selected browser')
    before = Path.cwd()
    error = None
    with tempfile.TemporaryDirectory(prefix='creator-f2-') as temp:
        temp = Path(temp)
        os.chmod(temp, 0o700)
        config = temp/'auth.yaml'
        # JSON is valid YAML; no credentials appear in process arguments.
        fd = os.open(config, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump({'douyin': {'cookie': cookie, 'naming': '{create}_{aweme_id}',
                'path': str(root/'media'), 'timeout': 20, 'max_retries': 1,
                'max_connections': 3, 'max_tasks': 3, 'page_counts': 20,
                'max_counts': a.max_items}}, f)
        cookie = ''
        # F2's own logs/database/config remain private and ephemeral.
        os.chdir(temp)
        try:
            with (temp/'private-run.log').open('w', encoding='utf-8') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                from f2.apps.douyin.dl import DouyinDownloader
                from f2.apps.douyin.utils import format_file_name
                from f2.cli.cli_commands import main as f2_main
                original = DouyinDownloader.create_download_tasks
                async def capture(self, kwargs, aweme_datas, user_path):
                    items = aweme_datas if isinstance(aweme_datas,list) else [aweme_datas]
                    for item in items:
                        ident = str(item['aweme_id'])
                        is_image = item.get('aweme_type') == 68
                        records[ident] = dict(id=ident, platform='douyin', account_url=account_url,
                            title=item.get('desc_raw') or item.get('desc') or '',
                            published_at=item.get('create_time'),
                            source_url=f'https://www.douyin.com/{"note" if is_image else "video"}/{ident}',
                            media_kind='image' if is_image else 'video',
                            file_prefix=format_file_name('{create}_{aweme_id}', item),
                            media_paths=[])
                    atomic_json(manifest, list(records.values()))
                    if not a.metadata_only:
                        return await original(self, kwargs, aweme_datas, user_path)
                DouyinDownloader.create_download_tasks = capture
                try:
                    f2_main(args=['dy','-c',str(config),'-M','post','-u',account_url,
                        '-p',str(root/'media'),'-o',str(a.max_items),'-s','20','-e','20','-r','1'], standalone_mode=False)
                finally:
                    DouyinDownloader.create_download_tasks = original
        except (Exception, SystemExit) as e:
            if not isinstance(e,SystemExit) or e.code not in (None,0): error = type(e).__name__
        finally:
            os.chdir(before)
    atomic_json(root/'acquisition_status.json',dict(account_url=account_url,
        enumerated=len(records), metadata_only=a.metadata_only,
        collected_at_utc=datetime.now(timezone.utc).isoformat(), requested_max_items=a.max_items,
        scope_claim='all_visible_requested_not_independently_verified' if a.max_items==0 else 'limited_sample',
        status='failed' if error or not records else 'enumerated_pending_media_audit',
        error_type=error))
    print(json.dumps(dict(enumerated=len(records), manifest=str(manifest),
        status='failed' if error or not records else 'pending_media_audit'), ensure_ascii=False))
    if error or not records:
        print('Acquisition incomplete. Check authorized access or the installed F2 adapter version; no raw credential logs were exported.', file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__': main()
