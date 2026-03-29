# KabuSys

日本株向け自動売買・データプラットフォームライブラリ（KabuSys）。

本リポジトリはデータ取得（J-Quants）、データ品質チェック、特徴量生成・リサーチ、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、および監査ログの管理を目的としたモジュール群を提供します。バックテストや実運用の基盤（データ層・監査層・研究層）として利用できます。

---

## 主な特徴

- データ ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得して DuckDB に保存（冪等）。
  - 差分取得 / バックフィル / ページネーション対応 / レート制御 / トークン自動リフレッシュ。

- データ品質管理
  - 欠損・重複・スパイク・日付不整合などの品質チェック（QualityIssue を返却）。

- ニュース収集 & 前処理
  - RSS 取得（SSRF 対策、リダイレクト検査、サイズ制限、トラッキングパラメータ除去）と raw_news への保存（冪等）。

- ニュース NLP（OpenAI）
  - 銘柄ごとのセンチメントスコア算出（gpt-4o-mini を想定、JSON Mode を利用）・バッチ処理・リトライと検証付き。
  - 市場マクロニュースを使った市場レジーム判定（ETF 1321 の MA 乖離と OpenAI センチメントを合成）。

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルを DuckDB に冪等作成（監査用 DB 初期化ユーティリティあり）。

- 研究用途ユーティリティ
  - モメンタム/バリュー/ボラティリティ等のファクター計算、将来リターン・IC 計算、Z スコア正規化等。

---

## 必要条件 / 依存関係

- Python 3.10+
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実際の requirements.txt はプロジェクト側で用意してください。上記は本コードベースで直接利用している主要ライブラリです）

---

## 環境変数

config.Settings で利用される主な環境変数（必須は明記）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack bot token
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI の API キー（score_news / score_regime に使用）

自動で .env/.env.local をプロジェクトルートから読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。プロジェクトルートは .git または pyproject.toml を基準に探索します。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=/path/to/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば: pip install -r requirements.txt）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数を適宜設定します。
   - 自動読み込みはデフォルトで有効です。

5. DuckDB 初期化（監査テーブルなど）
   - 監査用スキーマを初期化する例:
     ```
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db

     conn = init_audit_db(settings.duckdb_path)  # ファイルを作成して監査テーブルを初期化
     conn.close()
     ```
   - 既存の DuckDB 接続に対して監査テーブルだけ追加する場合は init_audit_schema を呼ぶことも可能です。

---

## 使い方（代表的な例）

以下はモジュールをプログラムから利用する際の代表例です。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  ```
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- ニュースセンチメントの計算（OpenAI API が必要）
  ```
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を None にすると環境変数 OPENAI_API_KEY が使用される
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("written scores:", written)
  conn.close()
  ```

- 市場レジーム判定（MA + マクロニュース + LLM）
  ```
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  conn.close()
  ```

- RSS フィード取得（ニュース収集）
  ```
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- 監査 DB を新しく作る（ファイルが無ければ親ディレクトリも作成）
  ```
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  # 以降 conn を使って order_requests 等の操作が可能
  ```

---

## 注意点 / 運用メモ

- OpenAI 呼び出しは API 料金が発生します。score_news / score_regime は API キーを必ず設定して利用してください（関数引数 api_key を与えるか環境変数 OPENAI_API_KEY を設定）。
- J-Quants API の利用にはリフレッシュトークンが必要です。settings.jquants_refresh_token を正しく設定してください。
- DuckDB への executemany 等で空のパラメータリストが問題になるケースがあるため、各関数は空リストの処理をガードしています（そのまま呼べば安全です）。
- カレンダー / ETL は Look-ahead bias（先見バイアス）を避ける設計になっています。target_date を明示して利用してください。
- ニュース収集は SSRF 対策・サイズ制限・XML 安全パーサ（defusedxml）を使用していますが、運用時は RSS ソースの信頼性・取り扱いに留意してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - pipeline.py
  - etl.py
  - jquants_client.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - etl.py (再エクスポート用)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
  - (その他ユーティリティ)
- research/* はファクター計算・IC/統計ユーティリティを提供

（上記は主要モジュールのみ抜粋しています。詳しくはソースツリーを参照してください。）

---

## 開発 / テスト

- 自動環境変数読み込みを無効にしたい場合は環境変数を設定:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- ユニットテストを作成する際は、OpenAI 呼び出しやネットワークを伴う関数はモック化してテストしてください（コード中で _call_openai_api やネットワーク関連の低レイヤ関数が分離されています）。

---

README に記載のないモジュールや関数の詳細はソースコード（src/kabusys 以下）を参照してください。必要であれば、用途別の使い方サンプルや API リファレンスを追加で作成します。