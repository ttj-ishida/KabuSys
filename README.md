KabuSys — 日本株向けデータ基盤・リサーチ・自動売買ユーティリティ
=============================================================================

概要
----
KabuSys は日本株向けに設計されたデータ収集・ETL・品質チェック・研究用ファクター計算・ニュースNLP・市場レジーム判定・監査ログ等をまとめた Python パッケージです。J-Quants / RSS / OpenAI（LLM）などの外部サービスと連携して、日次 ETL、AI によるニュースセンチメント評価、研究用指標計算や注文関連の監査テーブルの初期化を行うためのユーティリティを提供します。

主な機能
--------
- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得・冪等保存
  - run_daily_etl による日次 ETL パイプライン
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付整合性 などのチェック
- ニュース収集 / 前処理
  - RSS フィードの安全な収集（SSRF 対策、gzip 上限検査、URL 正規化）
- ニュース NLP（OpenAI）
  - 銘柄単位のセンチメントスコア算出（gpt-4o-mini, JSON mode）
  - news_nlp.score_news(conn, target_date, api_key=None)
- 市場レジーム判定（AI + テクニカル）
  - ETF(1321) の 200 日 MA 乖離とマクロニュースセンチメントを組み合わせ日次でレジーム判定
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 研究用ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を SQL と Python で利用）
  - forward returns / IC / factor summary などのユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルとインデックス定義
  - DuckDB で監査 DB を初期化する init_audit_db

前提・依存
-----------
- Python 3.10+（ソースで | 型注釈を使用）
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ多数（urllib, datetime, json 等）

セットアップ手順
----------------
1. リポジトリをクローン（またはパッケージを取得）
   - 例: git clone <repo_url>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\Activate     (Windows)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （開発： pip install -e . を使う場合は pyproject.toml / setup が必要）

4. 環境変数（.env）を用意
   - プロジェクトルート（.git や pyproject.toml のある場所）に .env を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の主な環境変数（.env 例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_station_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C12345678
- OPENAI_API_KEY=sk-...
- （オプション）DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|...

例 (.env)
- JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
- OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C0XXXXXXX
- DUCKDB_PATH=data/kabusys.duckdb

使い方（簡易サンプル）
---------------------

共通：DuckDB 接続を作る
- import duckdb
- from kabusys.config import settings
- conn = duckdb.connect(str(settings.duckdb_path))

1) 日次 ETL を実行する
- from kabusys.data.pipeline import run_daily_etl
- from datetime import date
- result = run_daily_etl(conn, target_date=date(2026,3,20))
- print(result.to_dict())  # ETL 結果の概要

2) ニュースセンチメントを算出して ai_scores に書き込む
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
- print(f"書込銘柄数: {n_written}")

3) 市場レジーム判定（regime を market_regime テーブルに書込）
- from kabusys.ai.regime_detector import score_regime
- from datetime import date
- score_regime(conn, target_date=date(2026,3,20), api_key=None)

4) 研究用ファクター計算（例：モメンタム）
- from kabusys.research.factor_research import calc_momentum
- records = calc_momentum(conn, target_date=date(2026,3,20))
- # records は [{ "date":..., "code":..., "mom_1m":..., ... }, ...] のリスト

5) 監査 DB（監査用 DuckDB）を初期化する
- from kabusys.data.audit import init_audit_db
- conn_audit = init_audit_db("data/audit.duckdb")
- # テーブルとインデックスが作成されます

設定の自動読み込み
------------------
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）を基に .env と .env.local を自動読み込みします。
  - 既存 OS 環境変数 > .env.local > .env の順で優先
  - テスト等で自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します

主なモジュール説明
------------------
- kabusys.config
  - 環境変数の取得とバリデーション（Settings クラス）
- kabusys.data
  - jquants_client: J-Quants API 呼び出し・DuckDB 保存ロジック
  - pipeline: 日次 ETL のオーケストレーション（run_daily_etl 等）
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - news_collector: RSS フィードの安全な収集と前処理
  - calendar_management: JPX カレンダー管理と営業日ロジック
  - audit: 監査ログテーブル定義・初期化
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp: 銘柄ごとのニュースセンチメント算出（score_news）
  - regime_detector: ETF MA とマクロニュースを組み合わせた市場レジーム判定（score_regime）
- kabusys.research
  - factor_research: momentum / volatility / value などのファクター計算
  - feature_exploration: forward returns, IC, factor_summary, rank など

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
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
  - quality.py
  - news_collector.py
  - calendar_management.py
  - audit.py
  - etl.py
  - stats.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/ や ai/ 以下に研究・モデルロジック、OpenAI 用呼び出しが実装されています。

運用時の注意点 / ベストプラクティス
----------------------------------
- OpenAI 呼び出しや外部 API はレート・コストが発生するため、本番では API キー管理と呼び出し頻度に注意してください。
- ETL / AI 実行は運用スケジューラ（cron / Airflow 等）で夜間に行う想定です。
- DuckDB ファイルのバックアップ・バージョン管理（特に監査 DB）は運用ルールを設けてください。
- 本パッケージの関数は Look-ahead bias を避ける設計思想（target_date 未満でデータ参照など）を守っています。研究やバックテストで日付指定を適切に行ってください。

ライセンス / 貢献
-----------------
- （リポジトリにライセンスファイルがあればそこを参照してください。ここでは特に指定していません。）

問い合わせ
----------
実行でエラーが出る場合は、実行ログ（LOG_LEVEL=DEBUG を推奨）と使用した環境変数（秘匿情報は除外）を添えて報告してください。