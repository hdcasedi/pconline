"""
Utilitaires de scan pour détecter les paramètres dans le contenu de l'exercice.
Utilise des regex avec DOTALL pour capturer le contenu multi-lignes.
"""

import re
from typing import Set, Dict, List


def find_value_params(text: str) -> Set[str]:
    """
    Détecte les paramètres de valeur [[ name ]] (espaces internes autorisés),
    en excluant slot: et image:.

    Args:
        text: Contenu textuel à scanner

    Returns:
        Ensemble des noms de paramètres détectés
    """
    # Regex pour [[ name ]] - exclut slot: et image:
    pattern = r"\[\[\s*([A-Za-z_][A-Za-z0-9_]*)\s*\]\]"
    matches = re.findall(pattern, text, re.DOTALL)

    # Filtrer pour exclure les slots et images
    filtered = set()
    for match in matches:
        if not re.search(rf"\[\[\s*(?:slot|image):{re.escape(match)}\s*", text):
            filtered.add(match)

    return filtered


def find_slot_params(text: str) -> Dict[str, str]:
    """
    Détecte les paramètres slot [[slot:name]] … [[/slot]] (même bloc texte),
    contenu capturé en non-greedy.

    Args:
        text: Contenu textuel à scanner

    Returns:
        Dictionnaire nom -> contenu HTML par défaut
    """
    # Regex pour [[slot:name]]...[[/slot]] - capture le contenu entre les balises
    pattern = r"\[\[\s*slot:([A-Za-z_][A-Za-z0-9_]*)\s*\]\](.*?)\[\[\s*/\s*slot\s*\]\]"
    matches = re.findall(pattern, text, re.DOTALL)

    return {name: content.strip() for name, content in matches}


def find_image_params(text: str) -> Set[str]:
    """
    Détecte les paramètres image [[image:name]] (dans les légendes d'image notamment).

    Args:
        text: Contenu textuel à scanner

    Returns:
        Ensemble des noms de paramètres image détectés
    """
    # Regex pour [[image:name]]
    pattern = r"\[\[\s*image:([A-Za-z_][A-Za-z0-9_]*)\s*\]\]"
    matches = re.findall(pattern, text, re.DOTALL)

    return set(matches)


def parse_set_items(text: str) -> List[str]:
    """
    Parse le texte d'un ensemble de valeurs.
    Sépare par ; ou \n, trim, filtre vide.

    Args:
        text: Texte contenant les valeurs

    Returns:
        Liste des valeurs nettoyées
    """
    if not text:
        return []

    # Split par ; ou \n
    items = re.split(r'[;\n]', text)

    # Nettoyer et filtrer
    cleaned_items = []
    for item in items:
        item = item.strip()
        if item:  # Ignorer les items vides
            cleaned_items.append(item)

    return cleaned_items