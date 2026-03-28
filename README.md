# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買基盤のためのライブラリ群です。  
J-Quants / RSS / OpenAI 等と連携してデータ収集（ETL）、品質チェック、ニュースセンチメント評価、マーケットレジーム判定、監査ログの管理などを行うことを目的としています。

主な特徴
- J-Quants API を用いた株価・財務・上場銘柄・マーケットカレンダーの差分取得（ページネーション・リトライ・レート制御付き）
- DuckDB をデータレイクとして使用する ETL パイプライン（差分更新・バックフィル・品質チェック付き）
- RSS ベースのニュース収集（SSRF対策・トラッキングパラメータ除去・前処理）
- OpenAI（gpt-4o-mini）を用いたニュース NLP（銘柄別センチメント）と市場レジーム判定モジュール
- 監査ログ（signal → order_request → execution）のための冪等なテーブル定義と初期化ユーティリティ
- 各種データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計要約、Z スコア正規化）

----------------------------------------
## 機能一覧（モジュール別ハイライト）

- kabusys.config
  - .env 自動読み込み（.env → .env.local、OS 環境変数優先）
  - アプリ設定（J-Quants トークン、OpenAI キー、DB パス、環境フラグなど）
- kabusys.data
  - jquants_client: API 呼び出し、保存関数（raw_prices, raw_financials, market_calendar 等）
  - pipeline: 日次 ETL run_daily_etl / 個別 ETL ジョブ（run_prices_etl 等）と ETLResult
  - news_collector: RSS 取得・正規化・raw_news 保存
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合）
  - calendar_management: 営業日判定 / next/prev_trading_day / calendar_update_job
  - audit: 監査ログ用テーブル定義と初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等汎用統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news(conn, target_date): 銘柄ごとの AI センチメントを ai_scores テーブルへ書込
  - regime_detector.score_regime(conn, target_date): ETF（1321）MA とマクロニュースの LLM センチメントを合成して market_regime に書込
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- その他
  - 環境に依存しない設計（Look-ahead バイアス回避、DuckDB を用いた SQL 処理）

----------------------------------------
## 必要条件 / 依存パッケージ（例）

- Python 3.10+
- duckdb
- openai (OpenAI の Python SDK)
- defusedxml
- （標準ライブラリ: urllib, json, datetime, logging 等）

インストール例（プロジェクトルートで）:
- pip install -e . もしくは
- pip install duckdb openai defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

----------------------------------------
## 環境変数（主要なもの）

必須（本番的な実行で必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client.get_id_token に使用）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（監視等で使用）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- KABU_API_PASSWORD — kabu ステーション API のパスワード（API を使う場合）

オプション / デフォルトあり:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール呼び出し用）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（monitoring DB）パス（デフォルト data/monitoring.db）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env と .env.local を自動読み込みします。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）

----------------------------------------
## セットアップ手順（開発 / 実行）

1. リポジトリをクローン
   - git clone <repo> && cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
     または
   - pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルートに .env を作成するか、環境変数を設定してください。
   - 最低限、JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY（AI を使う場合）を準備してください。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB スキーマの初期化（監査ログ等）
   - 監査ログ専用 DB を作りたい場合:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - 既存のデータ DB に監査テーブルを追加する場合:
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

----------------------------------------
## 基本的な使い方（コード例）

- DuckDB 接続を生成して ETL を実行する（日次 ETL）:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- OpenAI を使ってニュースセンチメント（ai_scores）を生成する:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")

  備考: OPENAI_API_KEY は環境変数か api_key 引数で渡してください。

- 市場レジーム判定を行い market_regime に書き込む:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 研究用ファクター計算:
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(mom), "records")

- ニュース RSS の手動取得（news_collector.fetch_rss）:
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])

----------------------------------------
## よく使うユーティリティ / 注意点

- Look-ahead バイアス回避
  - 多くの関数は内部で date.today() や datetime.now() を直接参照しない設計で、バックテストや再現性の高い処理に配慮しています。target_date を明示して呼び出してください。

- 自動リトライ / フェイルセーフ
  - OpenAI や J-Quants 呼び出しはレート制御・リトライ・5xx ハンドリングが組み込まれています。API 失敗時はゼロや空でフォールバックする箇所があるため、ログを確認してください。

- DuckDB 側の executemany 空リスト制約
  - DuckDB のバージョンによって executemany に空リストを渡すとエラーになるため、コード内で事前チェックを行っています。

- .env 読み込み
  - ローカル開発では .env と .env.local を使い分けると便利です。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を有効にしてください。

----------------------------------------
## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - quality.py
    - stats.py
    - calendar_management.py
    - audit.py
    - etl.py (ETL result re-export)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research パッケージは zscore_normalize 等を re-export
- pyproject.toml / setup.cfg / requirements.txt（リポジトリに含める想定）

----------------------------------------
## ロギング・監視

- ログレベルは環境変数 LOG_LEVEL で制御できます（デフォルト INFO）。
- Slack 連携や監視機能は別途実装されている箇所からトークンを参照します（SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）。

----------------------------------------
## テスト・開発のヒント

- 外部 API 呼び出し（OpenAI, J-Quants, HTTP）部分はモジュール内部で呼び出し関数が分離されており、単体テスト時は unittest.mock.patch で差し替えてテスト可能です（例: kabusys.ai.news_nlp._call_openai_api をモック）。
- news_collector のネットワーク部分は _urlopen を差し替えることでローカルテストしやすくなっています。
- KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で .env の自動ロードを無効にできます（テストや CI で明示的に環境を構築したい場合に有効）。

----------------------------------------
この README はコードベースの説明と利用手順のサマリです。  
実運用／デプロイ時はセキュリティ（API キー管理・ネットワークアクセス制限）や運用監視、ログの永続化、バックアップ等を必ず検討してください。