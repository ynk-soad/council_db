import pandas as pd
import os
import re
# ベースパス
BASE_DIR = "/Users/ynkhiru09/Downloads/ishigaki"

# 各テーブル名を自動取得
city_name = os.path.basename(BASE_DIR)
GIIN_CSV = os.path.join(BASE_DIR, f"{city_name}_giinlist.csv")
TEIREI_CSV = os.path.join(BASE_DIR, f"{city_name}_teirei.csv")
KAIGI_CSV = os.path.join(BASE_DIR, f"{city_name}_kaigi.csv")


# **CSVファイルを読み込み**
giin_df = pd.read_csv(GIIN_CSV, dtype=str)
teirei_df = pd.read_csv(TEIREI_CSV, dtype=str)
kaigi_df = pd.read_csv(KAIGI_CSV, dtype=str)

giin_df = giin_df.dropna(how="all")


def extract_leaders_from_minutes(teirei_df, kaigi_df, base_dir):
    
    """
    各定例会 (ID_teirei) のすべての議事録を参照して議長と副議長を抽出
    - 同じ年のすべての定例会に適用
    - 副議長が埋まっていなかった場合は、同じ年の他の定例会や翌年の最初の定例会を参照して補完
    - 副議長が最初に登場したら、それより前の定例会にも適用
    - 未来の定例会から情報を補完
    """
    leader_info = {}  # { ID_teirei: {"gicho": "議員名", "gicho_sub": "議員名"} }
    previous_gicho = None  # 直前の議長
    previous_gicho_sub = None  # 直前の副議長
    year_leader_map = {}  # { YYYY: {"gicho": "議員名", "gicho_sub": "議員名"} }

    # **定例会ごとに複数の議事録を参照**
    for id_teirei, kaigi_ids in kaigi_df.groupby("ID_teirei")["kaigi_id"]:
        gicho_name = None
        gicho_sub_name = None

        # 各定例会のすべての議事録を対象にする
        for kaigi_id in kaigi_ids:
            minutes_path = os.path.join(base_dir, f"{kaigi_id}.txt")

            # **議事録が存在しない場合はスキップ**
            if not os.path.exists(minutes_path):
                continue

            # **議事録を開いて読み込む**
            with open(minutes_path, "r", encoding="utf-8-sig") as file:
                minutes_text = file.read()

            # **議長を抽出**
            gicho_match = re.search(r"(?:○)?議長（(.+?)(?:議員|君)）", minutes_text)
            gicho_sub_match = re.search(r"(?:○)?副議長（(.+?)(?:議員|君)）", minutes_text)

            if gicho_match:
                gicho_name = gicho_match.group(1)
            if gicho_sub_match:
                gicho_sub_name = gicho_sub_match.group(1)

        # **直前のデータを適用**
        if not gicho_name:
            gicho_name = previous_gicho
        if not gicho_sub_name:
            gicho_sub_name = previous_gicho_sub

        # **新しい議長・副議長が登場したら更新**
        if gicho_name:
            previous_gicho = gicho_name  
        if gicho_sub_name:
            previous_gicho_sub = gicho_sub_name  

        # **この年のデータを記録**
        year = str(id_teirei)[:4]
        if year not in year_leader_map:
            year_leader_map[year] = {"gicho": gicho_name, "gicho_sub": gicho_sub_name}

        # **結果を保存**
        leader_info[id_teirei] = {
            "gicho": gicho_name,
            "gicho_sub": gicho_sub_name
        }

    return leader_info

def supplement_small_teireikai(df, threshold=10):
    df = df.copy()
    giin_df = df[df["shicho_or_giin"] == "0"]
    teirei_order = sorted(df["ID_teirei"].unique())  # ID順（昇順）

    # 定例会ごとの市議人数をカウント
    teirei_counts = giin_df.groupby("ID_teirei")["giin_id"].count().to_dict()

    output_rows = []

    for idx, current_id in enumerate(teirei_order):
        current_count = teirei_counts.get(current_id, 0)

        if current_count > threshold:
            continue  # 補完不要

        city_name = df[df["ID_teirei"] == current_id]["city_name"].iloc[0]

        
        for prev_idx in range(idx - 1, -1, -1):
            prev_id = teirei_order[prev_idx]
            prev_city = df[df["ID_teirei"] == prev_id]["city_name"].iloc[0]
            if prev_city != city_name:
                continue  # 他市の定例会はスキップ
            prev_count = teirei_counts.get(prev_id, 0)
            if prev_count > threshold:
                # 議員を抽出して current_id に割り当てて追加
                additional = df[
                    (df["ID_teirei"] == prev_id) &
                    (df["shicho_or_giin"] == "0")
                ].copy()
                additional["ID_teirei"] = current_id

                output_rows.append(additional)
                break  # 最初に見つかった定例会のみ使う

    if output_rows:
        additional_df = pd.concat(output_rows, ignore_index=True)
        combined_df = pd.concat([df, additional_df], ignore_index=True).drop_duplicates()
        return combined_df
    else:
        return df
    
def sort_final_dataframe(df):
    # 並び順の基準を作成
    df["YYYYMM"] = df["ID_teirei"].str[-6:].astype(int)
    df["ELECTION_DATE"] = df["市議選日"].astype(int)

    # 並び順:
    # 1. ID_teirei 昇順（もしくは必要に応じて降順）
    # 2. 市議選日 降順（補欠→通常）
    # 3. giin_id 昇順（安定化）

    df = df.sort_values(by=["ID_teirei", "ELECTION_DATE", "giin_id"], ascending=[True, False, True])

    df.drop(columns=["YYYYMM", "ELECTION_DATE"], inplace=True)
    return df





def determine_election_date(id_teirei, election_dates, mayor_election_dates):
    year_month = int(str(id_teirei)[-6:])
    latest_election_date = min(election_dates)
    latest_mayor_election_date = min(mayor_election_dates)


    for date in sorted(election_dates):
        if date // 100 > year_month:
            break
        latest_election_date = date

    for date in sorted(mayor_election_dates):
        if date // 100 > year_month:
            break
        latest_mayor_election_date = date

    return latest_election_date, latest_mayor_election_date





def assign_teirei_and_update_age(giin_df, teirei_df, kaigi_df, base_dir, merge_map):
    result = []

    giin_df["市議選日"] = giin_df["市議選日"].astype(int)
    # 通常選挙日リスト
    normal_election_dates = sorted(set(
        [int(v) for v in merge_map.values()] +
        giin_df[(giin_df["shicho_or_giin"] == "0") & (giin_df["giin_id_suffix"] <= 500)]["市議選日"].dropna().astype(int).tolist()
    ))
    # 補欠選挙日リスト
    hoketsu_election_dates = sorted(set(
        [int(k) for k in merge_map.keys()] +
        giin_df[(giin_df["shicho_or_giin"] == "0") & (giin_df["giin_id_suffix"] >= 501)]["市議選日"].dropna().astype(int).tolist()
    ))

    mayor_election_dates = sorted(giin_df[giin_df["shicho_or_giin"] == "1"]["市議選日"].dropna().unique())

    # 各定例会の議長・副議長を取得
    leader_info = extract_leaders_from_minutes(teirei_df, kaigi_df, base_dir)

    teirei_df["YYYYMM"] = teirei_df["ID_teirei"].str[-6:]
    teirei_df["YYYY"] = teirei_df["YYYYMM"].str[:4]
    teirei_df["MM"] = teirei_df["YYYYMM"].str[4:]
    teirei_df["YYYYMM_INT"] = teirei_df["YYYYMM"].astype(int)
    teirei_df = teirei_df[teirei_df["MM"].astype(int) >= 5]

    selected_teirei_list = []
    for year in teirei_df["YYYY"].unique():
        group_sorted = teirei_df[teirei_df["YYYY"] == year].sort_values("YYYYMM_INT")
        min_teirei = group_sorted.iloc[0]
        selected_teirei_list.append(min_teirei)
        giin_in_year = giin_df[
            (giin_df["shicho_or_giin"] == "0") &
            (giin_df["市議選日"] // 10000 == int(year))
        ].copy()
        if not giin_in_year.empty:
            valid_giin_in_year = giin_in_year[
                (giin_in_year["giin_id"].notna()) &
                (giin_in_year["giin_id"].str.len() >= 16)
            ]
            if not valid_giin_in_year.empty:
                valid_giin_in_year["giin_id_last3"] = valid_giin_in_year["giin_id"].str[-3:].astype(int)
                hoketsu_dates = valid_giin_in_year[valid_giin_in_year["giin_id_last3"] >= 501]["市議選日"].unique()
                if len(hoketsu_dates) > 0:
                    hoketsu_yyyymm = min([d // 100 for d in hoketsu_dates])
                    after_hoketsu = group_sorted[group_sorted["YYYYMM_INT"] > hoketsu_yyyymm]
                    if not after_hoketsu.empty:
                        selected_teirei_list.append(after_hoketsu.iloc[0])

    for teirei in selected_teirei_list:
        id_teirei = teirei["ID_teirei"]
        election_date, mayor_election_date = determine_election_date(id_teirei, normal_election_dates, mayor_election_dates)

        # 通常選挙議員
        giin_normal = giin_df[
            (giin_df["市議選日"] == election_date) &
            (giin_df["shicho_or_giin"] == "0") &
            (giin_df["giin_id_suffix"] <= 500)
        ]
        # 補欠選挙議員（もしこの定例会が補欠選挙に該当する場合）
        giin_hoketsu = pd.DataFrame()
        if int(id_teirei[-6:]) in hoketsu_election_dates:
            giin_hoketsu = giin_df[
                (giin_df["市議選日"] == int(id_teirei[-6:])) &
                (giin_df["shicho_or_giin"] == "0") &
                (giin_df["giin_id_suffix"] >= 501)
            ]
        # 重複しないように結合
        giin_all = pd.concat([giin_normal, giin_hoketsu]).drop_duplicates(subset=["giin_id"])

        giin_mayor = giin_df[
            (giin_df["市議選日"] == mayor_election_date)  
            & (giin_df["shicho_or_giin"] == "1")
        ]

        gicho_name = leader_info.get(id_teirei, {}).get("gicho", "")
        gicho_sub_name = leader_info.get(id_teirei, {}).get("gicho_sub", "")

        for _, giin in giin_all.iterrows():
            age_at_election = int(giin["age"]) if pd.notna(giin["age"]) else 0
            updated_age = age_at_election + (int(str(id_teirei)[-6:-2]) - (giin["市議選日"] // 10000))
            new_entry = giin.copy()
            new_entry["ID_teirei"] = id_teirei
            new_entry["市議選日"] = election_date if giin["giin_id_suffix"] <= 500 else int(id_teirei[-6:])
            new_entry["age"] = str(updated_age)
            new_entry["gicho"] = "1" if giin["name"] == gicho_name else ""
            new_entry["gicho_sub"] = "1" if giin["name"] == gicho_sub_name else ""
            result.append(new_entry)

        for _, giin in giin_mayor.iterrows():
            age_at_election = int(giin["age"]) if pd.notna(giin["age"]) else 0
            updated_age = age_at_election + (int(str(id_teirei)[-6:-2]) - (giin["市議選日"] // 10000))
            new_entry = giin.copy()
            new_entry["ID_teirei"] = id_teirei
            new_entry["市議選日"] = mayor_election_date
            new_entry["age"] = str(updated_age)
            new_entry["gicho"] = ""
            new_entry["gicho_sub"] = ""
            result.append(new_entry)

    return pd.DataFrame(result, columns=[
        "ID_teirei", "市議選日", "giin_id", "city_name", "name", "kana", "age", "gender", "title",
        "new_and_old", "party", "kaiha", "gicho", "gicho_sub", "kansa", "shicho_or_giin"
    ])



# **shicho_or_giin == 1 のデータを最後にまとめる**
def process_final_dataframe(df):
    # `ID_teirei` の YYYYMM を抽出してソート用のカラムを作成
    df["YYYYMM"] = df["ID_teirei"].str[-6:].astype(int)
    df["YEAR"] = df["YYYYMM"] // 100  # 年 (YYYY)
    df["MONTH"] = df["YYYYMM"] % 100  # 月 (MM)

    # 市長データと議員データを分離
    df_normal = df[df["shicho_or_giin"] == "0"]
    df_mayor = df[df["shicho_or_giin"] == "1"]

    # **議員データ: ID_teirei の年降順、月昇順**
    df_normal = df_normal.sort_values(by=["YEAR", "MONTH"], ascending=[False, True])

    # **市長データ: ID_teirei の年降順、月昇順**
    df_mayor = df_mayor.sort_values(by=["YEAR", "MONTH"], ascending=[False, True])

    # **市長データを最後にまとめる**
    final_df = pd.concat([df_normal, df_mayor], ignore_index=True)

    # **不要なソート用カラムを削除**
    final_df.drop(columns=["YYYYMM", "YEAR", "MONTH"], inplace=True)

    return final_df

def load_csv_files():
    if not os.path.exists(GIIN_CSV):
        raise FileNotFoundError(f"議員テーブル {GIIN_CSV} が見つかりません")

    if not os.path.exists(TEIREI_CSV):
        raise FileNotFoundError(f"定例会テーブル {TEIREI_CSV} が見つかりません")

    if not os.path.exists(KAIGI_CSV):
        raise FileNotFoundError(f"会議テーブル {KAIGI_CSV} が見つかりません")

    giin_df = pd.read_csv(GIIN_CSV, dtype=str)
    teirei_df = pd.read_csv(TEIREI_CSV, dtype=str)
    kaigi_df = pd.read_csv(KAIGI_CSV, dtype=str)

    return giin_df, teirei_df, kaigi_df


def main():
    # CSV読み込み
    giin_df, teirei_df, kaigi_df = load_csv_files()

    # giin_id の末尾番号（13桁目以降）を整数として抽出する安全な方法
    giin_df = giin_df.copy()
    giin_df["giin_id"] = giin_df["giin_id"].astype(str)
    giin_df["giin_id_suffix"] = giin_df["giin_id"].str[13:]
    giin_df = giin_df[giin_df["giin_id_suffix"].str.isnumeric()]
    giin_df["giin_id_suffix"] = giin_df["giin_id_suffix"].astype(int)

    # 補欠選挙データ（suffix >= 501 の市議）
    hoketsu_df = giin_df[
        (giin_df["shicho_or_giin"] == "0") &
        (giin_df["giin_id_suffix"] >= 501)
    ]

    # 通常選挙データ（suffix <= 500 の市議）
    normal_df = giin_df[
        (giin_df["shicho_or_giin"] == "0") &
        (giin_df["giin_id_suffix"] <= 500)
    ]

    # 数値として扱う（文字列→int）
    giin_df["市議選日"] = giin_df["市議選日"].astype(int)

    # 補欠選挙ごとの通常選挙を見つける処理
    latest_normal_dates = {}

    for (city, hoketsu_date) in hoketsu_df[["city_name", "市議選日"]].drop_duplicates().itertuples(index=False):
        # 通常選挙のうち、補欠選挙より前のもの
        candidates = normal_df[
            (normal_df["city_name"] == city) &
            (normal_df["市議選日"] < hoketsu_date)
        ]
        if not candidates.empty:
            latest = candidates["市議選日"].max()
            latest_normal_dates[(city, hoketsu_date)] = latest

    # 結果を確認用に出力（必要に応じてこの下に定例会データとのマージ処理などを書く）
    for key, val in latest_normal_dates.items():
        print(f"{key[0]}の補欠選挙（{key[1]}）に対応する通常選挙: {val}")

    # merge_mapを構築（補欠選挙日 → 通常選挙日のマッピング）
    merge_map = {}
    for (city, hoketsu_date), normal_date in latest_normal_dates.items():
        merge_map[hoketsu_date] = normal_date

    final_df = assign_teirei_and_update_age(giin_df, teirei_df, kaigi_df, BASE_DIR, merge_map)
    final_df = supplement_small_teireikai(final_df, threshold=10)
    final_df = sort_final_dataframe(final_df)
    final_df = process_final_dataframe(final_df)

    # 年情報を抽出（定例会データのみ）
    final_df["YEAR"] = final_df["ID_teirei"].str[-6:].str[:4]
    
    # 定例会データと市長データに分ける
    df_normal = final_df[final_df["shicho_or_giin"] == "0"].copy()
    df_mayor = final_df[final_df["shicho_or_giin"] == "1"].copy()

    output_rows = []

    # 年の降順で並べる
    for year in sorted(df_normal["YEAR"].dropna().unique(), reverse=True):
        group = df_normal[df_normal["YEAR"] == year]
        output_rows.append(group)
        output_rows.append(pd.DataFrame([[""] * len(group.columns)], columns=group.columns))  # 空行

    # 市長データを最後に追加
    if not df_mayor.empty:
        output_rows.append(df_mayor)

    # 出力連結
    final_df_output = pd.concat(output_rows, ignore_index=True).drop(columns=["YEAR"])

    # 出力
    output_path = os.path.join(BASE_DIR, f"{city_name}_giin_year.csv")
    final_df_output.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"csvを出力しました: {output_path}")





# 実行
if __name__ == "__main__":
    main()
