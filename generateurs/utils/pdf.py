"""Utilitaire LaTeX → PDF avec logs et hints."""
from pathlib import Path
import subprocess
import tempfile
import re
from django.template.loader import render_to_string
from .exceptions import LatexCompileError

TAIL_LINES = 1000

# Macros sensibles qui ne doivent être définies qu'une fois
SENSITIVE_MACROS = [
    "ecoleLigneUn", "ecoleLigneDeux", "ecoleLigneTrois",
    "titreDevoir", "sousTitreUn", "sousTitreDeux", "baremeGlobal"
]

SENSITIVE = [
    "ecoleLigneUn","ecoleLigneDeux","ecoleLigneTrois",
    "titreDevoir","titreSerie","sousTitreUn","sousTitreDeux","baremeGlobal",
]


def latex_override_block(values: dict) -> str:
    """
    Génère un bloc d'override unique pour les macros sensibles.
    values keys: ecoleLigneUn, ecoleLigneDeux, ecoleLigneTrois,
                 titreDevoir, sousTitreUn, sousTitreDeux, baremeGlobal
    Toute valeur None/'' => ne rien override (laisser le défaut).
    """
    def line(name, value):
        if value is None or str(value).strip() == "":
            return ""
        return rf"\renewcommand{{\{name}}}{{ {value} }}%" + "\n"

    return (
        line("ecoleLigneUn", values.get("ecoleLigneUn"))
        + line("ecoleLigneDeux", values.get("ecoleLigneDeux"))
        + line("ecoleLigneTrois", values.get("ecoleLigneTrois"))
        + line("titreDevoir", values.get("titreDevoir"))
        + line("sousTitreUn", values.get("sousTitreUn"))
        + line("sousTitreDeux", values.get("sousTitreDeux"))
        + line("baremeGlobal", values.get("baremeGlobal"))
    )


def _deep_trim(x):
    if isinstance(x, dict):
        return {k: _deep_trim(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return type(x)(_deep_trim(v) for v in x)
    if x is None:
        return ""
    if isinstance(x, (int, float)):
        return str(x)
    if isinstance(x, bool):
        return str(x)
    s = str(x)
    return s.strip()

def normalize_context(ctx: dict) -> dict:
    return _deep_trim(ctx)

def assert_no_sensitive_newcommand(rendered_tex: str):
    for macro in SENSITIVE:
        pattern = rf'\\newcommand{{\\{macro}}}'
        if re.search(pattern, rendered_tex):
            raise RuntimeError(f"Interdit: \\newcommand sur {macro}. "
                               f"N'utilise que \\providecommand (macros.tex) + \\renewcommand (overrides).")

def sanitize_duplicate_newcommand(tex: str) -> str:
    """
    Convertit toute occurrence supplémentaire de \newcommand{\macro} en \renewcommand{\macro}
    pour les macros sensibles (pare-feu contre les doublons).
    """
    for macro in SENSITIVE_MACROS:
        pattern = rf'(\\newcommand\{{\\{macro}\}}\s*\{{)'
        # Garder la 1re occurrence; les suivantes -> \renewcommand
        seen = 0
        def repl(match):
            nonlocal seen
            seen += 1
            return match.group(1) if seen == 1 else rf'\renewcommand{{\{macro}}}{{'
        tex = re.sub(pattern, repl, tex)
    return tex


def _read_log_tail(workdir: Path, tex_stem: str) -> str:
    log = workdir / f"{tex_stem}.log"
    if not log.exists():
        return ""
    try:
        txt = log.read_text(encoding="utf-8", errors="ignore")
        lines = txt.splitlines()

        # 1) Depuis la première ligne d'erreur commençant par '!'
        bang_idx = next((i for i, L in enumerate(lines) if L.startswith("!")), None)
        if bang_idx is not None:
            return "\n".join(lines[bang_idx : min(len(lines), bang_idx + 200)])

        # 2) Sinon autour d'"Emergency stop"
        em_idx = next((i for i, L in enumerate(lines) if "Emergency stop" in L), None)
        if em_idx is not None:
            start = max(0, em_idx - 80)
            return "\n".join(lines[start : min(len(lines), em_idx + 120)])

        # 3) Gros tail
        return "\n".join(lines[-TAIL_LINES:])
    except Exception:
        return ""


def _hint(stdout: str, log_tail: str, engine: str) -> str:
    text = (stdout or "") + "\n" + (log_tail or "")
    if "tikz.sty' not found" in text:
        return "Installe `texlive-pictures`."
    if "tabularx.sty' not found" in text:
        return "Installe `texlive-latex-extra`."
    if "xcolor.sty' not found" in text:
        return "Installe `texlive-latex-recommended`."
    if "mhchem.sty' not found" in text or "\\ce{" in text:
        return "Installe `texlive-science` et ajoute \\usepackage[version=4]{mhchem}."
    if "minted.sty' not found" in text:
        return "Installe `texlive-latex-extra` et `python3-pygments` puis active -shell-escape."
    if "shell-escape" in text:
        return "Active -shell-escape (minted)."
    if "fontspec.sty" in text and engine != "xelatex":
        return "Utilise xelatex (installe `texlive-xetex`)."
    return ""


def render_tex_to_pdf(template_name: str, context: dict, *, engine: str | None = None, shell_escape: bool | None = None) -> tuple[str, str]:
    tmp = Path(tempfile.mkdtemp(prefix="pdf_generator_"))

    # Normaliser le contexte (vides → "")
    context = normalize_context(context)

    tex_source = render_to_string(template_name, context)
    
    # Garde-fou anti-doublons
    assert_no_sensitive_newcommand(tex_source)
    
    # Nettoyage des doublons de \newcommand avant compilation
    tex_source = sanitize_duplicate_newcommand(tex_source)
    
    stem = "enonce" if "enonce" in template_name else ("correction" if "correction" in template_name else "document")
    tex_path = tmp / f"{stem}.tex"
    tex_path.write_text(tex_source, encoding="utf-8")
    
    # Copier macros.tex dans le dossier temporaire
    macros_path = Path(__file__).parent.parent / "templates" / "generateurs" / "pdf" / "macros.tex"
    if macros_path.exists():
        import shutil
        shutil.copy2(macros_path, tmp / "macros.tex")

    eng = engine or ("xelatex" if ("fontspec" in tex_source or "\\setmainfont" in tex_source) else "pdflatex")
    se = shell_escape if shell_escape is not None else ("minted" in tex_source or "pygmentize" in tex_source)

    def run_once():
        cmd = [eng]
        if se:
            cmd.append("-shell-escape")
        cmd += ["-interaction=nonstopmode", "-halt-on-error", "-file-line-error", tex_path.name]
        return subprocess.run(cmd, cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    p1 = run_once()
    if p1.returncode != 0:
        tail = _read_log_tail(tmp, stem)
        raise LatexCompileError(f"{eng} failed (pass 1) @ {tmp}", stdout=p1.stdout, log_tail=tail, hint=_hint(p1.stdout, tail, eng))

    p2 = run_once()
    if p2.returncode != 0:
        tail = _read_log_tail(tmp, stem)
        raise LatexCompileError(f"{eng} failed (pass 2) @ {tmp}", stdout=p2.stdout, log_tail=tail, hint=_hint(p2.stdout, tail, eng))

    pdf = tmp / f"{stem}.pdf"
    if not pdf.exists():
        tail = _read_log_tail(tmp, stem)
        raise LatexCompileError(f"PDF non généré @ {tmp}", stdout=p2.stdout, log_tail=tail)

    return str(pdf), str(tmp)


def get_branding_settings() -> dict:
    """Récupère les paramètres de marque depuis le snippet Wagtail."""
    try:
        from generateurs.models import DSBrandingSettings
        settings = DSBrandingSettings.objects.first()
        if settings and settings.logo:
            return {
                'logo_url': settings.logo.file.url if settings.logo else None,
                'ecole_l1': settings.ecole_l1 or '',
                'ecole_l2': settings.ecole_l2 or '',
                'ecole_l3': settings.ecole_l3 or '',
            }
    except Exception:
        pass
    return {'logo_url': None, 'ecole_l1': '', 'ecole_l2': '', 'ecole_l3': ''}

