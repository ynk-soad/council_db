from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import os
import time
import re
import requests

CITY_CODE = "37207"  # 東かがわ市のJISコード
BASE_URL = "https://www.city.higashikagawa.kagawa.dbsr.jp"
LIBRARY_URL = f"{BASE_URL}/index.php/1840633?Template=search-library"
DOWNLOAD_DIR = "/Users/ynkhiru09/Library/CloudStorage/OneDrive-KansaiUniversity/四国/香川県/higashikagawa"
YEARS = list(range(2019, 2025))[::-1]  # 2024→2019の降順処理

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

options = webdriver.ChromeOptions()
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

def click_element_with_text(tag, text):
    elements = driver.find_elements(By.TAG_NAME, tag)
    for el in elements:
        if text in el.text:
            el.click()
            return True
    return False

def extract_date(text):
    m = re.search(r"開催日：(\d{4})年(\d{2})月(\d{2})日", text)
    return f"{m.group(1)}{m.group(2)}{m.group(3)}" if m else "unknown"

def download_text():
    driver.get(LIBRARY_URL)

    for year in YEARS:
        print(f"\n📅 {year}年の処理を開始")
        click_element_with_text("a", f"{year}年")
        time.sleep(1)

        meetings = driver.find_elements(By.CSS_SELECTOR, "a[href*='Template=list']")
        meeting_urls = [
            m.get_attribute("href") for m in meetings
            if "Template=list" in m.get_attribute("href")
            and ("定例会" in m.text or "臨時会" in m.text)
        ]

        for m_url in meeting_urls:
            driver.get(m_url)
            time.sleep(1)

            doc_links = driver.find_elements(By.CSS_SELECTOR, "div.result-document")
            docs_by_date = {}

            for div in doc_links:
                link = div.find_element(By.TAG_NAME, "a")
                href = link.get_attribute("href")
                title = link.text
                date_text = div.text
                date_key = extract_date(date_text)

                if date_key not in docs_by_date:
                    docs_by_date[date_key] = {}
                if "名簿" in title:
                    docs_by_date[date_key]["meibo"] = href
                elif "本文" in title:
                    docs_by_date[date_key]["honbun"] = href

            for date, urls in docs_by_date.items():
                texts = []
                for kind in ["meibo", "honbun"]:
                    if kind not in urls:
                        continue
                    driver.get(urls[kind])
                    try:
                        try:
                            label = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "label[for='tab-all']")))
                            label.click()
                            time.sleep(0.5)
                        except:
                            print(f"⚠ {kind}：全文表示タブなし")

                        dl_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.tools__anchor")))
                        full_url = urljoin(BASE_URL, dl_btn.get_attribute("href"))

                        res = requests.get(full_url)
                        res.encoding = res.apparent_encoding
                        soup = BeautifulSoup(res.text, "html.parser")

                        # 本文テキスト抽出（発言行）
                        voices = soup.select("p.print-text__voice")
                        text_content = "\n".join(v.get_text(strip=True) for v in voices)

                        if not text_content.strip():
                            raise Exception("テキスト抽出失敗または空")

                        texts.append(text_content)

                    except Exception as e:
                        print(f"⚠ {kind} エラー: {e}")

                if texts:
                    save_name = f"{date}{CITY_CODE}.txt"
                    save_path = os.path.join(DOWNLOAD_DIR, save_name)
                    with open(save_path, "w", encoding="utf-8") as f:
                        f.write("\n\n".join(texts))
                    print(f"✅ 保存完了: {save_path}")

    driver.quit()

if __name__ == "__main__":
    download_text()
