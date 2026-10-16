"""
helpers module containing functions which are used few times in the code and are not associated to Eurostat API connector library.
"""

import subprocess
import sys
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _ensure(import_name, pip_name):
    """Import a library, if missing, install it and retry."""
    try:
        __import__(import_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m","pip", "install", pip_name])

if not getattr(sys, "frozen", False):
    _ensure("pandas", "pandas")

import pandas as pd

def _normalise_codelist(raw):
    """Accept dictionary/dataframe/list and return a list of tuples."""
    if isinstance(raw, dict):
        return [(str(k), str(v)) for k, v in raw.items()]
    if isinstance(raw, pd.DataFrame):
        cols = raw.columns.tolist()
        if len(cols) >= 2:
            return list(zip(raw[cols[0]].astype(str), raw[cols[1]].astype(str)))
        return [(str(x), str(x)) for x in raw[cols[0]]]
    if isinstance(raw, (list, tuple)):
        out = []
        for item in raw:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                out.append((str(item[0]), str(item[1])))
            else:
                out.append((str(item), str(item)))
        return out
    return []

def script_folder():
    """Folder where this script lives."""
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()

def output_folder():
    if getattr(sys, "frozen", False):
        root = os.path.dirname(sys.executable)
    else:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder = os.path.join(root, "output")
    os.makedirs(folder, exist_ok=True)
    return folder

def _load_lookup():
    """Load the abbreviation code dictionary from the P: drive."""
    try:
        with open(os.path.join(BASE_DIR, "src", "create dictionaries", "parameter abreviations", "lookup_dictionary.json"), encoding="utf-8") as f:
            raw = json.load(f)
        return {str(k).upper(): v for k, v in raw.items()}
    except Exception as e:
        return {}

LOOKUP = _load_lookup()

def dim_display_name(dim):
    """Full dimension name (with code in parentheses), or the code if unknown."""
    entry = LOOKUP.get(str(dim).upper())
    if entry and entry.get("name"):
        return f"{entry['name']} [{dim}]"
    return str(dim)

def value_label(dim, code, fallback):
    """Full label for a value code, or the code if unknown."""
    entry = LOOKUP.get(str(dim).upper())
    if entry:
        vals = entry.get("values", {})
        lab = vals.get(code) or vals.get(str(code).upper())
        if lab:
            return lab
    return fallback

def _flatten_leaves(nodes, out):
    """Collect every non-folder node (dataset/table) into out."""
    for n in nodes:
        if n.get("type") == "folder":
            _flatten_leaves(n.get("children", []), out)
        else:
            out.append(n)
