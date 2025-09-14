# generator/services/media_paths.py
from __future__ import annotations
import os, re
from typing import Optional, Tuple
from django.conf import settings

# Regex pour extraire les <img src="..."> d'un HTML
_re_img_src = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)

# Normalise diverses formes de src -> chemin absolu local utilisable par LaTeX
def normalize_media_url(src: str) -> Tuple[Optional[str], bool]:
    """
    Retourne (abs_path, exists).
    Règles:
      - /media/xxx           -> MEDIA_ROOT/xxx
      - media/xxx            -> MEDIA_ROOT/xxx
      - online/media/xxx     -> MEDIA_ROOT/xxx  (mapping spécifique)
      - chemin absolu /srv/...  -> tel quel
      - http(s)://...        -> None, False  (on n'essaie pas de downloader)
    Nettoie les ?query, #frag et espaces.
    """
    if not src:
        return None, False

    s = str(src).strip().replace('\\', '/')
    # enlever query/fragment
    s = s.split('?', 1)[0].split('#', 1)[0].strip()

    # Absolu serveur
    if s.startswith('/srv/') or s.startswith('/var/') or s.startswith('/home/'):
        return (s, os.path.exists(s))

    # Cas /media/xxx
    if s.startswith('/media/'):
        rel = s[len('/media/'):]
        abs_path = os.path.join(settings.MEDIA_ROOT, rel)
        return (abs_path, os.path.exists(abs_path))

    # Cas online/media/xxx
    if s.startswith('online/media/'):
        rel = s[len('online/media/'):]
        abs_path = os.path.join(settings.MEDIA_ROOT, rel)
        return (abs_path, os.path.exists(abs_path))

    # Cas media/xxx
    if s.startswith('media/'):
        rel = s[len('media/'):]
        abs_path = os.path.join(settings.MEDIA_ROOT, rel)
        return (abs_path, os.path.exists(abs_path))

    # URL http(s) -> non géré (pas de download en génération PDF)
    if s.startswith('http://') or s.startswith('https://'):
        return None, False

    # Dernier recours: essayer tel quel par rapport à MEDIA_ROOT si ça ressemble à un sous-chemin
    candidate = os.path.join(settings.MEDIA_ROOT, s.lstrip('/'))
    if os.path.exists(candidate):
        return candidate, True

    return None, False

# --- NEW: extraire les <img src="..."> d'un HTML ---
def extract_img_srcs(html: Optional[str]) -> list[str]:
    """
    Extrait tous les src d'images présents dans un HTML.
    Retourne une liste de chaînes src.
    """
    if not html:
        return []
    return _re_img_src.findall(str(html))
