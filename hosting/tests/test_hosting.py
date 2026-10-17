"""Contract and access-boundary tests against the actual frozen reader database."""
import json
import os
import shutil
import sqlite3
import re
from pathlib import Path
import sys
from urllib.parse import urlencode

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import HostedReader


@pytest.fixture(scope='module')
def app(tmp_path_factory):
    source = Path(os.environ.get('TEST_BUNDLE', str(Path(__file__).resolve().parents[2])))
    if not (source / 'build/atlas.sqlite').exists():
        from principia_legacy.storage import build
        build(source, '1.4.1-exploratory')
    bundle = tmp_path_factory.mktemp('hosted-reader')
    (bundle / 'build').mkdir()
    shutil.copyfile(source / 'build/atlas.sqlite', bundle / 'build/atlas.sqlite')
    with sqlite3.connect((bundle / 'build/atlas.sqlite').resolve().as_uri() + '?mode=ro', uri=True) as db:
        current = db.execute("SELECT value FROM metadata WHERE key='current_release'").fetchone()[0]
        releases = [r[0] for r in db.execute('SELECT id FROM snapshots') if re.fullmatch(r'\d+\.\d+\.\d+-exploratory', r[0])]
    config = {'default_release': current,
              'public_releases': releases,
              'hosts': ['atlas.example.org', 'localhost', '127.0.0.1']}
    (bundle / 'hosting.json').write_text(json.dumps(config))
    return HostedReader(bundle)


def request(app, path, params=None, method='GET', host='atlas.example.org'):
    result = {}
    def start(status, headers):
        result['status'] = int(status.split()[0])
        result['headers'] = dict(headers)
    raw = b''.join(app({'REQUEST_METHOD': method, 'PATH_INFO': path,
                       'QUERY_STRING': params if isinstance(params, str) else urlencode(params or {}),
                       'HTTP_HOST': host}, start))
    result['raw'] = raw
    result['json'] = json.loads(raw) if raw else None
    return result


def test_pinned_release_and_info(app):
    result = request(app, '/api/info')
    assert result['status'] == 200
    info = result['json']
    assert info['release_id'] == app.release
    assert info['current_release_id'] == app.release
    assert set(info['releases']) == app.releases
    assert info['counts']['contribution'] > 1000
    assert info['human_reviewed'] == 0
    assert result['headers']['Content-Security-Policy']


@pytest.mark.parametrize('method', ['POST','PUT','PATCH','DELETE','OPTIONS','TRACE','CONNECT'])
def test_read_only(app, method):
    result = request(app, '/api/info', method=method)
    assert result['status'] == 405
    assert result['headers']['Allow'] == 'GET, HEAD'


@pytest.mark.parametrize('host', ['evil.example','atlas.example.org.evil.example','atlas.example.org:99',''])
def test_host_boundary(app, host):
    assert request(app, '/api/info', host=host)['status'] == 403


@pytest.mark.parametrize('path', ['/api/info','/api/search','/api/brief','/api/changes'])
def test_private_snapshot_denied(app, path):
    assert request(app, path, {'release':'working'})['status'] == 404


def test_private_comparison_denied(app):
    assert request(app, '/api/changes', {'from':'working'})['status'] == 400


def test_head_and_health(app):
    get = request(app, '/api/info')
    head = request(app, '/api/info', method='HEAD')
    assert head['raw'] == b''
    assert head['headers']['Content-Length'] == str(len(get['raw']))
    assert request(app, '/healthz')['json']['release_id'] == app.release


@pytest.mark.parametrize('query', ['q=a&q=b','q='+'x'*501,'limit=999999','hops=7','offset=-1','limit=nan'])
def test_bounded_queries(app, query):
    assert request(app, '/api/search', query)['status'] == 400


def test_url_limit(app):
    assert request(app, '/api/search', 'x='+'a'*8192)['status'] == 414


@pytest.mark.parametrize('path', ['/.secrets/principia-legacy.env','/build/atlas.sqlite','/api/author','/api/apply','/api/contributions/missing'])
def test_private_paths_unavailable(app, path):
    assert request(app, path)['status'] == 404


def test_query_and_release_cache_isolation(app):
    first = request(app, '/api/search', {'q':'entropy'})
    second = request(app, '/api/search', {'q':'Hamiltonian'})
    assert first['status'] == second['status'] == 200
    assert first['json']['results'] != second['json']['results']
    for release in app.releases:
        out = request(app, '/api/info', {'release':release})
        assert out['json']['release_id'] == release
    assert request(app, '/api/search', {'q':'entropy'})['raw'] == first['raw']


def test_reader_workflows(app):
    result = request(app, '/api/search', {'q':'relativity'})['json']
    node = result['results'][0]['id']
    assert request(app, '/api/contributions/'+node)['status'] == 200
    assert request(app, '/api/neighborhood', {'seed':node})['status'] == 200
    assert request(app, '/api/dossiers')['status'] == 200
    assert request(app, '/api/brief', {'q':'relativity'})['status'] == 200
    if hasattr(app.Atlas, 'people'):
        people = request(app, '/api/people', {'q':'Einstein'})
        assert people['status'] == 200
        entries = people['json'].get('people', people['json'].get('results', []))
        assert entries
        assert request(app, '/api/people/'+entries[0]['id'])['status'] == 200
    old = sorted(app.releases)[0]
    assert request(app, '/api/changes', {'from':old})['status'] == 200


def test_database_is_read_only(app):
    atlas = app.Atlas(app.root, app.release)
    try:
        with pytest.raises(Exception, match='readonly'):
            atlas.db.execute("DELETE FROM metadata")
    finally:
        atlas.close()


def test_cache_is_bounded(app):
    app = HostedReader(app.root)
    app.cache_budget = 1024
    for query in ('mechanics','gravity','quantum','information'):
        assert request(app, '/api/search', {'q':query})['status'] == 200
    # A single item is permitted only if it fits the configured budget.
    assert app.cache_size <= app.cache_budget


def test_public_exploration_index_is_capped_read_only_and_snapshot_pinned(app):
    first = request(app, '/api/exploration-index', {'limit': 200})
    assert first['status'] == 200
    assert len(first['json']['entries']) == 200
    assert first['json']['total'] == request(app, '/api/info')['json']['counts']['contribution']
    assert first['json']['release_id'] == app.release
    second = request(app, '/api/exploration-index', {'limit': 200, 'offset': 200})
    assert first['json']['snapshot_hash'] == second['json']['snapshot_hash']
    assert {e['id'] for e in first['json']['entries']}.isdisjoint(e['id'] for e in second['json']['entries'])
    assert request(app, '/api/exploration-index', {'limit': 201})['status'] == 400
    assert request(app, '/api/exploration-index', {'release': 'working'})['status'] == 404
    assert request(app, '/api/exploration-index', method='POST')['status'] == 405
    csp = first['headers']['Content-Security-Policy']
    assert 'https://api.siliconflow.cn' in csp
    assert 'https://api.crossref.org' in csp
    assert 'https://www.ebi.ac.uk' in csp
    assert "connect-src *" not in csp


def test_work_search_detail_and_subjects(app):
    info = request(app, '/api/info')['json']
    if not info.get('catalog_counts', {}).get('works'):
        pytest.skip('External test bundle predates the work catalogue')
    result = request(app, '/api/search', {'q': 'Allan Turing'})['json']
    assert any(p['name'] == 'Alan Turing' for p in result['people'])
    assert result['works']
    work = request(app, '/api/works/' + result['works'][0]['id'])
    assert work['status'] == 200
    assert work['json']['release_id'] == app.release
    assert work['json']['sources'] and work['json']['contributions']
    assert request(app, '/api/works', {'topic': 'C1002'})['json']['works']
    people = request(app, '/api/people', {'pillar': 'physics'})['json']['people']
    assert people and all('physics' in p['subjects'] for p in people)
    assert request(app, '/api/works', method='POST')['status'] == 405
