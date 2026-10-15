"""Isolated optional PDF parser, invoked with a bounded process timeout."""

import io
import json
import re
import sys


def main():
    from pypdf import PdfReader

    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (50, 50))
    except (ImportError, ValueError, OSError):
        pass
    raw = sys.stdin.buffer.read(12_000_001)
    if len(raw) > 12_000_000:
        raise ValueError("PDF exceeds input cap")
    pdf = PdfReader(io.BytesIO(raw))
    lines = []
    characters = 0
    for page_no, page in enumerate(pdf.pages[:150], 1):
        if characters > 750_000:
            break
        text = page.extract_text() or ""
        for part in re.split(r"\n\s*\n", text):
            part = re.sub(r"\s+", " ", part).strip()
            if len(part) > 50:
                lines.append({"selector": f"PDF page {page_no}", "text": part})
                characters += len(part)
    print(
        json.dumps(
            {"title": str((pdf.metadata or {}).get("/Title", "")), "lines": lines},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
