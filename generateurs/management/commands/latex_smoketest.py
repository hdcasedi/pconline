# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from pathlib import Path
import subprocess, tempfile, textwrap, shutil

MINI_TEX = r"""
\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[french]{babel}
\usepackage{geometry}
\geometry{margin=2cm}
\input{macros.tex}
\renewcommand{\titreDevoir}{ Contrôle }
\renewcommand{\sousTitreUn}{  }      % volontairement "vide"
\renewcommand{\sousTitreDeux}{ Test }
\renewcommand{\baremeGlobal}{ 20 }
\begin{document}
OK
\end{document}
"""

class Command(BaseCommand):
    help = "Compile un mini .tex pour fumer les erreurs (macros, lignes vides)."

    def handle(self, *args, **opts):
        with tempfile.TemporaryDirectory(prefix="latex_smoke_") as tmp:
            tmp = Path(tmp)
            # copie macros.tex
            repo_macros = Path("generateurs/templates/generateurs/pdf/macros.tex")
            shutil.copy(repo_macros, tmp / "macros.tex")
            (tmp / "enonce.tex").write_text(textwrap.dedent(MINI_TEX), encoding="utf-8")

            cmd = ["pdflatex","-interaction=errorstopmode","-halt-on-error","-file-line-error","enonce.tex"]
            p = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
            print(p.stdout)
            print(p.stderr)
            if (tmp / "enonce.pdf").exists():
                self.stdout.write(self.style.SUCCESS("Smoke OK: PDF généré."))
            else:
                self.stderr.write(self.style.ERROR("Smoke FAIL: pas de PDF. Consulte enonce.log dans le tmp."))
                self.stderr.write((tmp / "enonce.log").read_text(encoding="utf-8"))
                raise SystemExit(2)


