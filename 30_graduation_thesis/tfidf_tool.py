import os
import re
import MeCab
import numpy as np
import csv
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

# ==========================================================
# ★★★ ここだけ触ればOK（比較の切替） ★★★
# ==========================================================
path = "/workspaces/council_db/data/kagoshima"
output_file = "/workspaces/council_db/data/kagoshima/tfidf_compare_by_year.csv"

# compare_mode:
#   "gender"      : 男 / 女
#   "mayor_giin"  : 市長 / 議員（shicho_or_giin が 1/0 or 1.0/0.0 想定）
#   "kaiha_2"     : 会派2つを指定して比較（例：A会派 vs B会派）
#   "age_bins"    : 年齢をビン分けして比較（例：20代/30代/40代...）
compare_mode = "age_bins"

TOPN = 10  # 各グループの上位語数

# kaiha_2 用（compare_mode="kaiha_2" のときだけ使う）
kaiha_a = "新政みらい"
kaiha_b = "公明党"

# age_bins 用（compare_mode="age_bins" のときだけ使う）
# age列の想定：整数っぽい文字列（例："34"）
age_column = "age"
age_bins = [(20, 29), (30, 39), (40, 49), (50, 59), (60, 200)]  # (min,max)
# ==========================================================


# ==========================================================
# ストップワード（数字・元号系のノイズも除外）
# ==========================================================
stop_words = [
    "僕", "部", "課","議員","登壇", "だれ", "すべて", "室", "181554https", "181602https", "ページ", "id",
    "平成", "令和", "昭和", "年度", "年", "月", "日", "期", "点"
]

KANJI_NUM_RE = re.compile(r'^[0-9一二三四五六七八九十百千万億兆]+$')


# ==========================================================
# MeCab Tagger（1回だけ生成）
# ==========================================================
try:
    import unidic_lite
    mecab = MeCab.Tagger(f"-d {unidic_lite.DICDIR}")
    mecab.parse("")
except Exception:
    mecab = MeCab.Tagger()
    mecab.parse("")


# ==========================================================
# TF-IDF
# ==========================================================
def tfidf_fit_transform(docs):
    """
    docs: list[str]（各docは年単位など）
    returns: (tfidf_x, index, feature_words)
    """
    # 年の数が少ないと max_df=0.5 が落ちることがあるので安全側
    max_df_val = 1.0 if len(docs) < 3 else 0.5

    vectorizer = TfidfVectorizer(
        token_pattern=r'(?u)\b\w+\b',
        min_df=1,
        max_df=max_df_val,
        max_features=2000
    )
    tfidf_x = vectorizer.fit_transform(docs).toarray()
    index = tfidf_x.argsort(axis=1)[:, ::-1]
    feature_names = np.array(vectorizer.get_feature_names_out())
    feature_words = feature_names[index]
    return tfidf_x, index, feature_words


# ==========================================================
# wakati（名詞のみ。数字・漢数字のみは落とす）
# ==========================================================
def extract_words(text):
    """
    1発言 -> 単語リスト（名詞連結の元ロジックを維持）
    """
    word = ""
    words = []

    node = mecab.parseToNode(text)
    while node:
        if node.feature.startswith("名詞"):
            if "人名" in node.feature:
                node = node.next
                continue
            if node.surface not in stop_words:
                if node.feature.split(",")[1] != "数":
                    if not KANJI_NUM_RE.fullmatch(node.surface):
                        word += node.surface

        else:
            if word != "":
                words.append(word)
                word = ""
        node = node.next

    return words


# ==========================================================
# グループ仕様（比較ごとの設定）
# ==========================================================
def get_compare_spec():
    """
    compare_mode に応じて
    - group_col: 比較に使う列名
    - groups: {key: label}
    - selector(row): row -> group_key or None
    を返す
    """
    if compare_mode == "gender":
        group_col = "gender"
        groups = {"男": "男", "女": "女"}

        def selector(row):
            v = str(row.get(group_col, ""))
            return v if v in groups else None

        return group_col, groups, selector

    if compare_mode == "mayor_giin":
        group_col = "shicho_or_giin"
        # データによって "1"/"0" "1.0"/"0.0" が混ざるので両対応
        groups = {"1": "市長", "1.0": "市長", "0": "議員", "0.0": "議員"}

        def selector(row):
            v = str(row.get(group_col, ""))
            return v if v in groups else None

        return group_col, groups, selector

    if compare_mode == "kaiha_2":
        group_col = "kaiha"
        groups = {kaiha_a: kaiha_a, kaiha_b: kaiha_b}

        def selector(row):
            v = str(row.get(group_col, ""))
            return v if v in groups else None

        return group_col, groups, selector

    if compare_mode == "age_bins":
        group_col = age_column
        # binsをラベル化
        groups = {}
        for a, b in age_bins:
            groups[f"{a}-{b}"] = f"{a}-{b}"

        def selector(row):
            v = row.get(group_col, None)
            if v is None:
                return None
            try:
                age = int(float(str(v)))
            except Exception:
                return None

            for a, b in age_bins:
                if a <= age <= b:
                    return f"{a}-{b}"
            return None

        return group_col, groups, selector

    raise ValueError("compare_mode が不正です")


# ==========================================================
# メイン処理
# ==========================================================
def main():
    if not os.path.isdir(path):
        raise ValueError("path がフォルダではありません: " + str(path))

    files = [f for f in os.listdir(path) if f.endswith(".csv")]
    if not files:
        print("CSVファイルが見つかりません。")
        return

    group_col, groups, selector = get_compare_spec()

    # year -> list[word] をグループごとに持つ
    bucket_all = {}  # year -> list[word]
    bucket_by_group = {gk: {} for gk in groups.keys()}  # group_key -> (year -> list[word])

    for file in sorted(files):
        year = file[:4]  # ファイル名先頭4桁を年とする（今の運用に合わせる）
        file_path = os.path.join(path, file)

        try:
            df = pd.read_csv(file_path, index_col=False, dtype="object")
            df = df.loc[:, ~df.columns.str.contains("^Unnamed:")]
        except Exception as e:
            print(f"[SKIP] 読み込み失敗: {file} ({e})")
            continue

        if df.empty:
            continue

        # 必須列
        required = ["statement", group_col]
        missing = [c for c in required if c not in df.columns]
        if missing:
            print(f"[SKIP] 必須列不足: {file} {missing}")
            continue

        # 年バケツ初期化
        bucket_all.setdefault(year, [])
        for gk in groups.keys():
            bucket_by_group[gk].setdefault(year, [])

        # statement単位で回す
        n_all = 0
        n_in_groups = {gk: 0 for gk in groups.keys()}

        for _, row in df.iterrows():
            st = row.get("statement", None)
            if st is None or (isinstance(st, float) and np.isnan(st)):
                continue

            text = re.sub(r"\s|　|\n|\r", "", str(st))
            if text == "":
                continue

            # 全体に入れる
            w = extract_words(text)
            if w:
                bucket_all[year].extend(w)
                n_all += 1

            # グループ判定して入れる
            gk = selector(row)
            if gk is not None:
                bucket_by_group[gk][year].extend(w)
                n_in_groups[gk] += 1

        print(f"[FILE] {file} year={year} all={n_all} " +
              " ".join([f"{groups[gk]}={n_in_groups[gk]}" for gk in groups.keys()]),
              flush=True)

    years = sorted(bucket_all.keys())
    docs_all = [" ".join(bucket_all[y]) for y in years]

    # 各グループ doc（年ごと）
    docs_groups = {}
    for gk in groups.keys():
        docs_groups[gk] = [" ".join(bucket_by_group[gk][y]) for y in years]

    # TF-IDF（全体 + 各グループ）
    all_x, all_idx, all_words = tfidf_fit_transform(docs_all)

    group_result = {}
    for gk in groups.keys():
        gx, gidx, gwords = tfidf_fit_transform(docs_groups[gk])
        group_result[gk] = (gx, gidx, gwords)

    # 出力：年×rank を縦、全体＋各グループを横
    # 例：年,rank,全体_word,全体_score,男_word,男_score,女_word,女_score...
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")

        header = ["年", "rank", "全体_word", "全体_tfidf"]
        for gk in groups.keys():
            header += [f"{groups[gk]}_word", f"{groups[gk]}_tfidf"]
        writer.writerow(header)

        for i, y in enumerate(years):
            for r in range(TOPN):
                row = [
                    y,
                    r + 1,
                    all_words[i][r], float(all_x[i][all_idx[i][r]])
                ]

                for gk in groups.keys():
                    gx, gidx, gwords = group_result[gk]
                    row += [gwords[i][r], float(gx[i][gidx[i][r]])]

                writer.writerow(row)

    print("finish:", output_file)


if __name__ == "__main__":
    main()
