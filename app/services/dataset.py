import pandas as pd
EXPECTED_COLS = ["Name","Platform","Year_of_Release","Genre","Publisher","NA_Sales","EU_Sales","JP_Sales","Other_Sales","Global_Sales","Critic_Score","Critic_Count","User_Score","User_Count","Developer","Rating"]
def load_dataset(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    for c in EXPECTED_COLS:
        if c not in df.columns:
            df[c] = pd.NA
    num_cols = ["NA_Sales","EU_Sales","JP_Sales","Other_Sales","Global_Sales","Critic_Score","Critic_Count","User_Score","User_Count"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Year_of_Release"] = pd.to_numeric(df["Year_of_Release"], errors="coerce").astype("Int64")
    df["name_lower"] = df["Name"].astype(str).str.lower()
    return df
def year_range(df: pd.DataFrame):
    years = df["Year_of_Release"].dropna().astype(int)
    return None if years.empty else (int(years.min()), int(years.max()))
