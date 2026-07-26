#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmwiki lib.secscan — 内容脱敏扫描(仅 Python 标准库,W-SEC-3)。

在 wiki/ 与 raw/ 文本内容里扫常见密钥/凭证样式,由 lint 挂载报 **soft warning**(W-SEC-2
的 config/manifest 凭证扫描是同档先例)。目的是"密钥进不了 wiki"的整合前告警,不是 fail 门。

设计约束:
  - **只回显命中类型 + 行号,绝不回显命中值本身**——把密钥打进 lint 报告/日志等于二次泄漏。
  - 行内豁免:某行含 `<!-- secscan:allow -->` 时,**豁免其下一行**(误报/示范语法的逃生舱)。
  - raw/ 不可变(W-ARCH-1)无法加豁免标注,其命中是"ingest 时遮蔽"的持久提醒(见 ingest skill)。
  - 正则是**样式匹配**不含真实 token;本文件自检用的测试串一律拆分拼接,源码里不出现完整
    token 样式串(CONTRIBUTING §58 仓内零 token 样式串)。

已知限制(soft 尽力扫描,如实声明):generic 赋值要求值含**至少一个大写或数字**(熵信号,压散文
误报),故**纯小写且无数字的口令/passphrase 明文**(如 `password = correcthorsebatterystaple`、
纯小写 hex)不覆盖——这类是人类记忆型弱密钥、价值低于必带熵的 API key/token(后者都被专用 pattern
兜底),用它换掉高频 kebab 散文误报是有意取舍。字段词表也不穷尽厂商 token 形态,这是 tripwire 不是
保证;真要拦须配 ingest 遮蔽纪律(W-SEC-3)。
"""
from __future__ import annotations

import re

__all__ = ["ALLOW_MARK", "scan_text"]

ALLOW_MARK = "secscan:allow"
# 豁免标注须为**锚定的注释形态**(F1:防散文/文档里讨论 secscan:allow 的行意外豁免下一行——
# 本框架自身文档正好讨论该功能,是高风险语境);`\b[^>]*` 允许 `<!-- secscan:allow: 理由 -->`
# 带豁免理由(鼓励的好实践),仍拒无 `<!--` 包裹的散文。
_ALLOW_RE = re.compile(r"<!--\s*" + ALLOW_MARK + r"\b[^>]*-->")

# (kind, 编译正则):样式匹配,宁可 soft 误报(有 allow 豁免)也不漏报明显密钥
_PATTERNS = [
    ("aws-access-key", re.compile(r"\bA(?:KIA|SIA)[0-9A-Z]{16}")),      # AKIA + ASIA(临时会话)
    ("gcp-api-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}")),
    ("github-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}")),      # 细粒度 PAT
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("private-key-block", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----")),  # 含 PGP BLOCK
    # 通用「凭证字段 = 长随机值」:字段词表对齐 W-SEC-2 并补 client_secret/token/private_key/
    # credential 等(放宽 secret/token 左边界匹配复合名);值 ≥20 位且**含至少一个大写或数字**
    # (熵信号,压纯小写连字符散文误报)。字段部大小写不敏感,值部大小写敏感(故熵信号真实)。
    ("generic-secret-assign", re.compile(
        r"(?i:api[_-]?key|(?:client[_-]?)?secret|(?:access[_-]?|auth[_-]?)?token"
        r"|private[_-]?key|credential|password|passwd)"   # 去 pwd:3 字母短词撞 shell pwd/路径赋值,误报高
        r"\s*[:=]\s*[\"']?(?=[A-Za-z0-9+/_\-]*[A-Z0-9])[A-Za-z0-9+/_\-]{20,}")),
]


def scan_text(text: str) -> list:
    """扫描文本 → [{line, kind}](line 1-based);上一行含 ALLOW_MARK 的行豁免。

    每行至多报一条(取首个命中的 kind);**不回显命中值**。空/无命中返回 []。
    """
    findings = []
    allow_next = False
    for i, line in enumerate((text or "").split("\n"), 1):
        skip = allow_next
        allow_next = bool(_ALLOW_RE.search(line))   # 本行有锚定标注 → 豁免下一行
        if skip:
            continue
        for kind, rx in _PATTERNS:
            if rx.search(line):
                findings.append({"line": i, "kind": kind})
                break
    return findings


if __name__ == "__main__":  # python3 tools/lib/secscan.py — 零依赖冒烟自检
    # 测试串一律拆分拼接:源码里不出现完整 token 样式串(CONTRIBUTING §58)
    aws = "AKIA" + "ABCDEFGH12345678"                        # AKIA + 16 大写字母数字
    asia = "ASIA" + "ABCDEFGH12345678"                       # 临时会话密钥
    gh = "ghp" + "_" + "b" * 36
    pat = "github_pat_" + "A1b2C3d4E5" * 3                    # 细粒度 PAT
    pk = "-----BEGIN " + "RSA PRIVATE KEY-----"
    pgp = "-----BEGIN " + "PGP PRIVATE KEY BLOCK-----"
    # 值含大写/数字(熵信号):client_secret / access_token / 裸 token 均须命中(F3)
    cs = "client_secret" + " = " + "Ab3" + "x" * 20
    tok = "token" + ": " + "Xy9" + "z" * 20
    for s, kind in ((aws, "aws-access-key"), (asia, "aws-access-key"), (gh, "github-token"),
                    (pat, "github-pat"), (pk, "private-key-block"), (pgp, "private-key-block"),
                    (cs, "generic-secret-assign"), (tok, "generic-secret-assign")):
        assert scan_text(s) and scan_text(s)[0]["kind"] == kind, (s[:20], scan_text(s))
    # F1:只有锚定注释形态豁免下一行;散文提及 secscan:allow **不**豁免;带理由的注释豁免
    assert scan_text("<!-- " + ALLOW_MARK + " -->\n" + aws) == []
    assert scan_text("<!-- " + ALLOW_MARK + ": 误报-示范用 -->\n" + aws) == []
    assert scan_text("讨论 " + ALLOW_MARK + " 用法的散文\n" + aws)[0]["kind"] == "aws-access-key"
    # 值不回显(finding 只含 line/kind)
    assert set(scan_text(aws)[0]) == {"line", "kind"}
    # F5:纯小写连字符散文(无熵信号)不误报;"password 走环境变量"无长随机值不误报
    assert scan_text("secret: this-page-documents-the-secret-handshake-protocol") == []
    assert scan_text("默认问候语「你好,世界」\npassword 只走环境变量\n普通正文") == []
    print("secscan self-check OK")
