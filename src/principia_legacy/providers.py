"""SiliconFlow adapter. Imported only by explicit network authoring commands."""

import json
import os
import random
import ssl
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from .common import digest, now, read_json, write_json


def tls_context():
    # python.org macOS installations may not have run Install Certificates.command.
    return ssl.create_default_context(
        cafile="/etc/ssl/cert.pem" if Path("/etc/ssl/cert.pem").exists() else None
    )


def credentials(path=None):
    key = os.environ.get("SILICONFLOW_API_KEY")
    if not key and path:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            name, value = line.split("=", 1)
            if name.strip().removeprefix("export ").strip() == "SILICONFLOW_API_KEY":
                key = value.strip().strip("\"'")
    if not key:
        raise ValueError(
            "SILICONFLOW_API_KEY is missing. Use --env-file or the environment."
        )
    return key


def streamed_body(response, receipt, deadline_seconds=180):
    """Read documented SSE output with a size cap and a whole-request deadline."""
    start = time.monotonic()
    content, total, decoded_size, finish, done = [], 0, 0, None, False
    for line in response:
        if time.monotonic() - start > deadline_seconds:
            raise TimeoutError("Streaming response exceeded bounded duration")
        total += len(line)
        # SSE repeats a JSON envelope for each tiny token delta. Bound that
        # transport overhead separately from the actual model output.
        if total > 32_000_000:
            raise ValueError("Provider stream exceeded transport size cap")
        if not line.startswith(b"data:"):
            continue
        data = line[5:].strip()
        if data == b"[DONE]":
            done = True
            break
        event = json.loads(data)
        if event.get("error"):
            raise ValueError("Provider returned a stream error")
        for key, value in (
            ("request_id", event.get("id")),
            ("returned_model", event.get("model")),
            ("usage", event.get("usage")),
        ):
            if value is not None:
                receipt[key] = value
        for choice in event.get("choices", []):
            delta = choice.get("delta", {}).get("content") or ""
            decoded_size += len(delta.encode("utf-8"))
            if decoded_size > 2_000_000:
                raise ValueError("Provider decoded output exceeded size cap")
            content.append(delta)
            if choice.get("finish_reason"):
                finish = choice["finish_reason"]
    if not done:
        raise TimeoutError("Provider stream ended without completion marker")
    return {
        "id": receipt.get("request_id"),
        "model": receipt.get("returned_model"),
        "usage": receipt.get("usage"),
        "choices": [
            {"finish_reason": finish, "message": {"content": "".join(content)}}
        ],
    }


class Provider:
    def __init__(
        self,
        root,
        env_file=None,
        model="deepseek-ai/DeepSeek-V4-Flash",
        base_url="https://api.siliconflow.cn/v1",
    ):
        if base_url != "https://api.siliconflow.cn/v1":
            raise ValueError(
                "Provider endpoint must be explicitly supported; no silent credential forwarding."
            )
        self.root, self.key, self.model, self.base_url = (
            Path(root),
            credentials(env_file),
            model,
            base_url,
        )
        (self.root / ".work/receipts").mkdir(parents=True, exist_ok=True)
        (self.root / ".work/jobs").mkdir(parents=True, exist_ok=True)

    def models(self):
        req = urllib.request.Request(
            self.base_url + "/models", headers={"Authorization": "Bearer " + self.key}
        )
        with urllib.request.urlopen(req, context=tls_context(), timeout=30) as response:
            return [m["id"] for m in json.load(response)["data"]]

    def complete(self, system, payload, task, max_tokens=10000):
        job_id = digest(
            {
                "model": self.model,
                "system": system,
                "payload": payload,
                "task": task,
                "max_tokens": max_tokens,
            }
        )
        job_path = self.root / ".work/jobs" / (job_id + ".json")
        cached = read_json(job_path, {})
        if cached.get("state") == "succeeded":
            return cached["result"], cached["receipt"]
        if (
            cached.get("state") == "running"
            or cached.get("receipt", {}).get("state") == "unknown_possible_charge"
        ):
            raise RuntimeError(
                "This authoring job has an unresolved submitted request. Inspect its receipt before explicitly creating a new task; no automatic resubmission was made."
            )
        request = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,
            "temperature": 0.15,
            "enable_thinking": False,
            "stream": True,
        }
        write_json(
            job_path,
            {"state": "running", "task": task, "started": now(), "model": self.model},
        )
        for attempt in range(3):
            trace = str(uuid.uuid4())
            receipt = {
                "provider": "SiliconFlow",
                "requested_model": self.model,
                "task": task,
                "job_id": job_id,
                "attempt": attempt + 1,
                "trace_id": trace,
                "time": now(),
                "input_hash": digest(payload),
                "prompt_hash": digest(system),
                "state": "running",
            }
            # Persist the attempt before transmission so a killed authoring process
            # cannot make a potentially charged request disappear from the ledger.
            write_json(self.root / ".work/receipts" / (trace + ".json"), receipt)
            try:
                req = urllib.request.Request(
                    self.base_url + "/chat/completions",
                    data=json.dumps(request).encode(),
                    headers={
                        "Authorization": "Bearer " + self.key,
                        "Content-Type": "application/json",
                        "X-Trace-Id": trace,
                    },
                )
                with urllib.request.urlopen(
                    req, context=tls_context(), timeout=180
                ) as response:
                    receipt["provider_trace_id"] = response.headers.get(
                        "x-siliconcloud-trace-id"
                    )
                    body = streamed_body(response, receipt)
                choice = body["choices"][0]
                receipt.update(
                    {
                        "returned_model": body.get("model"),
                        "request_id": body.get("id"),
                        "usage": body.get("usage"),
                        "finish_reason": choice.get("finish_reason"),
                    }
                )
                if body.get("model") != self.model:
                    raise ValueError("Provider returned an unexpected model identity")
                if choice.get("finish_reason") != "stop":
                    raise ValueError("Truncated or incomplete model output")
                content = choice["message"]["content"].strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1].rsplit("```", 1)[0]
                result = json.loads(content)
                if not isinstance(result, dict):
                    raise ValueError("Structured response must be a JSON object")
                receipt.update({"state": "succeeded", "output_hash": digest(result)})
                write_json(self.root / ".work/receipts" / (trace + ".json"), receipt)
                write_json(
                    job_path,
                    {"state": "succeeded", "result": result, "receipt": receipt},
                )
                return result, receipt
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
                # Never serialize request headers or credentials into exceptions/logs.
                code = getattr(exc, "code", None)
                receipt.update(
                    {
                        "state": "failed"
                        if code or isinstance(exc, (ValueError, KeyError))
                        else "unknown_possible_charge",
                        "error_type": type(exc).__name__,
                        "error_detail": str(exc)[:160]
                        if isinstance(exc, (ValueError, KeyError))
                        else None,
                        "http_status": code,
                    }
                )
                write_json(self.root / ".work/receipts" / (trace + ".json"), receipt)
                write_json(job_path, {"state": "failed", "receipt": receipt})
                # A timeout may still be running and charged upstream. Never
                # replay it (including when a resumable campaign is restarted).
                # Retry only an explicit transient HTTP rejection or malformed
                # JSON, with at most two repairs. Truncation/identity/size errors
                # require an author to change the task rather than repeat it.
                retryable = code in {429, 502, 503, 504} or isinstance(
                    exc, json.JSONDecodeError
                )
                if not retryable or attempt == 2:
                    raise RuntimeError(
                        f"Provider job failed ({type(exc).__name__}, HTTP {code}); see receipt {trace}"
                    ) from None
                if isinstance(exc, json.JSONDecodeError):
                    request["messages"] = [
                        *request["messages"][:2],
                        {
                            "role": "user",
                            "content": "The previous response was not valid JSON. Return only one complete JSON object matching the requested contract. Do not use markdown fences.",
                        },
                    ]
                retry_after = (
                    getattr(exc, "headers", {}).get("Retry-After")
                    if getattr(exc, "headers", None)
                    else None
                )
                try:
                    delay = float(retry_after or 2 ** (attempt + 1))
                except (TypeError, ValueError):
                    delay = 2 ** (attempt + 1)
                time.sleep(min(max(delay, 0) + random.random(), 30))
        raise RuntimeError("Provider retry limit exhausted")
