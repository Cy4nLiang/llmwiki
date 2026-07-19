# -*- coding: utf-8 -*-
"""llmwiki tools.lib — 工具共享库(仅 Python 标准库)。

单一实现原则:frontmatter / est_tokens / wikilink / config 载入全部住在 lib/fm.py,
其余工具 import,禁止私写副本(签名语义变更 = 框架 MAJOR,W-UPG-1)。
"""
from .fm import (  # noqa: F401
    ConfigError,
    WIKILINK_RE,
    est_tokens,
    iter_pages,
    iter_wikilinks,
    load_config,
    parse_frontmatter,
    read_page,
)

__all__ = [
    "ConfigError", "WIKILINK_RE", "est_tokens", "iter_pages", "iter_wikilinks",
    "load_config", "parse_frontmatter", "read_page",
]
