Council DB – Japanese Local Assembly Minutes Pipeline

地方議会の議事録（会議録）を自動収集・整形・構造化し、
定例会テーブル・会議テーブル・議員マスタ・発言テーブル・Q&A 生成までを
一気通貫で処理する ETL + NLP パイプライン です。

研究目的としては、全国の地方議会の議事録をデータベース化し、
将来的に RAG（Retrieval-Augmented Generation）議会検索システム を実現することを目指しています。

 Features
1. 議事録スクレイピング（Scraper）

discuss.net 対応（複数バージョン）

PDF / HTML / TXT の自動取得

市ごとの専用 scraper（大阪市・東かがわ市・鳥栖市など）

PDF ダウンロード・ファイル名の正規化

2. PDF → TXT 変換（Preprocess）

PDF のテキスト化

UTF-8 への文字コード統一

不要な空白・改行のクリーニング処理

3. 定例会・会議テーブル生成（Meeting Tables）

TXT / HTML から定例会情報を抽出

会議 ID、日程、回次などの構造化

自治体ごとの書式差異に対応

4. 議員テーブル生成（Giin Tables）

go2senkyo.com から議員情報をスクレイピング

年度別議員リスト（補選対応）

議長・副議長・監査委員の自動抽出

giin_year → giin_sakusei による統合マスタ生成

5. 発言テーブル生成（Speech Extraction）

発言者・肩書き・本文の抽出

○議員 / ◎市長 / ◆部長 など記号にも対応

HTML議事録向けロジック（大阪市）

例外処理（hatsugen_reigai）

6. Q&A ペア生成（RAG 用）

発言から質問・回答を自動生成

1発言から最大3文以内に要約

GPT モデルを用いた整形

RAG 検索向け学習データを生成

 Folder Structure
council_db/
├─ 01_scraper/                # 議事録スクレイピング
│  ├─ osaka/                  # 大阪市専用 scraper
│  ├─ discuss3.py
│  ├─ pdf_dl.py
│  ├─ pdf_txt.py
│  ├─ higashikagawa.py
│  ├─ tosu.py
│  └─ rename_minutes_files.py
│
├─ 02_meeting_tables/         # 定例会・会議テーブル生成
│  ├─ teirei_sakusei_txt.py
│  ├─ teirei_sakusei_html.py
│  ├─ kaigi_sakusei.py
│  └─ teirei_kaigi_sakusei.py
│
├─ 03_giin_tables/            # 議員テーブル生成
│  ├─ giinlist_sakusei.py
│  ├─ giin_year.py
│  ├─ giin_sakusei.py
│  ├─ gicho.py
│  ├─ 副議長探索.py
│  └─ 監査委員検索.py
│
├─ 04_speech_tables/          # 発言抽出・QA生成
│  ├─ preprocess/
│  │  ├─ convert_to_utf8.py
│  │  ├─ format.py
│  │  └─ format_minutes.py
│  ├─ extraction/
│  │  ├─ 発言.py
│  │  ├─ html_hatsugen.py
│  │  └─ hatsugen_reigai.py
│  ├─ qa_generation/
│  │  ├─ hatsugen_paired.py
│  │  └─ hatsugen_qa.py
│
├─ utils/
│  └─ jiscode.json
│
├─ secrets/ (ignored)
│  └─ OPENAI_API_KEY.env
│
└─ .gitignore

 How to Setup
1. Clone repository
git clone https://github.com/ynk-soad/council_db.git

2. Python 環境構築
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

3. APIキーの設定

secrets/OPENAI_API_KEY.env に以下を書き込む：

OPENAI_API_KEY=xxxx

 Pipeline Overview
[01_scraper]
        ↓
   [PDF / HTML / TXT]
        ↓  （convert_to_utf8 / format）
   [Preprocessed Text]
        ↓
[02_meeting_tables / 03_giin_tables]
        ↓
[会議テーブル / 議員テーブル]
        ↓
     [04_speech_tables]
        ↓
     [発言テーブル]
        ↓
   [QA生成（RAG 用）]

 Use Cases

地方議会データベース構築

発言履歴の可視化

議会議論の構造分析

議会向け RAG チャットボット

行政データ分析研究の基盤整備

 Author

柚木 輝（ynk-soad）
Graduate School of Informatics, Kansai University

研究テーマ：
「地方議会データベース構築と RAG 検索システムの開発」

 License

MIT License.
