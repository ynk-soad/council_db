import pandas as pd
import os
import re

# ベースパス（必要に応じて変更）
BASE_DIR = "/Users/ynkhiru09/Downloads/ishigaki"

# 各ファイルパス
city_name = os.path.basename(BASE_DIR)
GIIN_YEAR_CSV = os.path.join(BASE_DIR, f"{city_name}_giinlist.csv")
TEIREI_CSV = os.path.join(BASE_DIR, f"{city_name}_teirei.csv")
KAIGI_CSV = os.path.join(BASE_DIR, f"{city_name}_kaigi.csv")
OUTPUT_CSV = os.path.join(BASE_DIR, f"{city_name}_giin.csv")

# ファイルの存在確認
if not os.path.exists(GIIN_YEAR_CSV):
    print(f"エラー: {GIIN_YEAR_CSV} が見つかりません")
    print("利用可能なファイル:")
    for file in os.listdir(BASE_DIR):
        if file.endswith('.csv'):
            print(f"  - {file}")
    exit(1)

if not os.path.exists(TEIREI_CSV):
    print(f"エラー: {TEIREI_CSV} が見つかりません")
    exit(1)

if not os.path.exists(KAIGI_CSV):
    print(f"エラー: {KAIGI_CSV} が見つかりません")
    exit(1)

# データ読み込み
giin_df = pd.read_csv(GIIN_YEAR_CSV, dtype=str)
teirei_df = pd.read_csv(TEIREI_CSV, dtype=str)
kaigi_df = pd.read_csv(KAIGI_CSV, dtype=str)

# 年情報を抽出
teirei_df["year"] = teirei_df["ID_teirei"].str[-6:].str[:4]

# 市議選日（YYYYMMDD）をintとして保持（NaNは除外）
giin_df["senkyo_date"] = pd.to_numeric(giin_df["市議選日"], errors='coerce').fillna(0).astype(int)

# 年ごとに定例会一覧を構築
year_to_teireis = (
    teirei_df.groupby("year")["ID_teirei"]
    .apply(list)
    .to_dict()
)

# 旧字体→新字体マッピング辞書
kanji_map = {
    "髙": "高", "﨑": "崎", "齋": "斎", "齊": "斉", "冨": "富", "澤": "沢",
    "德": "徳", "濵": "浜", "邊": "辺", "嶋": "島", "榮": "栄", "廣": "広",
    "實": "実", "圓": "円", "渕": "淵"
}

# 氏名を正規化する関数（NaN値に対応）
def normalize_kanji(text):
    if pd.isna(text) or text is None:
        return text
    text = str(text)
    for old, new in kanji_map.items():
        text = text.replace(old, new)
    return text

# giin_dfに正規化カラムを追加
giin_df["normalized_name"] = giin_df["name"].apply(normalize_kanji)

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

        # 遡って10人以上の定例会を探す
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

                # 重複除外（giin_idベース）
                existing_giin = set(df[df["ID_teirei"] == current_id]["giin_id"])
                additional = additional[~additional["giin_id"].isin(existing_giin)]

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
    """
    ID_teirei の YYYYMM に応じて、市議選日または市長選日を決定
    - election_dates: 市議選日のリスト (昇順)
    - mayor_election_dates: 市長選日のリスト (昇順)
    """
    year_month = int(str(id_teirei)[-6:])  # YYYYMM を取得
    latest_election_date = election_dates[0]  # 初期値は最古の市議選日
    latest_mayor_election_date = mayor_election_dates[0]  # 市長選の初期値

    for date in election_dates:
        if date // 100 > year_month:
            break
        latest_election_date = date

    for date in mayor_election_dates:
        if date // 100 > year_month:
            break
        latest_mayor_election_date = date

    return latest_election_date, latest_mayor_election_date

def assign_teirei_and_update_age(giin_df, teirei_df, kaigi_df, base_dir, merge_map):
    result = []
    
    # 市議選日を昇順にソート
    election_dates = sorted(giin_df[giin_df["shicho_or_giin"] == "0"]["市議選日"].dropna().unique())
    mayor_election_dates = sorted(giin_df[giin_df["shicho_or_giin"] == "1"]["市議選日"].dropna().unique())

    # 各定例会の議長・副議長を取得
    leader_info = extract_leaders_from_minutes(teirei_df, kaigi_df, base_dir)

    # YYYYMM を整数で取り出してから、年ごとに最小の定例会を選ぶ
    teirei_df["YYYYMM"] = teirei_df["ID_teirei"].str[-6:]
    teirei_df["YYYY"] = teirei_df["YYYYMM"].str[:4]
    teirei_df["MM"] = teirei_df["YYYYMM"].str[4:]
    teirei_df["YYYYMM_INT"] = teirei_df["YYYYMM"].astype(int)

    # 5月以降のみを対象
    teirei_df = teirei_df[teirei_df["MM"].astype(int) >= 5]

    # 年ごとに定例会を選択（補欠選挙後の定例会も考慮）
    selected_teirei_list = []
    
    for year in teirei_df["YYYY"].unique():
        # その年の定例会を取得
        group_sorted = teirei_df[teirei_df["YYYY"] == year].sort_values("YYYYMM_INT")
        
        # 通常の最小定例会（5月以降の最初の定例会）
        min_teirei = group_sorted.iloc[0]
        selected_teirei_list.append(min_teirei)
        
        # この年に補欠選挙があるかどうか判定（giin_id末尾ベース）
        # 例えば year = "2022" のとき
        giin_in_year = giin_df[
            (giin_df["shicho_or_giin"] == "0") &
            (giin_df["市議選日"] // 10000 == int(year))
        ].copy()
        
        if not giin_in_year.empty:
            # giin_idが有効なデータのみを対象にする
            valid_giin_in_year = giin_in_year[
                (giin_in_year["giin_id"].notna()) &
                (giin_in_year["giin_id"].str.len() >= 16)
            ]
            
            if not valid_giin_in_year.empty:
                valid_giin_in_year["giin_id_last3"] = valid_giin_in_year["giin_id"].str[-3:].astype(int)
                
                # 補欠議員の中で最も早い選挙日を取得（なければスキップ）
                hoketsu_dates = valid_giin_in_year[valid_giin_in_year["giin_id_last3"] >= 501]["市議選日"].unique()
                
                if len(hoketsu_dates) > 0:
                    hoketsu_yyyymm = min([d // 100 for d in hoketsu_dates])
                    after_hoketsu = group_sorted[group_sorted["YYYYMM_INT"] > hoketsu_yyyymm]
                    if not after_hoketsu.empty:
                        selected_teirei_list.append(after_hoketsu.iloc[0])

    # ↓ 選択された定例会をループ対象にする
    for teirei in selected_teirei_list:

        id_teirei = teirei["ID_teirei"]
        election_date, mayor_election_date = determine_election_date(id_teirei, election_dates, mayor_election_dates)

        # 通常＋補欠（マージ条件付き）両方を含める
        giin_normal = giin_df[
            (
                (giin_df["市議選日"] == election_date) | 
                (giin_df["市議選日"].isin([k for k, v in merge_map.items() if v == election_date]))
            ) &
            (giin_df["shicho_or_giin"] == "0")
        ]

        giin_normal = giin_normal[
        giin_normal["市議選日"] <= election_date
        ]
        
        # 補欠選挙の処理：補欠選挙より前の通常選挙データをベースとして使用
        if giin_normal.empty:
            # この定例会の年月を取得
            teirei_yyyymm = int(str(id_teirei)[-6:])
            teirei_date = pd.to_datetime(f"{teirei_yyyymm//100:04d}-{(teirei_yyyymm%100):02d}-01")
            
            # 補欠選挙日
            hoketsu_candidates = giin_df[
                (giin_df["shicho_or_giin"] == "0") &
                (giin_df["giin_id"].str[13:].astype(float) >= 501) &
                (giin_df["市議選日"] <= teirei_yyyymm)
            ]
            
            if not hoketsu_candidates.empty:
                # 補欠選挙日
                hoketsu_date = hoketsu_candidates["市議選日"].values[0]
                
                # 補欠より前に行われた通常選挙（giin_id末尾<500）で最新のものを探す
                tsujo_candidates = giin_df[
                    (giin_df["shicho_or_giin"] == "0") &
                    (giin_df["giin_id"].str[13:].astype(float) < 500) &
                    (giin_df["市議選日"] < hoketsu_date)
                ]
                
                if not tsujo_candidates.empty:
                    # 最新の通常選挙日を取得
                    latest_tsujo_date = tsujo_candidates["市議選日"].max()
                    
                    # その通常選挙のデータをベースとして補欠の定例会に付ける
                    base_tsujo = tsujo_candidates[tsujo_candidates["市議選日"] == latest_tsujo_date]
                    giin_normal = base_tsujo.copy()

       
        giin_mayor = giin_df[
            (giin_df["市議選日"] == mayor_election_date)  
            & (giin_df["shicho_or_giin"] == "1")
        ]

        # **議長・副議長を取得**
        gicho_name = leader_info.get(id_teirei, {}).get("gicho", "")
        gicho_sub_name = leader_info.get(id_teirei, {}).get("gicho_sub", "")

        for _, giin in giin_normal.iterrows():
            # NaNの場合は0として扱う
            age_at_election = int(giin["age"]) if pd.notna(giin["age"]) else 0
            updated_age = age_at_election + (int(str(id_teirei)[-6:-2]) - (giin["市議選日"] // 10000))  # 年齢の更新
            
            new_entry = giin.copy()
            new_entry["ID_teirei"] = id_teirei
            new_entry["市議選日"] = election_date
            new_entry["age"] = str(updated_age)

            # **議長・副議長のフラグをセット**
            new_entry["gicho"] = "1" if giin["name"] == gicho_name else ""
            new_entry["gicho_sub"] = "1" if giin["name"] == gicho_sub_name else ""

            result.append(new_entry)

        for _, giin in giin_mayor.iterrows():
            # NaNの場合は0として扱う
            age_at_election = int(giin["age"]) if pd.notna(giin["age"]) else 0
            updated_age = age_at_election + (int(str(id_teirei)[-6:-2]) - (giin["市議選日"] // 10000))  # 年齢の更新
            
            new_entry = giin.copy()
            new_entry["ID_teirei"] = id_teirei
            new_entry["市議選日"] = mayor_election_date
            new_entry["age"] = str(updated_age)

            # **市長データには議長・副議長の情報は不要**
            new_entry["gicho"] = ""
            new_entry["gicho_sub"] = ""

            result.append(new_entry)

    return pd.DataFrame(result, columns=[
        "ID_teirei", "市議選日", "giin_id", "city_name", "name", "kana", "age", "gender", "title",
        "new_and_old", "party", "kaiha", "gicho", "gicho_sub", "kansa", "shicho_or_giin"
    ])

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

def assign_teirei_by_election_date(giin_df, teirei_df):
    result = []

    teirei_df["YYYYMM"] = teirei_df["ID_teirei"].str[-6:].astype(int)
    teirei_df["YEAR"] = teirei_df["YYYYMM"] // 100
    teirei_df["MONTH"] = teirei_df["YYYYMM"] % 100
    teirei_df = teirei_df.sort_values(by=["YEAR", "MONTH"], ascending=True)

    for _, teirei in teirei_df.iterrows():
        id_teirei = teirei["ID_teirei"]
        yyyymm = teirei["YYYYMM"]
        # 1～4月なら前年の12月として扱う（たとえば202203 → 202112 → 20211231）
        ref_date = int(f"{teirei['YEAR']}{teirei['MONTH']:02d}30")

        # 定例会時点で有効な最も直近の市議選
        applicable_rows = giin_df[giin_df["senkyo_date"] <= ref_date]
        # senkyo_dateが0（元々NaN）の行を除外
        applicable_rows = applicable_rows[applicable_rows["senkyo_date"] > 0]
        if applicable_rows.empty:
            continue
        latest_date = applicable_rows["senkyo_date"].max()
        latest_rows = applicable_rows[applicable_rows["senkyo_date"] == latest_date]

        copied = latest_rows.copy()
        copied["ID_teirei"] = id_teirei
        result.append(copied)

    df = pd.concat(result, ignore_index=True)

    df["YYYYMM"] = df["ID_teirei"].str[-6:].astype(int)
    df["YEAR"] = df["YYYYMM"] // 100
    df["MONTH"] = df["YYYYMM"] % 100

    df_normal = df[df["shicho_or_giin"] == "0"].sort_values(by=["YEAR", "MONTH"], ascending=[False, False])
    df_mayor = df[df["shicho_or_giin"] == "1"].sort_values(by=["YEAR", "MONTH"], ascending=[False, False])

    final_df = pd.concat([df_normal, df_mayor], ignore_index=True)
    final_df.drop(columns=["senkyo_date", "YYYYMM", "YEAR", "MONTH"], inplace=True)

    return final_df

def assign_teirei_simple(giin_df, teirei_df):
    result = []
    
    
    # 定例会を年月で昇順ソート
    teirei_df["YYYYMM"] = teirei_df["ID_teirei"].str[-6:].astype(int)
    teirei_df["YEAR"] = teirei_df["YYYYMM"] // 100
    teirei_df["MONTH"] = teirei_df["YYYYMM"] % 100
    teirei_df = teirei_df.sort_values(by=["YEAR", "MONTH"], ascending=[True, True])

    # 各年ごとに定例会を展開
    giin_df["year"] = giin_df["ID_teirei"].str[-6:].str[:4]

    for _, teirei in teirei_df.iterrows():
        id_teirei = teirei["ID_teirei"]
        year = str(id_teirei)[-6:-2]  # YYYY
        month = int(str(id_teirei)[-2:])  # MM

        # 5月以前（1～4月）なら前年の会派情報を使用
        ref_year = str(int(year) - 1) if month < 5 else year

        # 対象年のデータを抽出して複製
        giin_subset = giin_df[giin_df["year"] == ref_year]
        copied = giin_subset.copy()
        copied["ID_teirei"] = id_teirei
        result.append(copied)


    df = pd.concat(result, ignore_index=True)

    # 昇順ソートして市長データは最後にする（年降順・月昇順）
    df["YYYYMM"] = df["ID_teirei"].str[-6:].astype(int)
    df["YEAR"] = df["YYYYMM"] // 100
    df["MONTH"] = df["YYYYMM"] % 100

    df_normal = df[df["shicho_or_giin"] == "0"].sort_values(by=["YEAR", "MONTH"], ascending=[False, False])
    df_mayor = df[df["shicho_or_giin"] == "1"].sort_values(by=["YEAR", "MONTH"], ascending=[False, False])

    final_df = pd.concat([df_normal, df_mayor], ignore_index=True)
    final_df.drop(columns=["senkyo_date", "YYYYMM", "YEAR", "MONTH", "year"], inplace=True)

    return final_df

def main():
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
    final_df_output.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"議員テーブルを出力しました: {OUTPUT_CSV}")

# 処理実行＆保存
if __name__ == "__main__":
    main()
