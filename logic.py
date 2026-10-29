# logic.py
import re
import pandas as pd
from config import *

def norm(s) -> str:
    if pd.isna(s): return ""
    return re.sub(r"\s+", " ", str(s)).strip().lower()

def is_date_filled(v) -> bool:
    if pd.isna(v): return False
    s = str(v).strip()
    if s in ("", "-", "NaT", "nan"): return False
    return True

def norm_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
    return df

def get_col(df: pd.DataFrame, name: str) -> str:
    target = re.sub(r"\s+", " ", name).strip().lower()
    for c in df.columns:
        if re.sub(r"\s+", " ", str(c)).strip().lower() == target:
            return c
    return None

def check_row(row: pd.Series, df: pd.DataFrame) -> dict:
    def val(col_name):
        c = get_col(df, col_name)
        return row[c] if c else None

    da_ok = is_date_filled(val(COL_DA_FACT))
    checklist_ok = is_date_filled(val(COL_CHECKLIST))

    eom_val = norm(val(COL_EOM))
    if eom_val in VALUE_OK or eom_val in VALUE_NOT_REQUIRED:
        eom_ok, tu_ok = True, True
    elif eom_val in VALUE_TU_RECEIVED:
        eom_ok, tu_ok = False, True
    else:
        eom_ok, tu_ok = False, False

    ovik_val = norm(val(COL_OVIK))
    ovik_ok = ovik_val in VALUE_OK or ovik_val in VALUE_NOT_REQUIRED

    ar_val = norm(val(COL_AR))
    ar_ok = ar_val in VALUE_OK or ar_val in VALUE_NOT_REQUIRED

    measure_ok = is_date_filled(val(COL_MEASURE))
    kp_ok      = is_date_filled(val(COL_KP))
    dp_ok      = is_date_filled(val(COL_DP))

    contractor_val = norm(val(COL_CONTRACTOR))
    contractor_ok  = contractor_val not in CONTRACTOR_BAD and contractor_val != ""

    checks = {
        "ДА факт":       da_ok,
        "Чек-лист АрДД": checklist_ok,
        "ТУ":            tu_ok,
        "ЭОМ":           eom_ok,
        "ОВиК":          ovik_ok,
        "АР":            ar_ok,
        "Замеры":        measure_ok,
        "КП":            kp_ok,
        "ДП":            dp_ok,
        "Подрядчик":     contractor_ok,
    }

    missing = [k for k, v in checks.items() if not v]
    
    return {
        "Готов к СМР": "ДА" if len(missing) == 0 else "НЕТ",
        "Отсутствует": ", ".join(missing) if missing else "—",
        "Кол-во отсутствующих": len(missing)
    }

def build_report(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = norm_columns(df_raw)
    results = [check_row(row, df) for _, row in df.iterrows()]
    res_df = pd.DataFrame(results)

    keep = [COL_ID, COL_ADDRESS, COL_MANAGER, COL_REGION, COL_SMR_PLAN, COL_SMR_FACT]
    keep_real = [get_col(df, k) for k in keep if get_col(df, k)]
    
    base = df[keep_real].reset_index(drop=True)
    out = pd.concat([base, res_df], axis=1)

    rename_map = {
        get_col(df, COL_ID): "Код",
        get_col(df, COL_ADDRESS): "Адрес",
        get_col(df, COL_MANAGER): "Менеджер",
        get_col(df, COL_REGION): "Регион",
        get_col(df, COL_SMR_PLAN): "План СМР",
        get_col(df, COL_SMR_FACT): "Факт СМР"
    }
    out = out.rename(columns={k: v for k, v in rename_map.items() if k})

    today = pd.Timestamp.today().normalize()
    def to_dt(x):
        try: return pd.to_datetime(x, dayfirst=True, errors="coerce")
        except: return pd.NaT

    if "План СМР" in out.columns:
        out["_plan_dt"] = out["План СМР"].apply(to_dt)
        out["_fact_filled"] = out["Факт СМР"].apply(is_date_filled) if "Факт СМР" in out.columns else False
        
        out["Просрочка"] = out.apply(
            lambda r: (today - r["_plan_dt"]).days
            if pd.notna(r["_plan_dt"]) and r["_plan_dt"] < today and not r["_fact_filled"]
            else 0,
            axis=1,
        )
        out = out.drop(columns=["_plan_dt", "_fact_filled"])
    else:
        out["Просрочка"] = 0

    return out