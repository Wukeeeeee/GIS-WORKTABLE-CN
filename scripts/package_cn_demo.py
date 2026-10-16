"""从源码清单生成 CN 演示提交包，不带本机配置、凭据或会话。"""
from contextlib import closing
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit, parse_qs
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['GISWTB_PROFILE'] = 'cn'
from backend.services.network_policy import check_data_url

EXCLUDED = {'.git', '.serena', '.workbuddy', '.venv', 'node_modules', '__pycache__', 'cache', 'logs', 'output', 'uploads'}
SECRET = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{24,}|\b(?:ghp|github_pat)_[A-Za-z0-9_]{30,}|\bAKIA[A-Z0-9]{16}\b')


def build_package():
    paths = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    files = []
    for name in sorted(set(paths)):
        path = ROOT / name
        if not name or not path.is_file() or path.is_symlink() or EXCLUDED.intersection(Path(name).parts):
            continue
        if Path(name).name.startswith('.env') or Path(name).name == 'apikey.txt' or path.suffix.lower() in {'.db', '.sqlite', '.sqlite3', '.pyc', '.log'}:
            continue
        if path.stat().st_size < 2_000_000 and 'frontend/vendor/' not in name:
            try:
                text = path.read_text(encoding='utf-8')
            except UnicodeError:
                text = ''
            if SECRET.search(text):
                raise ValueError(f'疑似密钥，停止打包（值已隐藏）: {name}')
        files.append((name, path))
    output = ROOT / 'output' / 'GIS-WORKTABLE-CN-demo-2026-10-16.zip'
    output.parent.mkdir(exist_ok=True)
    count = 0
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for name, path in files:
            bundle.write(path, 'GIS-WORKTABLE-CN/' + name)
        catalog = ROOT / 'data' / 'gis_services.db'
        if catalog.exists():
            # 重建副本而非 backup/delete，确保副本页内没有被删数据的残留。
            with tempfile.TemporaryDirectory() as tmp:
                demo = Path(tmp) / 'gis_services.db'
                with closing(sqlite3.connect(f'file:{catalog.resolve().as_posix()}?mode=ro', uri=True)) as source, closing(sqlite3.connect(demo)) as target:
                    for (sql,) in source.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name IN ('master','layers','ecosystem')"):
                        target.execute(sql)
                    columns = [r[1] for r in source.execute('PRAGMA table_info(master)')]
                    id_index, url_index = columns.index('service_id'), columns.index('service_url')
                    kept = []
                    for row in source.execute('SELECT * FROM master'):
                        url = row[url_index]
                        try:
                            check_data_url(url)
                            if any(k.lower() in {'key', 'tk', 'token', 'api_key', 'password', 'secret', 'access_token'} for k in parse_qs(urlsplit(url).query)):
                                continue
                            if SECRET.search(str(row)):
                                continue
                        except (ValueError, TypeError):
                            continue
                        target.execute('INSERT INTO master VALUES (' + ','.join('?' for _ in row) + ')', row)
                        kept.append(row[id_index])
                        count += 1
                    for sid in kept:
                        for row in source.execute('SELECT * FROM layers WHERE service_id=?', (sid,)):
                            target.execute('INSERT INTO layers VALUES (?,?,?)', row)
                    target.commit()
                bundle.write(demo, 'GIS-WORKTABLE-CN/data/gis_services.db')
    print(f'Package: {output}')
    print(f'Source files: {len(files)}; approved catalog services: {count}; size: {output.stat().st_size / 1024**2:.1f} MB')
    return output


if __name__ == '__main__':
    build_package()
