"""
Module with functions helping establishing connections with give database,
obtaining parameters' values, applying filters and obtaining observations. 
"""

import re
import sys
from datetime import datetime
import pandas as pd
from .helpers import _ensure, _normalise_codelist

if not getattr(sys, "frozen", False):
    _ensure("eurostat", "eurostat")

import eurostat

def fetch_dimensions(db):
    return list(eurostat.get_pars(db))

def fetch_codelist(db, dimension):
    # full=False -> only values that actually occur in this dataset
    raw = eurostat.get_dic(db, dimension, frmt="list", full=False)
    return _normalise_codelist(raw)

def fetch_data(db, filters):
    df = eurostat.get_data_df(db, filter_pars=filters)
    if df is None:
        return pd.DataFrame()
    return _tidy(df)

def _tidy(df):
    """Clean the public package's raw TSV-style output."""
    df = df.copy()
    # headers look like 'geo\TIME_PERIOD' -> keep just 'geo'
    df.columns = [str(c).split("\\")[0].strip() for c in df.columns]
    # values arrive as text (e.g. '12.3', ':' for missing) -> numbers
    for c in df.columns:
        if _TIME_COL_RE.match(c):
            df[c] = pd.to_numeric(df[c].astype(str).str.strip(), errors="coerce")
    return df

def to_eurostat_period(text, ptype="Annual (year only)"):
    """Convert a user-entered date into a Eurostat period string.

    Accepts dd/mm/yyyy, dd-mm-yyyy, yyyy-mm-dd, dd.mm.yyyy, or a native period
    (e.g. yyyy, yyyy-qq, yyyy-mmm) which is passed through unchanged.
    Returns a period string, or None if empty. Raises ValueError if unparseable.
    """
    text = (text or "").strip()
    if not text:
        return None
    # Check for native Eurostat period.
    if re.match(r"^\d{4}([-/](Q[1-4]|S[12]|W\d{1,2}|D\d{1,3}|M?\d{1,2}))?$", text, re.I):
        return text.replace("/", "-")
    # Otherwise parse depending on format.
    d = None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            d = datetime.strptime(text, fmt)
            break
        except ValueError:
            continue
    if d is None:
        raise ValueError(f"Could not understand date/period: '{text}'")
    if ptype.startswith("Quarter"):
        return f"{d.year}-Q{(d.month - 1)//3 + 1}"
    if ptype.startswith("Month"):
        return f"{d.year}-M{d.month:02d}"
    if ptype.startswith("Daily"):
        return f"{d.year}-D{d.timetuple().tm_yday:03d}"
    return f"{d.year}"

_TIME_COL_RE = re.compile(
    r"^\s*\d{4}([-\s]?(Q[1-4]|S[12]|M\d{1,2}|W\d{1,2}|D\d{1,3}|\d{2}))?\s*$", re.I
)

def melt_to_panel(df):
    """Reshape data into panel format."""
    time_cols = [c for c in df.columns if _TIME_COL_RE.match(str(c))]
    if not time_cols:
        return df
    id_cols = [c for c in df.columns if c not in time_cols]
    long_df = df.melt(id_vars=id_cols, value_vars=time_cols,
                      var_name="time", value_name="value")
    return long_df.dropna(subset=["value"]).reset_index(drop=True)
