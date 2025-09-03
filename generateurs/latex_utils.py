import re

_LATEX_ESCAPE_MAP = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_escape(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"[\\&%$#_{}~^]", lambda m: _LATEX_ESCAPE_MAP[m.group()], s)


def latex_macro(name: str, default: str, value: str | None = None) -> str:
    """
    Émet un bloc LaTeX robuste pour une macro donnée:
      \providecommand{\name}{<default>}
      \renewcommand{\name}{ <value> }%   (si value n'est pas None)
    Ne JAMAIS utiliser \newcommand ici pour éviter les collisions.
    """
    out = rf"\providecommand{{\{name}}}{{{default}}}\n"
    if value is not None:
        out += rf"\renewcommand{{\{name}}}{{ {value} }}%\n"
    return out


