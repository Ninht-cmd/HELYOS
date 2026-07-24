"""Accès web — les yeux du cerveau sur Internet (marchés, e-commerce, ingénierie…).

Sans ça, le cerveau ne connaît que ce que qwen3 a appris avant sa date de coupure.
Ici : recherche instantanée (DuckDuckGo, gratuit sans clé) + lecture de page.
Stdlib pur, Local First (aucune clé, aucune donnée qui traîne).

Sécurité (garde-fou SSRF) : `web_fetch` refuse les adresses privées/locales — le
cerveau ne doit jamais pouvoir sonder tes services internes via une URL choisie
par le LLM. Lecture publique uniquement, avec timeout et taille bornée.

Honnêteté : DuckDuckGo « Instant Answer » est une recherche LIBRE mais peu
profonde (définitions, abstracts, faits) — pas un crawl Google. Pour une
recherche riche, une clé (Brave/Tavily) serait nécessaire : chantier assumé.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

_UA = {"User-Agent": "helyos-brain/1.0"}
_MAX = 4000  # caractères max rendus au LLM (on ne noie pas le contexte)


def _get(url: str, timeout: float = 8.0) -> str:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (URL publique bornée)
        return r.read(_MAX * 4).decode("utf-8", "replace")


def web_search(query: str) -> str:
    """Recherche instantanée DuckDuckGo (gratuit) ; repli Wikipédia pour le savoir."""
    q = (query or "").strip()
    if not q:
        return "(requête vide)"
    try:
        url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(
            {"q": q, "format": "json", "no_html": 1, "skip_disambig": 1})
        d = json.loads(_get(url))
        parts = []
        if d.get("Answer"):
            parts.append(str(d["Answer"]))
        if d.get("AbstractText"):
            parts.append(d["AbstractText"])
        for t in d.get("RelatedTopics", [])[:4]:
            if isinstance(t, dict) and t.get("Text"):
                parts.append(t["Text"])
        if parts:
            return " | ".join(parts)[:_MAX]
    except Exception:
        pass
    # repli : résumé Wikipédia (savoir de fond sur un sujet)
    try:
        slug = urllib.parse.quote(q.replace(" ", "_"))
        d = json.loads(_get(f"https://fr.wikipedia.org/api/rest_v1/page/summary/{slug}"))
        if d.get("extract"):
            return d["extract"][:_MAX]
    except Exception:
        pass
    return f"(aucune réponse instantanée pour « {q} » — reformule ou donne une URL à lire)"


def _is_public(host: str) -> bool:
    """Bloque localhost et IP privées (garde-fou SSRF)."""
    import ipaddress
    import socket
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(host))
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                    or ip.is_multicast)
    except Exception:
        return False


def web_fetch(url: str) -> str:
    """Lit une page publique et renvoie son texte (HTML dépouillé)."""
    u = (url or "").strip()
    if not u.startswith(("http://", "https://")):
        return "(URL invalide : http(s) requis)"
    host = urllib.parse.urlparse(u).hostname or ""
    if not _is_public(host):
        return "(refusé : adresse privée/locale interdite au cerveau)"
    try:
        html = _get(u, timeout=10)
    except Exception as exc:
        return f"(page injoignable : {str(exc)[:80]})"
    html = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:_MAX] or "(page vide après nettoyage)"
