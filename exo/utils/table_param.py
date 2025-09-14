# exo/utils/table_param.py
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
import random
import copy

MASK_PREFIX = "calc:"  # sémantique "masque" (PAS de token -> cellule vide)

def _split_semicolons(s: str) -> List[str]:
    return [c.strip() for c in s.split(";")]

@dataclass
class TableBank:
    orientation: str  # 'h' (header row) or 'v' (header col)
    header: List[str]           # pour 'h' : titres de colonnes ; pour 'v' : titres de lignes (1ère colonne)
    rows: List[List[str]]       # banque brute de lignes (pour 'h') ou colonnes (pour 'v')

# --- helpers de normalisation ---
def _pad_row(row: List[str], n: int) -> List[str]:
    if len(row) < n:
        return row + [""] * (n - len(row))
    if len(row) > n:
        return row[:n-1] + [" / ".join(row[n-1:])]
    return row


def parse_table_bank(defn: Dict[str, Any]) -> TableBank:
    """
    defn = {
      "orientation": "h"|"v",
      "header": "A;B;C"
      "rows": ["x;y;z", ...]
    }
    """
    orientation = (defn.get("orientation") or "h").lower()
    header = _split_semicolons(defn["header"])
    rows = [_split_semicolons(r) for r in defn.get("rows", [])]
    return TableBank(orientation=orientation, header=header, rows=rows)

def _is_mask(s: str) -> bool:
    return isinstance(s, str) and s.startswith(MASK_PREFIX)

def _strip_mask(s: str) -> str:
    return s[len(MASK_PREFIX):].strip()

def pick_rows(bank: TableBank, n: int, seed: int) -> List[List[str]]:
    rng = random.Random(seed)
    pool = copy.deepcopy(bank.rows)
    rng.shuffle(pool)
    return pool[:max(0, min(n, len(pool)))]

def apply_masks_h(header: List[str], rows: List[List[str]], view: str) -> Tuple[List[str], List[List[str]]]:
    head = header[:]
    col_mask = [_is_mask(h) for h in head]
    head = [_strip_mask(h) if m else h for h, m in zip(head, col_mask)]

    if view == "corrige":
        fixed = [[_strip_mask(c) if _is_mask(c) else c for c in row] for row in rows]
        return head, fixed

    out_rows = []
    for row in rows:
        new_row = []
        for j, cell in enumerate(row):
            if col_mask[j]:
                new_row.append("")
            else:
                new_row.append("" if _is_mask(cell) else cell)
        out_rows.append(new_row)
    return head, out_rows

def apply_masks_v(header: List[str], cols: List[List[str]], view: str) -> Tuple[List[str], List[List[str]]]:
    head = header[:]
    row_mask = [_is_mask(h) for h in head]
    head = [_strip_mask(h) if m else h for h, m in zip(head, row_mask)]

    if view == "corrige":
        fixed_cols = []
        for col in cols:
            fixed_cols.append([_strip_mask(c) if _is_mask(c) else c for c in col])
        return head, fixed_cols

    masked_cols = []
    for col in cols:
        masked_cols.append([
            "" if row_mask[i] or _is_mask(col[i]) else col[i]
            for i in range(len(col))
        ])
    return head, masked_cols

# --- Normalisation en sortie StyledTableBlock ---
def to_tableblock_value_h(header: List[str], rows: List[List[str]]) -> Dict[str, Any]:
    n = len(header)
    norm = [_pad_row(r, n) for r in rows]
    data = [header] + norm
    return {
        "data": data,
        "first_row_is_table_header": True,
        "first_col_is_header": False,
    }

def to_tableblock_value_v(header: List[str], cols: List[List[str]]) -> Dict[str, Any]:
    n_rows = len(header)
    cols = [c[:n_rows] + [""]*(n_rows - len(c)) if len(c) < n_rows else c[:n_rows] for c in cols]
    top = [""] + [f"Col {i+1}" for i in range(len(cols))]
    data = [top]
    for i, h in enumerate(header):
        data.append([h] + [col[i] for col in cols])
    return {
        "data": data,
        "first_row_is_table_header": True,
        "first_col_is_header": False,
    }
