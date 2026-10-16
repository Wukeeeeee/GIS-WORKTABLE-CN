import io
import zipfile
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.services.file_safety import safe_extract_zip, safe_filename, contained_path


@pytest.fixture
def client():
    return TestClient(main.app)


def test_external_website_and_host_cannot_access_local_api(client):
    assert client.get('/api/health', headers={'Origin': 'https://evil.example'}).status_code == 403
    assert client.get('/api/health', headers={'Host': 'evil.example'}).status_code == 400
    assert client.get('/api/health', headers={'Sec-Fetch-Site': 'cross-site'}).status_code == 403
    assert client.get('/api/health', headers={'Origin': 'http://testserver'}).status_code == 200


def test_cache_configuration_is_not_public(client):
    for path in ['/cache/user_settings.json', '/cache/credentials/.key', '/cache/credentials/credentials.enc', '/cache/projects/index.json']:
        assert client.get(path).status_code == 404


def test_output_cannot_read_outside_directory(tmp_path, monkeypatch, client):
    public = tmp_path / 'output'
    public.mkdir()
    (tmp_path / 'secret.txt').write_text('private')
    (public / 'chart.txt').write_text('public')
    monkeypatch.setattr(main, '_TEMP_OUTPUT_DIR', str(public))
    assert client.get('/output/..%2fsecret.txt').status_code == 400
    response = client.get('/output/chart.txt')
    assert response.status_code == 200 and response.text == 'public'


def test_upload_rejects_path_before_write(client):
    response = client.post('/api/upload', files={'file': ('../escape.csv', b'a,b\n1,2', 'text/csv')})
    assert response.status_code == 400
    assert client.post('/api/upload', files={'file': ('payload.html', b'<script>alert(1)</script>', 'text/html')}).status_code == 400


@pytest.mark.parametrize('name', ['../escape', '..\\escape', 'C:\\escape', '/escape', 'a:b'])
def test_zip_rejected_before_any_file_is_written(tmp_path, name):
    content = io.BytesIO()
    with zipfile.ZipFile(content, 'w') as z:
        z.writestr('valid.txt', 'valid')
        z.writestr(name, 'bad')
    with zipfile.ZipFile(content) as z, pytest.raises(ValueError):
        safe_extract_zip(z, tmp_path)
    assert not list(tmp_path.iterdir())


def test_zip_size_limit_and_valid_archive(tmp_path):
    content = io.BytesIO()
    with zipfile.ZipFile(content, 'w') as z:
        z.writestr('nested/data.txt', 'valid')
    with zipfile.ZipFile(content) as z:
        with pytest.raises(ValueError):
            safe_extract_zip(z, tmp_path, max_bytes=1)
        safe_extract_zip(z, tmp_path)
    assert (tmp_path / 'nested/data.txt').read_text() == 'valid'


def test_cn_proxy_does_not_request_blocked_url(monkeypatch, client):
    monkeypatch.setenv('GISWTB_PROFILE', 'cn')
    request = Mock()
    monkeypatch.setattr('requests.request', request)
    response = client.get('/api/geosource/proxy', params={'url': 'https://overpass-api.de/api/interpreter'})
    assert response.status_code == 403
    request.assert_not_called()


def test_project_paths_cannot_escape():
    from backend.services import project_service
    for function in [project_service._project_dir, project_service._blob_path]:
        with pytest.raises(ValueError):
            function('../escape')


def test_cn_model_endpoints_checked_before_client_creation(monkeypatch):
    from backend.services.network_policy import check_model_url, NetworkPolicyError
    from backend.services.llm_config import build_llm, LLMConfig
    monkeypatch.setenv('GISWTB_PROFILE', 'cn')
    for url in ['https://openrouter.ai/api/v1', 'https://api.deepseek.com.evil.example/v1', 'https://api.deepseek.com@evil.example/v1']:
        with pytest.raises(NetworkPolicyError):
            build_llm(LLMConfig(base_url=url, model='demo', api_key='placeholder'))
    for url in ['https://api.deepseek.com', 'https://open.bigmodel.cn/api/paas/v4', 'http://127.0.0.1:11434/v1']:
        check_model_url(url)


def test_valid_project_roundtrip_still_works(tmp_path, monkeypatch):
    from backend.services import project_service as ps
    monkeypatch.setattr(ps, '_PROJECT_DIR', str(tmp_path))
    monkeypatch.setattr(ps, '_BLOB_DIR', str(tmp_path / 'blobs'))
    monkeypatch.setattr(ps, '_INDEX_PATH', str(tmp_path / 'index.json'))
    monkeypatch.setattr(ps, '_blob_refcount', {})
    saved = ps.save_project(None, '演示工程', 'demo', 'deepseek', {}, [], [])
    imported = ps.import_project(ps.export_project(saved['id']))
    loaded = ps.load_project(imported['id'])
    assert loaded['name'] == '演示工程'
    assert loaded['layers'] == []
