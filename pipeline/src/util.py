"""Shared helpers: config loading, paths, HTTP with a polite User-Agent, caching."""
from __future__ import annotations

import json
import os

import requests

PIPELINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def path(*parts: str) -> str:
    """Resolve a path relative to the pipeline/ directory."""
    return os.path.normpath(os.path.join(PIPELINE_DIR, *parts))


def load_json(rel_or_abs: str):
    with open(_resolve(rel_or_abs), encoding="utf-8") as fh:
        return json.load(fh)


def save_json(rel_or_abs: str, data) -> None:
    target = _resolve(rel_or_abs)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def load_config() -> dict:
    return load_json("config.json")


def _resolve(rel_or_abs: str) -> str:
    return rel_or_abs if os.path.isabs(rel_or_abs) else path(rel_or_abs)


def http_get_json(url: str, params: dict, user_agent: str, timeout: int = 60):
    resp = requests.get(
        url, params=params, headers={"User-Agent": user_agent}, timeout=timeout
    )
    resp.raise_for_status()
    return resp.json()


def http_post_json(url: str, data: dict, user_agent: str, timeout: int = 120):
    resp = requests.post(
        url, data=data, headers={"User-Agent": user_agent}, timeout=timeout
    )
    resp.raise_for_status()
    return resp.json()
