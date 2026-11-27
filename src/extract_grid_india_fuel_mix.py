"""
Fast parallel extractor for Grid-India (POSOCO) NLDC SCADA fuel-mix telemetry
(April 2022 - December 2023, 21 months, ~15,360 hourly observations).

Extracts:
  - thermal_coal_mw  (TOTAL_THM_ONLY|P)
  - hydro_mw         (TOTAL_NLDC_HYD|P)
  - gas_mw           (TOTAL_NLDC_GAS|P)
  - nuclear_mw       (TOTAL_NLDC_NPC|P)
  - wind_mw          (ALL_INDIA_WIND|P)
  - solar_mw         (Solar or ALL_IND_SOLAR|P)
  - demand_mw        (NLDC_DEMAND|P)
  - system_inertia   (INTRA_SYSTEM_INTERTIA|P)

Uses streaming XML parsing directly from .xlsx zip archives for ~15x speedup
over openpyxl on 50 MB high-frequency (10-second) SCADA spreadsheets.
"""

from __future__ import annotations

import concurrent.futures
import datetime as dt
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "grid_india"
OUT_DIR = PROJECT_ROOT / "data" / "processed" / "grid_india"
OUT_DIR.mkdir(parents=True, exist_ok=True)

EXCEL_EPOCH = dt.datetime(1899, 12, 30)
COL_RE = re.compile(r"^([A-Z]+)")


def col_letters_to_idx(letters: str) -> int:
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def find_sheet1_xml(zf: zipfile.ZipFile) -> str:
    """Finds the zip member path corresponding to Sheet1 in an xlsx archive."""
    wb_xml = ET.fromstring(zf.read("xl/workbook.xml"))
    ns_wb = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
             "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    rid = None
    for sh in wb_xml.findall(".//main:sheet", ns_wb):
        if sh.attrib.get("name") == "Sheet1":
            rid = sh.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            break
    if rid is None:
        raise ValueError("Sheet1 not found")

    rels_xml = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    for rel in rels_xml:
        if rel.attrib.get("Id") == rid:
            target = rel.attrib.get("Target", "")
            target = target.lstrip("/")
            if not target.startswith("xl/"):
                target = "xl/" + target
            return target
    raise ValueError(f"Relationship {rid} not found")


def load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    ss = []
    with zf.open("xl/sharedStrings.xml") as f:
        for _, elem in ET.iterparse(f, events=("end",)):
            if elem.tag.endswith("}si"):
                texts = [t.text or "" for t in elem.iter() if t.tag.endswith("}t")]
                ss.append("".join(texts))
                elem.clear()
    return ss


def parse_single_scada_xlsx(path_str: str) -> pd.DataFrame | None:
    path = Path(path_str)
    # Only process 2022-04 through 2023-12 SCADA files
    name_lower = path.name.lower()
    if "2024" in name_lower or "2021" in name_lower:
        return None
    if any(m in name_lower for m in ["january 2022", "february 2022", "march 2022"]):
        return None

    t0 = time.perf_counter()
    with zipfile.ZipFile(path, "r") as zf:
        sheet_xml = find_sheet1_xml(zf)
        shared_strings = load_shared_strings(zf)

        # Pass 1: stream rows
        col_map: dict[str, int] = {}
        target_indices: set[int] = set()
        # Hourly accumulators: hour_key (int hours since EXCEL_EPOCH) -> [sum_0, cnt_0, ...]
        hourly_sums: dict[int, np.ndarray] = {}
        hourly_cnts: dict[int, np.ndarray] = {}
        fields = [
            "thermal_coal_mw",
            "hydro_mw",
            "gas_mw",
            "nuclear_mw",
            "wind_mw",
            "solar_mw",
            "demand_mw",
            "system_inertia",
        ]
        n_fields = len(fields)
        idx_to_field_pos: dict[int, int] = {}

        row_num = 0
        with zf.open(sheet_xml) as f:
            for _, elem in ET.iterparse(f, events=("end",)):
                if not elem.tag.endswith("}row"):
                    continue
                row_num += 1
                if row_num == 1:
                    elem.clear()
                    continue
                if row_num == 2:
                    # Parse readable header names
                    headers: dict[int, str] = {}
                    for c in elem:
                        ref = c.attrib.get("r", "")
                        m = COL_RE.match(ref)
                        if not m:
                            continue
                        cidx = col_letters_to_idx(m.group(1))
                        ctype = c.attrib.get("t", "")
                        v_el = None
                        for ch in c:
                            if ch.tag.endswith("}v"):
                                v_el = ch
                                break
                        if v_el is None or v_el.text is None:
                            continue
                        val = shared_strings[int(v_el.text)] if ctype == "s" else v_el.text
                        headers[cidx] = val.strip()

                    def find_col(names: list[str]) -> int | None:
                        for target_name in names:
                            for ci, hv in headers.items():
                                if hv == target_name:
                                    return ci
                        return None

                    mapping = {
                        "thermal_coal_mw": find_col(["TOTAL_THM_ONLY|P"]),
                        "hydro_mw": find_col(["TOTAL_NLDC_HYD|P"]),
                        "gas_mw": find_col(["TOTAL_NLDC_GAS|P"]),
                        "nuclear_mw": find_col(["TOTAL_NLDC_NPC|P"]),
                        "wind_mw": find_col(["ALL_INDIA_WIND|P"]),
                        "solar_mw": find_col(["Solar", "ALL_IND_SOLAR|P"]),
                        "demand_mw": find_col(["NLDC_DEMAND|P"]),
                        "system_inertia": find_col(["INTRA_SYSTEM_INTERTIA|P"]),
                    }
                    for pos, fld in enumerate(fields):
                        ci = mapping[fld]
                        if ci is not None:
                            col_map[fld] = ci
                            idx_to_field_pos[ci] = pos
                            target_indices.add(ci)
                    target_indices.add(0)
                    elem.clear()
                    continue

                # Data row (row_num >= 3)
                ts_serial = None
                vals = [np.nan] * n_fields
                for c in elem:
                    ref = c.attrib.get("r", "")
                    m = COL_RE.match(ref)
                    if not m:
                        continue
                    cidx = col_letters_to_idx(m.group(1))
                    if cidx not in target_indices:
                        continue
                    ctype = c.attrib.get("t", "")
                    if ctype in ("e", "s", "str"):
                        continue
                    v_el = None
                    for ch in c:
                        if ch.tag.endswith("}v"):
                            v_el = ch
                            break
                    if v_el is None or v_el.text is None:
                        continue
                    try:
                        fval = float(v_el.text)
                    except ValueError:
                        continue
                    if cidx == 0:
                        ts_serial = fval
                    else:
                        vals[idx_to_field_pos[cidx]] = fval

                elem.clear()
                if ts_serial is None or ts_serial < 40000:
                    continue
                # Floor Excel serial day to exact integer hour
                hour_key = int(np.floor(ts_serial * 24.0 + 1e-7))
                if hour_key not in hourly_sums:
                    hourly_sums[hour_key] = np.zeros(n_fields, dtype=np.float64)
                    hourly_cnts[hour_key] = np.zeros(n_fields, dtype=np.int64)
                s_arr = hourly_sums[hour_key]
                c_arr = hourly_cnts[hour_key]
                for p_i in range(n_fields):
                    v = vals[p_i]
                    if not np.isnan(v):
                        s_arr[p_i] += v
                        c_arr[p_i] += 1

    rows = []
    for hk in sorted(hourly_sums.keys()):
        ts = EXCEL_EPOCH + dt.timedelta(hours=hk)
        s_arr = hourly_sums[hk]
        c_arr = hourly_cnts[hk]
        means = np.where(c_arr > 0, s_arr / np.maximum(c_arr, 1), np.nan)
        rec = {"timestamp": ts, "samples": int(c_arr[6])}
        for p_i, fld in enumerate(fields):
            rec[fld] = means[p_i]
        rec["source_file"] = path.name
        rows.append(rec)

    df = pd.DataFrame(rows)
    elapsed = time.perf_counter() - t0
    print(f"  [OK] {path.name:24s} -> {len(df):4d} hourly rows ({elapsed:5.2f}s)")
    return df


def main() -> None:
    t_start = time.perf_counter()
    print("=" * 78)
    print("EXTRACTING GRID-INDIA NLDC FUEL-MIX SCADA TELEMETRY (2022-04 TO 2023-12)")
    print("=" * 78)
    files = sorted(str(p) for p in RAW_DIR.glob("*.xlsx"))
    frames = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as ex:
        for res in ex.map(parse_single_scada_xlsx, files):
            if res is not None and len(res) > 0:
                frames.append(res)

    combined = pd.concat(frames, ignore_index=True)
    combined["timestamp"] = pd.to_datetime(combined["timestamp"])
    combined = combined.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="first").reset_index(drop=True)

    # Filter exact Apr 2022 - Dec 2023 window
    combined = combined[
        (combined["timestamp"] >= "2022-04-01 00:00:00") &
        (combined["timestamp"] <= "2023-12-31 23:00:00")
    ].reset_index(drop=True)

    # Clean rare telemetry glitches (zeros/negatives) via interpolation
    for col in ["thermal_coal_mw", "hydro_mw", "gas_mw", "nuclear_mw", "wind_mw", "solar_mw", "demand_mw"]:
        if col in ("thermal_coal_mw", "demand_mw"):
            combined.loc[combined[col] <= 1000, col] = np.nan
        elif col in ("hydro_mw", "gas_mw", "nuclear_mw"):
            combined.loc[combined[col] < 0, col] = np.nan
        elif col in ("wind_mw", "solar_mw"):
            combined.loc[combined[col] < 0, col] = 0.0
        combined[col] = combined[col].interpolate(method="linear").ffill().bfill()

    combined["total_dispatchable_mw"] = (
        combined["thermal_coal_mw"] + combined["hydro_mw"] + combined["gas_mw"] + combined["nuclear_mw"]
    )
    combined["net_demand_mw"] = combined["demand_mw"] - (combined["solar_mw"] + combined["wind_mw"])

    out_path = OUT_DIR / "grid_india_fuel_mix_hourly_2022_2023.csv"
    combined.to_csv(out_path, index=False)
    print("-" * 78)
    print(f"Saved: {out_path}")
    print(f"Shape: {combined.shape} | Range: {combined['timestamp'].min()} -> {combined['timestamp'].max()}")
    print("Fuel-Mix Summary (GW):")
    for col in ["thermal_coal_mw", "hydro_mw", "gas_mw", "nuclear_mw", "solar_mw", "wind_mw", "demand_mw", "net_demand_mw"]:
        s = combined[col] / 1000.0
        print(f"  {col:18s}: mean={s.mean():6.2f} GW | std={s.std():5.2f} | min={s.min():6.2f} | p90={s.quantile(0.9):6.2f} | max={s.max():6.2f}")
    print(f"Total extraction time: {time.perf_counter() - t_start:.1f}s")


if __name__ == "__main__":
    main()
