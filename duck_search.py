"""Observe Duck.ai WebSearch tool events without inventing citations."""
import json
from urllib.parse import urlparse

MAX_SOURCES = 5


def is_web_search(event):
    name = str(event.get('toolName') or '').lower()
    return name in ('websearch', 'web_search', 'searchweb', 'web-search')


def _urls(obj, depth=0):
    if depth > 5:
        return
    if isinstance(obj, str):
        if obj.startswith(('https://', 'http://')):
            yield obj
        elif len(obj) < 12000 and obj[:1] in ('{', '['):
            try:
                yield from _urls(json.loads(obj), depth + 1)
            except (ValueError, TypeError):
                return
    elif isinstance(obj, dict):
        for key, val in obj.items():
            if key.lower() in ('url', 'link', 'href', 'sourceurl', 'source_url'):
                yield from _urls(val, depth + 1)
            elif isinstance(val, (dict, list)):
                yield from _urls(val, depth + 1)
    elif isinstance(obj, list):
        for val in obj[:20]:
            yield from _urls(val, depth + 1)


def sources_from_event(event):
    # toolArguments may be merely a search query; only URLs explicitly
    # supplied by the provider are candidates for citation.
    found = []
    for key in ('toolResult', 'result', 'output', 'sources', 'toolArguments'):
        for raw in _urls(event.get(key)):
            parsed = urlparse(raw)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                continue
            if len(raw) > 600 or raw in found:
                continue
            found.append(raw)
            if len(found) >= MAX_SOURCES:
                return found
    return found


def format_sources(urls):
    if not urls:
        return ''
    return '\n\nمنابع ارائه‌شده توسط Duck.ai (تأیید مستقل نشده‌اند):\n' + '\n'.join(
        str(i) + '. ' + url for i, url in enumerate(urls[:MAX_SOURCES], 1))
