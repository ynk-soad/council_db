import os
import glob
import math
import pandas as pd

# ★ここを自分の環境に合わせて書き換える★
GIIN_DIR = "/workspaces/council_db/data/九州議員テーブル"

pattern = os.path.join(GIIN_DIR, "*_giin.csv")
paths = glob.glob(pattern)

rows = []

# 4年ごとの議員年齢を見るターゲット年
AGE_TARGET_YEARS = [2011, 2015, 2019, 2023]
# 会派は 2011〜2024 の各年
ALL_YEARS = list(range(2011, 2025))

for path in paths:
    df = pd.read_csv(path)

    if "shicho_or_giin" not in df.columns:
        # 想定外のファイルはスキップ
        continue

    # city_code = ファイル名（akune_giin.csv → akune）
    city_code = os.path.basename(path).replace("_giin.csv", "")
    # city_name = 日本語市名（どの行も同じ前提）
    city_name = df["city_name"].iloc[0]

    # 文字列化
    df["市議選日"] = df["市議選日"].astype(str)
    df["ID_teirei"] = df["ID_teirei"].astype(str)

    # ───────── 議員側データのみ利用 ─────────
    giin_df = df[df["shicho_or_giin"] == 0].copy()
    if giin_df.empty:
        continue

    # ───────── 議員男女比（全期間対象） ─────────
    g_all = giin_df["gender"].astype(str)
    male_count_all = (g_all == "男").sum()
    female_count_all = (g_all == "女").sum()
    total_sex_all = male_count_all + female_count_all

    if total_sex_all > 0:
        male_pct_all = round(male_count_all / total_sex_all * 100, 1)
        female_pct_all = round(female_count_all / total_sex_all * 100, 1)
    else:
        male_pct_all = None
        female_pct_all = None

    # ───────── 市長の年齢・性別：giin_id ごとに抜き出す ─────────
    shicho_df = df[df["shicho_or_giin"] == 1].copy()
    shicho_terms = []

    if not shicho_df.empty:
        # giin_id ごとにまとめる
        # ・市議選日: first（giin_id内で同じはず）
        # ・年齢: min（その任期で一番若い＝就任時に近い値）
        # ・性別: mode（なければ先頭）
        shicho_grouped = (
            shicho_df
            .groupby("giin_id", as_index=False)
            .apply(
                lambda g: pd.Series({
                    "市議選日": g["市議選日"].iloc[0],
                    "age": g["age"].min(),
                    "gender": (
                        g["gender"].dropna().mode().iloc[0]
                        if not g["gender"].dropna().empty
                        else None
                    )
                })
            )
        )

        # 市議選日の古い順に並べ替え（= 1期目 → 2期目 → …）
        shicho_grouped = shicho_grouped.sort_values("市議選日")

        # listにして後で列展開
        for _, row_term in shicho_grouped.iterrows():
            shicho_terms.append({
                "election": row_term["市議選日"],
                "age": row_term["age"],
                "gender": row_term["gender"],
            })

    # ───────── 4年ごとの議員平均年齢 ─────────
    age_df = giin_df.dropna(subset=["age"]).copy()

    if age_df.empty:
        giin_age_by_year = {year: None for year in AGE_TARGET_YEARS}
        giin_age_avg = None
    else:
        age_by_teirei = (
            age_df.groupby("ID_teirei")["age"]
            .mean()
            .reset_index(name="平均年齢")
        )
        age_by_teirei["year"] = age_by_teirei["ID_teirei"].str[-6:-2]

        yearly_age = (
            age_by_teirei.groupby("year")["平均年齢"]
            .mean()
            .round(1)
        )

        giin_age_by_year = {}
        for year in AGE_TARGET_YEARS:
            y_str = str(year)
            if y_str in yearly_age.index:
                giin_age_by_year[year] = float(yearly_age.loc[y_str])
            else:
                giin_age_by_year[year] = None

        valid_age = [v for v in giin_age_by_year.values() if v is not None]
        if valid_age:
            giin_age_avg = float(round(sum(valid_age) / len(valid_age), 1))
        else:
            giin_age_avg = None

    # ───────── 会派数：Rスクリプトと同じロジック ─────────
    kaiha_df = giin_df.dropna(subset=["kaiha"]).copy()

    if kaiha_df.empty:
        kaiha_by_year = {year: None for year in ALL_YEARS}
        kaiha_all_avg = None
    else:
        kaiha_counts = (
            kaiha_df.groupby("ID_teirei")["kaiha"]
            .nunique()
            .reset_index(name="会派の種類数")
        )
        kaiha_counts["year"] = kaiha_counts["ID_teirei"].str[-6:-2]

        yearly_avg = (
            kaiha_counts.groupby("year")["会派の種類数"]
            .mean()
            .round(1)
        )

        kaiha_by_year = {}
        for year in ALL_YEARS:
            y_str = str(year)
            if y_str in yearly_avg.index:
                kaiha_by_year[year] = float(yearly_avg.loc[y_str])
            else:
                kaiha_by_year[year] = None

        if not yearly_avg.empty:
            kaiha_all_avg = float(round(yearly_avg.mean(), 1))
        else:
            kaiha_all_avg = None

    # ───────── 1 行分をまとめる ─────────
    row = {
        "city_code": city_code,
        "city_name": city_name,
        "議員男女比/男(%)": male_pct_all,       # 全期間の男性割合
        "議員男女比/女(%)": female_pct_all,     # 全期間の女性割合
    }

    # 4年ごとの議員平均年齢
    for year in AGE_TARGET_YEARS:
        col = f"議員平均年齢_{year}"
        row[col] = giin_age_by_year[year]

    row["議員平均年齢_平均"] = giin_age_avg

    # 市長任期ごとの年齢・性別（giin_id 単位）
    # 1期目, 2期目, 3期目…の順に列を作る
        # 市長任期ごとの年齢・性別（giin_id 単位）
    # 「年齢_性別」の1カラムにまとめる（例: 69_男）
    for i, term in enumerate(shicho_terms, start=1):
        age = term["age"]
        gender = term["gender"]

        # 年齢・性別それぞれを文字列化（欠損は空文字）
        age_str = "" if pd.isna(age) else str(int(age))
        gender_str = "" if gender is None or (isinstance(gender, float) and math.isnan(gender)) else str(gender)

        if age_str and gender_str:
            value = f"{age_str}_{gender_str}"   # 例: "69_男"
        elif age_str:
            value = age_str                      # 片方だけあるレアケース
        elif gender_str:
            value = gender_str
        else:
            value = None

        row[f"市長{i}期目_年齢性別"] = value


    # 年ごとの会派数 2011〜2024
    for year in ALL_YEARS:
        col = f"kaiha_{year}"
        row[col] = kaiha_by_year[year]

    row["kaiha_avg"] = kaiha_all_avg

    rows.append(row)

# まとめて DataFrame にして CSV 出力
out_df = pd.DataFrame(rows)
out_df = out_df.sort_values("city_code")

out_path = os.path.join(GIIN_DIR, "九州_giin_summary_kaiha_age_gender_shicho_giinid.csv")
out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

print(f"書き出し完了: {out_path}")
print(out_df.head())
