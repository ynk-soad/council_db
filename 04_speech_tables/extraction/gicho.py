import os
import re
import pandas as pd


BASE_DIR = "/Users/ynkhiru09/Downloads/miyazaki"


def has_gicho_1(df):
    """gicho列に1または1.0が存在するか"""
    return df['gicho'].dropna().astype(str).str.strip().isin(['1', '1.0']).any()

def assign_gicho_if_absent(filepath):
    try:
        df = pd.read_csv(filepath, dtype=str)

        # 必須列の存在チェック
        required_cols = {'speaker', 'gicho', 'gicho_sub'}
        if not required_cols.issubset(df.columns):
            return

        # すでにgicho=1があるならスキップ
        if has_gicho_1(df):
            return

        # speaker列から最頻発言者を抽出
        if df['speaker'].dropna().empty:
            return

        most_common_speaker = df['speaker'].dropna().value_counts().idxmax()

        # gicho, gicho_sub を更新
        df['gicho'] = df.apply(
            lambda row: '1.0' if row['speaker'] == most_common_speaker else row['gicho'], axis=1)
        df['gicho_sub'] = df.apply(
            lambda row: '' if row['speaker'] == most_common_speaker else row['gicho_sub'], axis=1)

        df.to_csv(filepath, index=False)
        print(f"[更新] {os.path.basename(filepath)}")

    except Exception as e:
        print(f"[エラー] {os.path.basename(filepath)}: {e}")

def process_folder(folder_path):
    pattern = re.compile(r'^\d{13}\.csv$')
    for fname in os.listdir(folder_path):
        if pattern.match(fname):
            assign_gicho_if_absent(os.path.join(folder_path, fname))

if __name__ == "__main__":
    if not os.path.isdir(BASE_DIR):
        print(f"フォルダが存在しません: {BASE_DIR}")
    else:
        process_folder(BASE_DIR)
