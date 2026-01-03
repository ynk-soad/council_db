import os
import re
import csv
import MeCab
import numpy as np
import pandas as pd

from gensim import corpora
from gensim.models import LdaModel

# ==========================================================
# ★★★ ここだけ触ればOK ★★★
# ==========================================================
path = "/workspaces/council_db/data/kagoshima"

# mode:
#   "all"    : 全体（年ごとにtopic平均）
#   "gender" : 男女比較（年ごとに male/female を横並び）
#   "kaiha"  : 会派比較（年ごとに 会派ごと を横並び）
#   "term"   : 任期比較（年ごとに before/after を横並び）
#   "age"    : 年齢比較（年ごとに 年齢階級 を横並び）
mode = "gender"   # "all" / "gender" / "kaiha" / "term" / "age"

K = 5                  # トピック数
TOP_WORDS = 15         # 各トピックの上位語数
MIN_TOKEN_LEN = 2      # 1文字語のノイズを落とすなら2

# --- kaiha 設定（mode="kaiha" の時だけ使用） ---
kaiha_include_regex = None      # 例: r"自民|公明"
kaiha_exclude_regex = None      # 例: r"維新|無所属"

# --- term 設定（mode="term" の時だけ使用） ---
term_split_year = 2014
term_before_label = "before"
term_after_label = "after"

# --- age 設定（mode="age" の時だけ使用） ---
age_bins = [0, 40, 50, 60, 200]
age_labels = ["u39", "40s", "50s", "60p"]
# ==========================================================

# ==========================================================
# 出力ファイル名（modeから自動生成）
# ==========================================================
out_topics = os.path.join(path, f"lda_topics_{mode}.csv")
out_doc_topic = os.path.join(path, f"lda_doc_topic_{mode}.csv")

# ==========================================================
# ストップワード（必要に応じて増やしてOK）
# ==========================================================
stop_words = [
    "僕","部","課","だれ","すべて","室","ページ","id","平成","令和","昭和","年度",
    "年","月","日","期","点","か所","か月","本市","本県","本町","本会","当局",
    "当該","関係","事項","議員","委員","市長","局長","部長","課長","答弁","質疑",
    "質問","要望","報告","陛下","国旗","元号","表決","散会","起立","会期","開会",
    "議会","異議","会議","拍手","日程","登壇","個人","午後","議長","議事",
     "閉会","休憩","再開","採決","賛成","反対","動議","こと", "もの", "ところ", "ため", 
    "以上","今回", "今後", "本日", "自ら","なし", "等", "ほか", "それ", "これ",
]


KANJI_NUM_RE = re.compile(r'^[0-9一二三四五六七八九十百千万億兆]+$')

# ==========================================================
# MeCab Tagger（1回だけ）
# ==========================================================
try:
    import unidic_lite
    mecab = MeCab.Tagger(f"-d {unidic_lite.DICDIR}")
    mecab.parse("")
except Exception:
    mecab = MeCab.Tagger()
    mecab.parse("")


def extract_words(text):
    """
    名詞のみ、数・漢数字・ストップワード除外。人名も除外。
    固有名詞も除外。英字のみ/記号混じりも除外。
    """
    words = []
    node = mecab.parseToNode(text)

    while node:
        if node.feature.startswith("名詞"):
            if "人名" in node.feature:
                node = node.next
                continue

            if "固有名詞" in node.feature:
                node = node.next
                continue

            surf = node.surface

            if surf not in stop_words:
                if node.feature.split(",")[1] != "数":
                    if not KANJI_NUM_RE.fullmatch(surf):
                        if re.fullmatch(r"[A-Za-zＡ-Ｚａ-ｚ]+", surf):
                            node = node.next
                            continue
                        if re.search(r"[^\w一-龥ぁ-んァ-ン]", surf):
                            node = node.next
                            continue
                        if len(surf) >= MIN_TOKEN_LEN:
                            words.append(surf)

        node = node.next

    return words


def _read_csvs():
    files = [f for f in os.listdir(path) if f.endswith(".csv")]
    if not files:
        raise ValueError("CSVが見つからない: " + path)
    return sorted(files)


def _read_df(fp):
    try:
        df = pd.read_csv(fp, dtype="object")
        df = df.loc[:, ~df.columns.str.contains("^Unnamed:")]
        return df
    except Exception:
        return None


def _year_from_file(file_name):
    # ファイル名先頭4桁を年として使う前提
    return file_name[:4]


def _normalize_gender(gd):
    if gd == "男":
        return "male"
    if gd == "女":
        return "female"
    return None


def _bin_age(ag):
    if ag is None or (isinstance(ag, float) and np.isnan(ag)):
        return None
    try:
        agi = int(float(ag))
    except Exception:
        return None

    for i in range(len(age_bins) - 1):
        if age_bins[i] <= agi < age_bins[i + 1]:
            return age_labels[i]
    return None


def load_statement_docs():
    """
    発言1件=1doc として tokens を作り、メタ（year, gender, kaiha, age_label, term_label）も付与
    returns: DataFrame with columns:
      year, tokens, gender, kaiha, age_label, term_label
    """
    rows = []
    for file in _read_csvs():
        year = _year_from_file(file)
        fp = os.path.join(path, file)
        df = _read_df(fp)
        if df is None or df.empty or "statement" not in df.columns:
            continue

        for _, r in df.iterrows():
            st = r.get("statement", None)
            if st is None or (isinstance(st, float) and np.isnan(st)):
                continue

            text = re.sub(r"\s|　|\n|\r", "", str(st))
            if text == "":
                continue

            tokens = extract_words(text)
            if not tokens:
                continue

            gd = _normalize_gender(str(r.get("gender", ""))) if "gender" in df.columns else None
            kh = str(r.get("kaiha", "")) if "kaiha" in df.columns else None
            if kh in ("", "nan", "None"):
                kh = None

            ag_label = _bin_age(r.get("age", None)) if "age" in df.columns else None

            try:
                yi = int(year)
                term_label = term_before_label if yi <= term_split_year else term_after_label
            except Exception:
                term_label = None

            rows.append({
                "year": year,
                "tokens": tokens,
                "gender": gd,
                "kaiha": kh,
                "age_label": ag_label,
                "term_label": term_label
            })

    if not rows:
        raise ValueError("有効な発言が読み込めませんでした（statement列/内容を確認）")

    return pd.DataFrame(rows)


def fit_lda(docs_tokens):
    """
    docs_tokens: list[list[str]]
    returns: (lda, dictionary, corpus)
    """
    dictionary = corpora.Dictionary(docs_tokens)
    dictionary.filter_extremes(no_below=2, no_above=0.8)
    corpus = [dictionary.doc2bow(doc) for doc in docs_tokens]

    lda = LdaModel(
        corpus=corpus,
        id2word=dictionary,
        num_topics=K,
        random_state=0,
        passes=10,
        alpha="auto",
        eta="auto"
    )
    return lda, dictionary, corpus


def write_topics(lda, label):
    with open(out_topics, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        for topic_id in range(K):
            terms = lda.show_topic(topic_id, topn=TOP_WORDS)
            for rank, (term, prob) in enumerate(terms, start=1):
                w.writerow([label, topic_id, rank, term, float(prob)])


def infer_doc_topics(lda, corpus):
    """
    returns: list[list[float]]  (len=docs, each len=K)
    """
    out = []
    for bow in corpus:
        dist = lda.get_document_topics(bow, minimum_probability=0.0)
        vec = [0.0] * K
        for tid, p in dist:
            vec[int(tid)] = float(p)
        out.append(vec)
    return out


def pivot_year_group(df_with_topics, group_col, group_order=None):
    """
    df_with_topics columns: year, group_col, topic_0..topic_{K-1}
    年×グループでtopic平均を取り、横持ちにする
    """
    if group_order is None:
        group_order = sorted([g for g in df_with_topics[group_col].dropna().unique().tolist()])

    # 平均
    g = df_with_topics.dropna(subset=[group_col]).groupby(["year", group_col], as_index=False).mean(numeric_only=True)

    # ワイド化
    years = sorted(g["year"].unique().tolist())
    wide = pd.DataFrame({"year": years})

    for grp in group_order:
        sub = g[g[group_col] == grp].set_index("year")
        for i in range(K):
            col = f"{grp}_topic_{i}"
            wide[col] = [float(sub.loc[y, f"topic_{i}"]) if y in sub.index else 0.0 for y in years]

    return wide, group_order


def write_doc_topic_all(df_topics):
    # 年×topic平均（横並びはyear, topic_0..）
    g = df_topics.groupby("year", as_index=False).mean(numeric_only=True)
    g = g.sort_values("year")

    with open(out_doc_topic, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        header = ["year"] + [f"topic_{i}" for i in range(K)]
        if f.tell() == 0:
            w.writerow(header)

        for _, r in g.iterrows():
            row = [r["year"]] + [float(r[f"topic_{i}"]) for i in range(K)]
            w.writerow(row)


def write_doc_topic_group_wide(wide_df, group_order):
    with open(out_doc_topic, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")

        header = ["year"]
        for grp in group_order:
            header += [f"{grp}_topic_{i}" for i in range(K)]

        if f.tell() == 0:
            w.writerow(header)

        for _, r in wide_df.iterrows():
            row = [r["year"]]
            for grp in group_order:
                for i in range(K):
                    row.append(float(r[f"{grp}_topic_{i}"]))
            w.writerow(row)


def main():
    # 出力を毎回作り直す（消せないときは警告だけ出して続行）
    for p in (out_topics, out_doc_topic):
        try:
            if os.path.exists(p):
                os.remove(p)
        except PermissionError:
            print(f"[WARN] 削除できませんでした: {p}")

    df = load_statement_docs()

    # modeごとに必要なdocだけ残す（比較に必要なメタが無いものは落ちる）
    if mode == "gender":
        df2 = df.dropna(subset=["gender"]).copy()
        group_col = "gender"
        group_order = ["male", "female"]

    elif mode == "kaiha":
        df2 = df.dropna(subset=["kaiha"]).copy()
        if kaiha_exclude_regex:
            df2 = df2[~df2["kaiha"].astype(str).str.contains(kaiha_exclude_regex, regex=True, na=False)]
        if kaiha_include_regex:
            df2 = df2[df2["kaiha"].astype(str).str.contains(kaiha_include_regex, regex=True, na=False)]
        group_col = "kaiha"
        group_order = None  # 自動

    elif mode == "age":
        df2 = df.dropna(subset=["age_label"]).copy()
        group_col = "age_label"
        group_order = age_labels[:]  # 定義順で固定

    elif mode == "term":
        df2 = df.dropna(subset=["term_label"]).copy()
        group_col = "term_label"
        group_order = [term_before_label, term_after_label]

    elif mode == "all":
        df2 = df.copy()
        group_col = None
        group_order = None

    else:
        raise ValueError("modeが不正です")

    if df2.empty:
        raise ValueError(f"mode={mode} で有効データが0件（必要列が無い/全て欠損の可能性）")

    docs_tokens = df2["tokens"].tolist()
    lda, dictionary, corpus = fit_lda(docs_tokens)

    # topics出力
    write_topics(lda, mode)

    # docごとのtopic分布を付与
    vecs = infer_doc_topics(lda, corpus)
    for i in range(K):
        df2[f"topic_{i}"] = [v[i] for v in vecs]

    # doc_topic出力（年で集計して横並び）
    if mode == "all":
        write_doc_topic_all(df2)
    else:
        wide, order = pivot_year_group(df2, group_col, group_order=group_order)
        write_doc_topic_group_wide(wide, order)

    print("finish")
    print("topics:", out_topics)
    print("doc_topic:", out_doc_topic)


if __name__ == "__main__":
    main()
