import os, re
import numpy as np
import pandas as pd
import MeCab

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score, normalized_mutual_info_score

# =========================
# ここだけ触ればOK
# =========================
DATA_DIR = "/workspaces/council_db/data/kagoshima"   # 議事録CSVフォルダ
OUT_DIR  = "/workspaces/council_db/data/kagoshima"   # 出力先

SPEAKER_COL = "speaker"      # 議員名
TEXT_COL    = "statement"    # 本文
KAIHA_COL   = "kaiha"        # 会派（比較用）

# ---- 年で絞る（Noneなら絞らない）----
YEAR_MIN = 2018
YEAR_MAX = 2018

# クラスタ数
N_CLUSTERS = 7

# 特徴語出力の上位
TOP_TERMS = 30

# 会派の前処理（無所属などを除外したい時）
KAIHA_INCLUDE_REGEX = None   # 例: r"自民|公明|立憲"
KAIHA_EXCLUDE_REGEX = None   # 例: r"無所属"

# TF-IDFの閾値（一般語が強いときは max_df を下げると効く）
MIN_DF = 2
MAX_DF = 0.5

# こと/もの/ところ系を落とす：ここは増やしてOK
STOP_WORDS = set([
    "こと","もの","ところ","ため","それ","これ","あれ","こちら","よう","ほう","たち","等","など",
    "今回","今後","現在","状況","以上","必要","対応","検討","実施","利用","推進","課題","取組","取り組み",
    "議会","議員","委員","市長","局長","部長","課長","答弁","質疑","質問",
    "ページ","資料","案件","議案","日程","登壇","拍手","異議","終了",
    "平成","令和","昭和","年度","年","月","日","期","点"
])
MIN_TOKEN_LEN = 2
# =========================

KANJI_NUM_RE = re.compile(r'^[0-9一二三四五六七八九十百千万億兆]+$')
YEAR_IN_FILENAME_RE = re.compile(r"^(19|20)\d{2}")

# MeCab
try:
    import unidic_lite
    mecab = MeCab.Tagger(f"-d {unidic_lite.DICDIR}")
    mecab.parse("")
except Exception:
    mecab = MeCab.Tagger()
    mecab.parse("")

def extract_year_from_filename(fn: str):
    m = YEAR_IN_FILENAME_RE.match(fn)
    if not m:
        return None
    try:
        return int(fn[:4])
    except Exception:
        return None

def tokenize(text: str):
    if text is None:
        return []
    text = re.sub(r"\s|　|\n|\r", "", str(text))
    if text == "":
        return []

    out = []
    node = mecab.parseToNode(text)
    while node:
        if node.feature.startswith("名詞"):
            # 人名・固有名詞を落とす
            if "人名" in node.feature or "固有名詞" in node.feature:
                node = node.next
                continue

            w = node.surface

            # 数詞・漢数字
            feats = node.feature.split(",")
            if len(feats) > 1 and feats[1] == "数":
                node = node.next
                continue
            if KANJI_NUM_RE.fullmatch(w):
                node = node.next
                continue

            # 英字のみ
            if re.fullmatch(r"[A-Za-zＡ-Ｚａ-ｚ]+", w):
                node = node.next
                continue

            # 記号混じり
            if re.search(r"[^\w一-龥ぁ-んァ-ン]", w):
                node = node.next
                continue

            # ストップワード
            if len(w) >= MIN_TOKEN_LEN and (w not in STOP_WORDS):
                out.append(w)

        node = node.next

    return out

def read_csvs(folder):
    files = sorted([f for f in os.listdir(folder) if f.endswith(".csv")])
    if not files:
        raise ValueError("CSVが見つかりません: " + folder)

    dfs = []
    for f in files:
        # 年で絞る（ファイル先頭4桁想定）
        y = extract_year_from_filename(f)
        if y is not None and YEAR_MIN is not None and y < YEAR_MIN:
            continue
        if y is not None and YEAR_MAX is not None and y > YEAR_MAX:
            continue

        fp = os.path.join(folder, f)
        try:
            df = pd.read_csv(fp, dtype="object")
            df = df.loc[:, ~df.columns.str.contains("^Unnamed:")]
        except Exception:
            continue

        need = {SPEAKER_COL, TEXT_COL, KAIHA_COL}
        if not need.issubset(set(df.columns)):
            continue

        df = df[[SPEAKER_COL, TEXT_COL, KAIHA_COL]].copy()
        if y is not None:
            df["year"] = y
        dfs.append(df)

    if not dfs:
        raise ValueError("条件に合うCSVがありません（年範囲や列名を確認）")

    return pd.concat(dfs, ignore_index=True)

def mode_or_first(s):
    s = s.dropna()
    if len(s) == 0:
        return ""
    return s.value_counts().idxmax()

def make_cluster_table(g, n_clusters):
    """
    スクショみたいに「cluster_0..cluster_{k-1}」の列に
    議員名（会派）を縦に並べる表を作る
    """
    cols = {}
    for cid in range(n_clusters):
        sub = g[g["cluster_id"] == cid].copy()
        sub = sub.sort_values(["kaiha", "speaker"])
        # 表示を「氏名（会派）」にする（いらなければ speaker のみに）
        cols[f"cluster_{cid}"] = (sub["speaker"] + "（" + sub["kaiha"].astype(str) + "）").tolist()

    maxlen = max((len(v) for v in cols.values()), default=0)
    out = {}
    for k, v in cols.items():
        out[k] = v + [""] * (maxlen - len(v))
    return pd.DataFrame(out)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    df = read_csvs(DATA_DIR)

    # 会派フィルタ
    df[KAIHA_COL] = df[KAIHA_COL].astype(str)
    if KAIHA_EXCLUDE_REGEX:
        df = df[~df[KAIHA_COL].str.contains(KAIHA_EXCLUDE_REGEX, regex=True, na=False)]
    if KAIHA_INCLUDE_REGEX:
        df = df[df[KAIHA_COL].str.contains(KAIHA_INCLUDE_REGEX, regex=True, na=False)]

    # 議員単位に結合（複数年まとめるなら speaker の粒度に注意）
    g = df.groupby(SPEAKER_COL).agg(
        text=(TEXT_COL, lambda x: " ".join(map(str, x))),
        kaiha=(KAIHA_COL, mode_or_first)
    ).reset_index().rename(columns={SPEAKER_COL: "speaker"})

    # 年範囲文字列（出力名用）
    yr = "all"
    if YEAR_MIN is not None or YEAR_MAX is not None:
        y1 = YEAR_MIN if YEAR_MIN is not None else "min"
        y2 = YEAR_MAX if YEAR_MAX is not None else "max"
        yr = f"{y1}-{y2}"

    # TF-IDF
    vec = TfidfVectorizer(
        tokenizer=tokenize,
        token_pattern=None,
        min_df=MIN_DF,
        max_df=MAX_DF
    )
    X = vec.fit_transform(g["text"])

    # KMeans
    km = KMeans(n_clusters=N_CLUSTERS, random_state=0, n_init=20)
    g["cluster_id"] = km.fit_predict(X)

    # 出力1：議員→クラスタ＋会派
    out_assign = os.path.join(OUT_DIR, f"giin_cluster_assign_{yr}_k{N_CLUSTERS}.csv")
    g[["speaker", "kaiha", "cluster_id"]].to_csv(out_assign, index=False, encoding="utf-8-sig")

    # 出力2：会派×クラスタ（人数）
    ct = pd.crosstab(g["kaiha"], g["cluster_id"])
    out_ct = os.path.join(OUT_DIR, f"kaiha_x_cluster_crosstab_{yr}.csv")
    ct.to_csv(out_ct, encoding="utf-8-sig")

    # 出力3：会派×クラスタ（構成比）
    ratio = ct.div(ct.sum(axis=1), axis=0).fillna(0)
    out_ratio = os.path.join(OUT_DIR, f"kaiha_x_cluster_ratio_{yr}.csv")
    ratio.to_csv(out_ratio, encoding="utf-8-sig")

    # 出力4：クラスタ特徴語
    terms = np.array(vec.get_feature_names_out())
    centers = km.cluster_centers_
    rows = []
    for cid in range(N_CLUSTERS):
        top_idx = np.argsort(centers[cid])[::-1][:TOP_TERMS]
        for r, idx in enumerate(top_idx, start=1):
            rows.append([cid, r, terms[idx], float(centers[cid, idx])])

    out_terms = os.path.join(OUT_DIR, f"cluster_top_terms_{yr}_k{N_CLUSTERS}.csv")
    pd.DataFrame(rows, columns=["cluster_id", "rank", "term", "weight"]).to_csv(
        out_terms, index=False, encoding="utf-8-sig"
    )

    # 出力5：スクショ形式の表
    cluster_table = make_cluster_table(g, N_CLUSTERS)
    out_table = os.path.join(OUT_DIR, f"cluster_giin_table_{yr}_k{N_CLUSTERS}.csv")
    cluster_table.to_csv(out_table, index=False, encoding="utf-8-sig")

    # 指標
    sil = None
    if N_CLUSTERS >= 2 and X.shape[0] > N_CLUSTERS:
        sil = silhouette_score(X, g["cluster_id"], metric="cosine")

    valid = g["kaiha"].astype(str).str.strip() != ""
    ari = adjusted_rand_score(g.loc[valid, "kaiha"], g.loc[valid, "cluster_id"])
    nmi = normalized_mutual_info_score(g.loc[valid, "kaiha"], g.loc[valid, "cluster_id"])

    out_score = os.path.join(OUT_DIR, f"scores_{yr}_k{N_CLUSTERS}.txt")
    with open(out_score, "w", encoding="utf-8") as f:
        f.write("\n".join([
            f"year_range={yr}",
            f"n_speakers={len(g)}",
            f"n_features={X.shape[1]}",
            f"K={N_CLUSTERS}",
            f"silhouette_cosine={sil}",
            f"ARI(kaiha vs cluster)={ari}",
            f"NMI(kaiha vs cluster)={nmi}",
        ]))

    print("[OK] assign:", out_assign)
    print("[OK] crosstab:", out_ct)
    print("[OK] ratio:", out_ratio)
    print("[OK] top_terms:", out_terms)
    print("[OK] table:", out_table)
    print("[OK] scores:", out_score)

if __name__ == "__main__":
    main()
