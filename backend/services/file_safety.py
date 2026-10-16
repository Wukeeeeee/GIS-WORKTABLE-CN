"""限制文件操作范围，并在解压前检查整个归档。"""
import os
import stat
from pathlib import Path, PureWindowsPath


def contained_path(root, name):
    base = Path(root).resolve()
    target = (base / name).resolve()
    if not target.is_relative_to(base) or target == base:
        raise ValueError("文件路径超出允许目录")
    return str(target)


def safe_filename(name):
    if not name or name in (".", "..") or any(c in name for c in '/\\:\x00'):
        raise ValueError("文件名不能包含路径或特殊字符")
    return name


def safe_extract_zip(archive, target_dir, max_bytes=300 * 1024 * 1024):
    members = archive.infolist()
    if len(members) > 5000 or sum(m.file_size for m in members) > max_bytes:
        raise ValueError("压缩包超过限制（最多 5000 项、解压后 300MB）")
    for member in members:
        name = member.filename
        windows = PureWindowsPath(name)
        parts = name.replace('\\', '/').split('/')
        if windows.is_absolute() or windows.drive or name.startswith(('/', '\\')) or '..' in parts or ':' in name:
            raise ValueError("压缩包包含不安全路径")
        if stat.S_ISLNK(member.external_attr >> 16):
            raise ValueError("压缩包不允许包含符号链接")
        contained_path(target_dir, name)
    archive.extractall(target_dir)
