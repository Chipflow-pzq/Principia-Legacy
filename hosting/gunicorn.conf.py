bind = '127.0.0.1:8766'
workers = 2
worker_class = 'sync'
threads = 1
timeout = 15
graceful_timeout = 20
max_requests = 2000
max_requests_jitter = 200
limit_request_line = 8190
limit_request_fields = 40
limit_request_field_size = 8190
accesslog = '-'
errorlog = '-'
access_log_format = '%(h)s %(m)s %(U)s %(s)s %(L)s'
forwarded_allow_ips = '127.0.0.1'
# No preloading: each worker creates its own adapter and request-local connections.
preload_app = False
