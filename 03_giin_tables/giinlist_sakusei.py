import requests
from bs4 import BeautifulSoup
import pandas as pd
import concurrent.futures
import re
import certifi
import json
import os

# **基本設定**
JSON_FILE = "/Users/ynkhiru09/Desktop/プログラム/テーブル作成集/jiscode.json"
folder_path = "/Users/ynkhiru09/Downloads/fukutsu"
BASE_URL = "https://go2senkyo.com"#ここは変えない
ELECTION_LIST_URL = "https://go2senkyo.com/local/jichitai/3363"
city_name = os.path.basename(folder_path)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


with open(JSON_FILE, "r", encoding="utf-8") as f:
    city_data = json.load(f)

JIS_CODE, city_name_jp = None, None
for romaji, values in city_data.items():
    if romaji == city_name:
        JIS_CODE = values[0]
        city_name_jp = values[1]
        break

if JIS_CODE is None or city_name_jp is None:
    raise ValueError(f"⚠ 市町村名 '{city_name}' が {JSON_FILE} に存在しません。")

city_name, city_romaji = None, None
for romaji, values in city_data.items():
    if values[0] == JIS_CODE:
        city_name = values[1]
        city_romaji = romaji
        break

if city_name is None or city_romaji is None:
    raise ValueError(f"JISコード {JIS_CODE} が {JSON_FILE} に存在しません。")

# **出力ファイルの設定**
OUTPUT_FILE = os.path.join(folder_path, f"{city_romaji}_giinlist.csv")

giin_data = []
shicho_data = []

# **共通のカラム**
COLUMNS = [
    "市議選日", "giin_id", "city_name", "name", "kana", "age", "gender", "title",
    "new_and_old", "party", "kaiha", "gicho", "gicho_sub", "kansa", "shicho_or_giin"
]
PARTY_MAPPING = {
    "無所属": "無",
    "日本共産党": "共",
    "共産党": "共",
    "公明党": "公",
    "自民党": "自",
    "自由民主党":"自",
    "民主党":"民",
    "立憲民主党": "立",
    "国民民主党": "国",
    "社民党": "社",
    "社会民主党": "社",
    "日本維新の会": "維",
    "大阪維新の会" :"維",
    "維新の会": "維",
    "れいわ新選組": "れ",
    "日本第一党": "一",
    "NHK党": "N",
    "幸福実現党": "幸",
    "新党大地": "大",
    "日本のこころ": "こ",
    "諸派": "諸",
    "新社会党":"新",
    "その他": "他"

}

# **title を補完する処理**
def fill_missing_titles():
    title_dict = {}

    for row in giin_data:
        name = row["name"]
        title = row["title"]

        # **title が空でない場合は辞書に登録**
        if title != "N/A" and title != "":
            title_dict[name] = title

    # **辞書を利用して title を補完**
    for row in giin_data:
        if row["title"] == "N/A" or row["title"] == "":
            if row["name"] in title_dict:
                row["title"] = title_dict[row["name"]]

# **選挙一覧ページからリンクを取得**
def get_election_links(election_type):
    response = requests.get(ELECTION_LIST_URL, headers=HEADERS, verify=certifi.where())
    if response.status_code != 200:
        print(f"エラー: 選挙一覧ページの取得に失敗しました（{response.status_code}）")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    election_links = []

    for row in soup.select("table.m_table tbody tr"):
        date_tag = row.select_one("td:first-child")
        election_date = date_tag.text.strip().replace("/", "") if date_tag else None

        if election_date == "未定":
            continue  # 未定の選挙はスキップ

        try:
            election_year = int(election_date[:4])
        except ValueError:
            continue  # 日付が不正な場合スキップ

        link_tag = row.select_one("td.left a")
        if link_tag:
            title = link_tag.text.strip()
            is_hoketsu = "補欠" in title  # ← ここでフラグ化！
            if election_type in title or is_hoketsu:
                link = BASE_URL + link_tag["href"] if not link_tag["href"].startswith("http") else link_tag["href"]
                if 2007 <= election_year <= 2024:
                    election_links.append((election_date, link, is_hoketsu))  # ← フラグを渡す

    return election_links

# **データ取得関数（補欠選を識別して giin_id を分けるように修正）**
def get_elected_data(election_date, election_url, is_mayor, is_hoketsu=False):
    response = requests.get(election_url, headers=HEADERS, verify=certifi.where())
    soup = BeautifulSoup(response.text, "html.parser")

    # 当選者数を取得
    total_winners = None
    winners_tag = soup.select_one("th.middle:-soup-contains('定数/候補者数') + td")
    if winners_tag:
        match = re.search(r"(\d+)\s*/\s*\d+", winners_tag.text.strip())
        if match:
            total_winners = int(match.group(1))

    candidates = soup.select("section.m_senkyo_result_data")
    if total_winners:
        candidates = candidates[:total_winners]

    if not candidates:
        return

    if is_mayor:
        candidates = candidates[:1]  # 市長選挙は1名だけ

    # 補欠：rank=501から、通常：rank=1から
    base_rank = 0 if is_mayor else (501 if is_hoketsu else 1)

    def process_candidate(candidate, idx):
        rank = base_rank + idx
        name_tag = candidate.select_one("h2.m_senkyo_result_data_ttl a")
        kana_tag = candidate.select_one("span.m_senkyo_result_data_kana")
        name_kanji = re.sub(r"\s+", "", name_tag.text.strip()) if name_tag else "N/A"
        kana = re.sub(r"\s+", "", kana_tag.text.strip()) if kana_tag else "N/A"
        name_kanji = re.sub(r"[ァ-ンー]", "", name_kanji)

        age_gender_tag = candidate.select_one("div.m_senkyo_result_data_bottom_right p span")
        age, gender = "", "N/A"
        if age_gender_tag:
            text = age_gender_tag.text.strip()
            age_match = re.search(r"(\d+)歳", text)
            if age_match:
                age = age_match.group(1)
            gender = "男" if "男" in text else "女" if "女" in text else "N/A"

        new_and_old_tag = candidate.select_one("div.m_senkyo_result_data_bottom_right p span:nth-of-type(2)")
        new_and_old = "N/A"
        if new_and_old_tag:
            new_and_old_text = new_and_old_tag.text.strip()
            if "現職" in new_and_old_text:
                new_and_old = "現"
            elif "新人" in new_and_old_text:
                new_and_old = "新"
            elif "元職" in new_and_old_text:
                new_and_old = "元"

        title_tag = candidate.select_one("div.m_senkyo_result_data_bottom_right p.m_senkyo_result_data_para.small")
        title = title_tag.text.strip() if title_tag else "N/A"

        party_tag = candidate.select_one("div.m_senkyo_result_data_bottom_left p.m_senkyo_result_data_circle")
        party = party_tag.text.strip() if party_tag and party_tag.text.strip() else "無"
        party = PARTY_MAPPING.get(party, party)

        giin_id = f"{election_date}{JIS_CODE}{str(rank).zfill(3)}"

        return {
            "市議選日": election_date,
            "giin_id": giin_id,
            "city_name": city_name,
            "name": name_kanji,
            "kana": kana,
            "age": age,
            "gender": gender,
            "title": title,
            "new_and_old": new_and_old,
            "party": party,
            "kaiha": "",
            "gicho": "",
            "gicho_sub": "",
            "kansa": "",
            "shicho_or_giin": "1" if is_mayor else "0"
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(process_candidate, candidates, range(len(candidates))))

    if is_mayor:
        shicho_data.extend(results)
    else:
        giin_data.extend(results)


def fill_name_by_kana_reference(data_list):
    """
    giin_data または shicho_data に対して
    kanaが一致する場合、フル漢字表記のnameに統一する
    """
    kana_to_kanji_name = {}

    # 1. まず「フル漢字のname」を持つものを辞書に登録
    for row in data_list:
        kana = row["kana"]
        name = row["name"]
        if kana and name:
            # nameが漢字のみなら登録
            if re.fullmatch(r"[一-龥々〆〤\s　]*", name):
                kana_to_kanji_name[kana] = name

    # 2. 補完処理
    for row in data_list:
        kana = row["kana"]
        if kana in kana_to_kanji_name:
            correct_name = kana_to_kanji_name[kana]
            if row["name"] != correct_name:
                row["name"] = correct_name


# **メイン処理**
def main():
    giin_links = get_election_links("市議会議員選挙")
    shicho_links = get_election_links("市長選挙")

    # **市議会議員データ取得**
    for election_date, election_url, is_hoketsu in giin_links:
        get_elected_data(election_date, election_url, is_mayor=False, is_hoketsu=is_hoketsu)

    # **市長データ取得**
    for election_date, election_url, is_hoketsu in shicho_links:
        get_elected_data(election_date, election_url, is_mayor=True, is_hoketsu=is_hoketsu)

    # **title 補完処理を実行**
    fill_missing_titles()
    fill_name_by_kana_reference(giin_data)
    fill_name_by_kana_reference(shicho_data)

    # **議員データは選挙ごとに1行空ける**
    final_giin_data = []
    prev_date = None
    for row in sorted(giin_data, key=lambda x: x["市議選日"], reverse=True):
        if prev_date and prev_date != row["市議選日"]:
            final_giin_data.append({col: "" for col in COLUMNS})
        final_giin_data.append(row)
        prev_date = row["市議選日"]

    # **市長データの前に1行空け、時系列順（降順）にソート**
    all_data = final_giin_data + [{"市議選日": "", **{col: "" for col in COLUMNS[1:]}}] + sorted(shicho_data, key=lambda x: x["市議選日"], reverse=True)

    # **CSV保存**
    df = pd.DataFrame(all_data, columns=COLUMNS)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"データをCSVに保存しました: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()