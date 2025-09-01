from functools import lru_cache
import pandas as pd
from .config import DATA_PATH
from .services.dataset import load_dataset
@lru_cache(maxsize=1)
def get_df() -> pd.DataFrame:
    return load_dataset(DATA_PATH)
