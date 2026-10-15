"""WSGI hosting adapter for immutable Principia-Legacy reader bundles.

Gunicorn runs one request per worker; SQLite connections are request-local.
No authoring routes, source downloads, credentials, or external calls exist here.
"""

from collections import OrderedDict
from http import HTTPStatus
import inspect
import json
import logging
import os
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs


CSP = "default-src 'self'; connect-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"


class HostedReader:
    def __init__(self, root, atlas_class=None):
        self.root = Path(root).resolve()
        self.config = json.loads((self.root / 'hosting.json').read_text())
        self.release = self.config['default_release']
        self.releases = frozenset(self.config['public_releases'])
        if self.release not in self.releases or any(
            not re.fullmatch(r'\d+\.\d+\.\d+-exploratory', r) for r in self.releases
        ):
            raise ValueError('Only explicitly published frozen releases may be hosted')
        self.hosts = frozenset(self.config['hosts'])
        if atlas_class is None:
            sys.path.insert(0, str(self.root / 'src'))
            from principia_legacy.storage import Atlas
            atlas_class = Atlas
        self.Atlas = atlas_class
        self.search_offset = 'offset' in inspect.signature(atlas_class.search).parameters
        self.cache = OrderedDict()
        self.cache_size = 0
        self.cache_budget = 32 * 1024 * 1024
        # Refuse startup when a configured release cannot be opened.
        for release in self.releases:
            atlas = self.Atlas(self.root, release)
            atlas.close()

    def dispatch(self, atlas, path, q):
        human = q.get('human') == 'true'
        if path == '/api/info':
            out = atlas.info()
            out['releases'] = sorted(self.releases)
            out['current_release_id'] = self.release
            return out
        if path == '/api/dossiers':
            return atlas.dossiers()
        if path == '/api/search':
            args = (q.get('q', ''), q.get('pillar'), human, q.get('limit', 40))
            return atlas.search(*args, **({'offset': q.get('offset', 0)} if self.search_offset else {}))
        if path == '/api/people' and hasattr(atlas, 'people'):
            return atlas.people(q.get('q', ''), q.get('limit', 60), q.get('offset', 0), human)
        if path.startswith('/api/people/') and hasattr(atlas, 'person'):
            return atlas.person(path.rsplit('/', 1)[1], human)
        if path == '/api/neighborhood':
            layers = None if not q.get('layers') else ([] if q['layers'] == 'none' else q['layers'].split(','))
            return atlas.neighborhood(q.get('dossier'), q.get('seed'), layers, human,
                                      q.get('limit', 80), q.get('hops', 1), q.get('direction', 'both'))
        if path.startswith('/api/contributions/'):
            return atlas.inspect(path.rsplit('/', 1)[1], 'contribution')
        if path.startswith('/api/relations/'):
            return atlas.inspect(path.rsplit('/', 1)[1], 'relation')
        if path == '/api/brief':
            return atlas.brief(q.get('q', ''), dossier=q.get('dossier'))
        if path == '/api/changes':
            return atlas.changes(q['from'])
        raise KeyError('Unknown API route')

    def __call__(self, environ, start_response):
        method = environ.get('REQUEST_METHOD', '')
        path = environ.get('PATH_INFO', '')
        query = environ.get('QUERY_STRING', '')
        host = environ.get('HTTP_HOST', '').lower()
        if host not in self.hosts:
            return self.reply(start_response, method, 403, {'error': 'Invalid host'})
        if method not in ('GET', 'HEAD'):
            return self.reply(start_response, method, 405, {'error': 'Reader is read-only'})
        if len(path) + len(query) > 8192:
            return self.reply(start_response, method, 414, {'error': 'URL too long'})
        if path == '/healthz':
            return self.reply(start_response, method, 200, {'status': 'ok', 'release_id': self.release})
        if not path.startswith('/api/') or any(c in path for c in ('\x00', '\\')):
            return self.reply(start_response, method, 404, {'error': 'Unknown API route'})
        atlas = None
        try:
            parsed = parse_qs(query, keep_blank_values=True, max_num_fields=25)
            if any(len(v) != 1 for v in parsed.values()):
                raise ValueError('Repeated query parameters are not accepted')
            q = {k: v[0] for k, v in parsed.items()}
            release = q.get('release') or self.release
            if release not in self.releases:
                raise KeyError('Snapshot is not published')
            if len(q.get('q', '')) > 500:
                raise ValueError('Search is limited to 500 characters')
            for field, maximum in (('limit', 200), ('offset', 10000), ('hops', 6)):
                if field in q and not 0 <= int(q[field]) <= maximum:
                    raise ValueError(f'{field} is outside the supported range')
            if path == '/api/changes' and q.get('from') not in self.releases:
                raise ValueError('Comparison requires a published source release')
            key = (release, path, tuple(sorted(q.items())))
            if key in self.cache:
                payload = self.cache.pop(key)
                self.cache[key] = payload
                return self.reply(start_response, method, 200, payload)
            atlas = self.Atlas(self.root, release)
            payload = json.dumps(self.dispatch(atlas, path, q), ensure_ascii=False).encode()
            if len(payload) <= min(1024 * 1024, self.cache_budget):
                while self.cache and (self.cache_size + len(payload) > self.cache_budget or len(self.cache) >= 128):
                    _, previous = self.cache.popitem(last=False)
                    self.cache_size -= len(previous)
                self.cache[key] = payload
                self.cache_size += len(payload)
            return self.reply(start_response, method, 200, payload)
        except KeyError:
            return self.reply(start_response, method, 404, {'error': 'Route, record, or published snapshot not found'})
        except (ValueError, TypeError):
            return self.reply(start_response, method, 400, {'error': 'Invalid reader query'})
        except Exception:
            logging.exception('Reader request failed')
            return self.reply(start_response, method, 500, {'error': 'Reader temporarily unavailable'})
        finally:
            if atlas is not None:
                atlas.close()

    @staticmethod
    def reply(start_response, method, status, value):
        body = value if isinstance(value, bytes) else json.dumps(value).encode()
        headers = [('Content-Type', 'application/json; charset=utf-8'),
                   ('Content-Length', str(len(body))), ('Cache-Control', 'no-store'),
                   ('X-Content-Type-Options', 'nosniff'), ('Referrer-Policy', 'no-referrer'),
                   ('Content-Security-Policy', CSP)]
        if status == 405:
            headers.append(('Allow', 'GET, HEAD'))
        start_response(f'{status} {HTTPStatus(status).phrase}', headers)
        return [b'' if method == 'HEAD' else body]


def create_app():
    return HostedReader(os.environ['PRINCIPIA_BUNDLE'])
