from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os
import time
import re
import requests
from datetime import datetime

# 保存先
DOWNLOAD_FOLDER = "/Users/ynkhiru09/Library/CloudStorage/OneDrive-KansaiUniversity/四国/徳島県/awa"
JIS_CODE = "36206"  # 阿波市の市町村コード
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# 和暦変換関数（令和・平成対応）
def convert_japanese_date(text):
    match = re.search(r'(令和|平成)(元|\d+)年第\d+回.*?(\d{1,2})月(\d{1,2})日', text)
    if match:
        era, year_part, month, day = match.groups()
        if era == '令和':
            base = 2018
        elif era == '平成':
            base = 1988
        else:
            return None
        year = base + (1 if year_part == '元' else int(year_part))
        try:
            return f"{year}{int(month):02}{int(day):02}"
        except ValueError:
            return None
    return None

# セットアップ
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver.get("https://www.city.awa.lg.jp/gikai/category/zokusei/kaigiroku/")
time.sleep(2)

# 会議録ページの全リンク取得
links = driver.find_elements(By.PARTIAL_LINK_TEXT, "会議録")
urls = [a.get_attribute("href") for a in links if a.get_attribute("href")]

visited = set()
for link in urls:
    if link in visited:
        continue
    visited.add(link)

    driver.execute_script("window.open(arguments[0])", link)
    driver.switch_to.window(driver.window_handles[1])
    time.sleep(2)

    pdf_links = driver.find_elements(By.CSS_SELECTOR, "a[href$='.pdf']")
    for pdf_a in pdf_links:
        href = pdf_a.get_attribute("href")
        text = pdf_a.text.strip()
        date_str = convert_japanese_date(text)
        if href and date_str:
            filename = f"{date_str}{JIS_CODE}.pdf"
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            print(f"⬇ {filename} をダウンロード中...")

            try:
                response = requests.get(href)
                with open(filepath, "wb") as f:
                    f.write(response.content)
            except Exception as e:
                print(f"❌ ダウンロード失敗: {href} ({e})")

    driver.close()
    driver.switch_to.window(driver.window_handles[0])
    time.sleep(1)

driver.quit()
print("✅ すべてのPDFのダウンロードが完了しました。")
