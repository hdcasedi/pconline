#!/usr/bin/env python3
"""
Script pour appliquer la correction Unicode au fichier latex.py
"""

import os

def apply_unicode_fix():
    """Applique la correction Unicode au fichier latex.py"""
    
    latex_file = "/srv/pconline/generator/templatetags/latex.py"
    
    # Lire le fichier
    with open(latex_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Trouver la ligne 134 (index 133)
    target_line = 133  # 0-indexed
    if target_line < len(lines) and "text.replace(\"^\"" in lines[target_line]:
        print(f"✅ Ligne 134 trouvée: {lines[target_line].strip()}")
        
        # Insérer la gestion Unicode après la ligne 135 (ligne vide)
        unicode_code = '''            # Gestion des caractères Unicode courants
            text = text.replace("λ", r"$\\lambda$")  # lambda
            text = text.replace("μ", r"$\\mu$")      # mu
            text = text.replace("π", r"$\\pi$")      # pi
            text = text.replace("α", r"$\\alpha$")   # alpha
            text = text.replace("β", r"$\\beta$")    # beta
            text = text.replace("γ", r"$\\gamma$")   # gamma
            text = text.replace("δ", r"$\\delta$")   # delta
            text = text.replace("ε", r"$\\varepsilon$")  # epsilon
            text = text.replace("θ", r"$\\theta$")   # theta
            text = text.replace("σ", r"$\\sigma$")   # sigma
            text = text.replace("τ", r"$\\tau$")     # tau
            text = text.replace("φ", r"$\\phi$")     # phi
            text = text.replace("ω", r"$\\omega$")   # omega
            text = text.replace("Δ", r"$\\Delta$")   # Delta
            text = text.replace("Σ", r"$\\Sigma$")   # Sigma
            text = text.replace("Ω", r"$\\Omega$")   # Omega
            text = text.replace("∞", r"$\\infty$")   # infinity
            text = text.replace("±", r"$\\pm$")      # plus-minus
            text = text.replace("×", r"$\\times$")   # times
            text = text.replace("÷", r"$\\div$")     # divide
            text = text.replace("≤", r"$\\leq$")     # less than or equal
            text = text.replace("≥", r"$\\geq$")     # greater than or equal
            text = text.replace("≠", r"$\\neq$")     # not equal
            text = text.replace("≈", r"$\\approx$")  # approximately equal
            text = text.replace("°", r"$^\\circ$")   # degree
'''
        
        # Insérer après la ligne 135 (ligne vide)
        lines.insert(135, unicode_code)
        
        # Écrire le fichier modifié
        with open(latex_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print("✅ Correction Unicode appliquée avec succès !")
        print("✅ Le caractère λ sera maintenant converti en $\\lambda$")
        return True
    else:
        print("❌ Impossible de trouver la ligne 134 avec le bon contenu")
        return False

if __name__ == "__main__":
    apply_unicode_fix()
