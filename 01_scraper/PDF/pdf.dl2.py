import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# 設定
BASE_URL = "https://www.city.mima.lg.jp"
LIST_PAGE = BASE_URL + "/gyosei/shisei/gikai/kaigiroku/"
SAVE_DIR = "/Users/ynkhiru09/Library/CloudStorage/OneDrive-KansaiUniversity/四国/徳島県/mima"
JIS_CODE = "36207"
os.makedirs(SAVE_DIR, exist_ok=True)

# 和暦→西暦変換
def convert_japanese_date(text):
    match = re.search(r'(令和|平成)(元|\d+)年(?:第\d+回)?(?:定例会|臨時会)?.*?(\d{1,2})月(\d{1,2})日', text)
    if not match:
        return None
    era, year_str, month, day = match.groups()
    base_year = 2018 if era == '令和' else 1988
    year = base_year + (1 if year_str == '元' else int(year_str))
    return f"{year}{int(month):02}{int(day):02}"

# 年別ページリンク取得
res = requests.get(LIST_PAGE)
soup = BeautifulSoup(res.text, "html.parser")
year_links = soup.select("article header h2 a")

for link in year_links:
    href = link.get("href")
    year_page_url = urljoin(BASE_URL, href)
    print(f"📄 年別ページ: {year_page_url}")

    res_year = requests.get(year_page_url)
    res_year.encoding = res_year.apparent_encoding  
    soup_year = BeautifulSoup(res_year.text, "html.parser")

    for a in soup_year.find_all("a", href=True):
        if ".pdf" in a["href"].lower():
            pdf_url = urljoin(BASE_URL, a["href"])
            text = a.text.strip()
            date_str = convert_japanese_date(text)
            if date_str:
                year = int(date_str[:4])
                if year < 2011:
                    print(f"⏭ {text} は {year} 年なのでスキップ")
                    continue
                filename = f"{date_str}{JIS_CODE}.pdf"
            else:
                print(f"⚠ 日付変換失敗: {text}")
                continue

            save_path = os.path.join(SAVE_DIR, filename)
            print(f"⬇ {filename} を保存中...")

            try:
                pdf_res = requests.get(pdf_url)
                with open(save_path, "wb") as f:
                    f.write(pdf_res.content)
            except Exception as e:
                print(f"❌ ダウンロード失敗: {pdf_url} ({e})")

print("✅ 全PDFのダウンロードが完了しました。")
