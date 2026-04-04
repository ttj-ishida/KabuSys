# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants クライアント、マーケットカレンダーなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム取引・リサーチのための内部ライブラリ群です。主な目的は以下です。

- J-Quants API からのデータ取得（株価日足・財務・マーケットカレンダー）
- データの ETL（差分取得・保存・品質チェック）
- ニュース収集（RSS）と LLM によるニュースセンチメント評価
- 市場レジーム判定（MA とマクロニュースを合成）
- 研究用ファクター計算・特徴量解析ユーティリティ
- 監査ログ（signal → order → execution のトレーサビリティ）
- DuckDB ベースのローカルデータ管理

設計方針としては「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗で処理継続）」「冪等性（ON CONFLICT 等）」を重視しています。

---

## 主な機能一覧

- data/jquants_client: J-Quants API クライアント（レート制限、トークン自動リフレッシュ、保存関数）
- data/pipeline: 日次 ETL（カレンダー・株価・財務・品質チェック）と ETLResult
- data/news_collector: RSS 取得と raw_news への整形ロジック（SSRF 対策・トラッキング除去）
- data/quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
- data/calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
- data/audit: 監査ログ（signal_events / order_requests / executions）のスキーマ初期化
- ai/news_nlp: ニュースを銘柄ごとにまとめて LLM（gpt-4o-mini）でスコア化し ai_scores に保存
- ai/regime_detector: 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存
- research: ファクター計算（モメンタム / ボラティリティ / バリュー）と探索ユーティリティ
- data/stats: zscore_normalize などの統計ユーティリティ
- config: .env または環境変数から設定を読み込む Settings クラス

---

## 動作環境 / 必要要件

- Python 3.10+
- 必要な外部パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード など）

（プロジェクトに requirements.txt があればそれを使用してください。ここでは主要依存を挙げています。）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   # 開発時はパッケージを編集可能モードでインストール
   pip install -e .
   ```

4. 環境変数 / .env を用意  
   プロジェクトはルートの `.env` / `.env.local` を自動ロードします（CWD ではなくパッケージ位置からプロジェクトルートを探索）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（例）:
   ```
   # 必須
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # オプション（必要に応じて）
   KABU_API_PASSWORD=...
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   OPENAI_API_KEY=sk-...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   KILL_FLAG_CLEAR_ON_START=0
   CPU_THRESHOLD_PCT=90.0
   MEMORY_THRESHOLD_PCT=85.0
   DISK_THRESHOLD_PCT=90.0
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な例）

以下は Python から使う際の代表的なスニペットです。

- DuckDB 接続を作り ETL を実行する（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントをスコア化（ai.news_nlp.score_news）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written scores: {written}")
```

- 市場レジームを判定（ai.regime_detector.score_regime）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査DB 初期化（data.audit）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続
```

- J-Quants トークンを取得（data.jquants_client）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

- RSS フィード取得（data.news_collector）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

url = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(url=url, source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

テスト時には OpenAI 呼び出しなどをモックすることが想定されています（モジュール内の `_call_openai_api` を patch するなど）。

---

## 設定の自動読み込み動作

- 自動読み込み順序: OS 環境変数 > .env.local > .env  
- 自動読み込みはパッケージルート（.git または pyproject.toml のある親ディレクトリ）を基準に行います。  
- 自動読み込みを無効にしたい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- Settings クラスから設定値は取得できます:
  ```python
  from kabusys.config import settings
  settings.jquants_refresh_token
  settings.duckdb_path
  settings.env  # development | paper_trading | live
  ```

---

## ディレクトリ構成（主要ファイル説明）

- src/kabusys/
  - __init__.py — パッケージ定義（data, strategy, execution, monitoring を公開）
  - config.py — 環境変数 / .env 読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを銘柄ごとに集約して LLM でセンチメントを算出、ai_scores に保存
    - regime_detector.py — ETF 1321 の MA200 とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存関数・認証）
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - etl.py — ETLResult の公開
    - news_collector.py — RSS 取得・前処理・記事保存ユーティリティ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - calendar_management.py — JPX カレンダー管理と営業日ユーティリティ
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - その他（strategy, execution, monitoring 等の名前空間は __all__ に含まれているが本リスト内に未実装のモジュールがある場合あり）

（上記は主要モジュールの概要です。各ファイル内に詳細な docstring が記載されています。）

---

## 開発上の注意 / 補足

- ルックアヘッドバイアス対策として、日付の扱いや DB クエリは target_date 未満／以前など明示的に指定しています。バックテスト用途に流用する際は注意してください。
- OpenAI API 呼び出しは gpt-4o-mini を前提に JSON Mode を使う設計です。APIの仕様・料金に注意してください。
- ニュース収集は SSRF 対策・レスポンス長制限・トラッキング除去など保守的な実装になっています。
- DuckDB への一括保存は冪等性（ON CONFLICT）を担保するように作られています。
- テストでは外部呼び出し（HTTP/OpenAI）をモックすることが推奨されます。ソース中にモック対象となる内部ヘルパ関数への注記があります。

---

## ライセンス / 貢献

本リポジトリに LICENSE ファイルがあればそれに従ってください。貢献はプルリクエストを通じて行ってください。大きな変更は事前に Issue で相談をお願いします。

---

README は以上です。必要であれば、README に含めるサンプル .env.example や requirements.txt のテンプレートも作成しますので指示ください。