# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。J-Quants / kabuステーション / RSS / OpenAI を組み合わせ、データ収集（ETL）・データ品質チェック・ファクター計算・ニュースセンチメント・市場レジーム判定・監査ログなどを提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API障害時は安全側にフォールバック）」です。

---

## 機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env/.env.local を自動読み込み（無効化可）
  - 必須設定の検査（例: JQUANTS_REFRESH_TOKEN）
- データ収集・ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants から株価日足 / 財務データ / マーケットカレンダーを差分取得
  - 保存は DuckDB に対して冪等に保存（ON CONFLICT 相当）
  - レートリミット・リトライ・トークン自動リフレッシュ対応
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合チェック
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定／前後営業日検索／バッチでのカレンダー更新
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF対策、前処理、raw_news への冪等保存向けユーティリティ
- AI（OpenAI）を用いた NLP（kabusys.ai）
  - ニュースごとの銘柄センチメント集計（score_news）
  - ETF + マクロニュースを合成した市場レジーム判定（score_regime）
  - API 呼び出しは JSON Mode を利用し、複数リトライ・フェイルセーフを実装
- 研究用分析（kabusys.research）
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions など監査テーブルの初期化ユーティリティ
  - 監査DBの初期化関数（init_audit_db）を提供

---

## 必要条件

- Python 3.10+
- 推奨ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトによってはさらに依存がある可能性があります。setup.py / pyproject.toml を参照してください。）

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動
   - 例: git clone ... && cd kabusys

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install --upgrade pip
   - 必要最低限の例:
     - pip install duckdb openai defusedxml

   - 開発インストール（プロジェクトに pyproject.toml / setup.py がある場合）:
     - pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成して必要な環境変数を設定します。自動読み込み機能はデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_PASSWORD: kabuステーション API パスワード（利用時）
     - SLACK_BOT_TOKEN: Slack 通知用トークン（利用時）
     - SLACK_CHANNEL_ID: Slack チャネル ID（利用時）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

---

## 使い方（クイックスタート）

以下の例は Python REPL やスクリプトから実行できます。DuckDB 接続は kabusys.config.settings.duckdb_path 等で指定される既定パスを使用するか、任意のパスを渡してください。

- DuckDB 接続の作成例
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（run_daily_etl）
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメントをスコアリングする（score_news）
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(str(settings.duckdb_path))
  - n_written = score_news(conn, target_date=date(2026, 3, 20))
  - print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定を行う（score_regime）
  - from datetime import date
  - import duckdb
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - score_regime(conn, target_date=date(2026, 3, 20))

- 監査DB（監査ログ）を初期化する
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")
  - # conn を使って監査テーブルにアクセスできます

- RSS をフェッチする（ニュース収集）
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  - articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  - for a in articles:
  -     print(a["id"], a["datetime"], a["title"])

- カレンダー／営業日ヘルパー
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - conn = duckdb.connect(str(settings.duckdb_path))
  - is_td = is_trading_day(conn, date(2026, 3, 20))

注意:
- OpenAI を用いる関数（score_news, score_regime）は OPENAI_API_KEY を必要とします。api_key 引数で明示的に渡すことも可能です。
- ETL / API 呼び出しにはネットワークアクセスと API キーが必要です。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env 自動ロードを無効化できます。

---

## よく使う API（抜粋）

- kabusys.data.pipeline.run_daily_etl(conn, target_date, id_token=None, ...)
  - 日次の ETL（カレンダー・株価・財務・品質チェック）を実行し ETLResult を返す。

- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - J-Quants からデータを取得する低レベル関数（ページネーション対応）。

- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
  - DuckDB に冪等保存する関数。

- kabusys.data.quality.run_all_checks(conn, target_date, reference_date)
  - データ品質チェックの一括実行。

- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ニュースを OpenAI でスコアリングして ai_scores に書き込む。

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - マクロニュースと ETF の MA を合成して market_regime に書き込む。

- kabusys.data.audit.init_audit_db(path)
  - 監査用 DuckDB を初期化して接続を返す。

---

## テスト・デバッグのヒント

- 環境変数の自動ロードは config モジュールがプロジェクトルート（.git または pyproject.toml を探索）を見つけることで行われます。テストで自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の呼び出しは内部で複数回リトライ・フェイルセーフ処理を行います。ユニットテストでは関数をモックしてネットワーク依存を排除してください（モジュール内で _call_openai_api をパッチする箇所が想定されています）。
- DuckDB の executemany に空リストを渡すと例外になるバージョンがあります（注意: コードはこの点を回避するためにガードを入れています）。

---

## ディレクトリ構成

（抜粋 — 主要ファイルのみを示します）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント処理
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント・保存処理
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL インターフェース再エクスポート
    - calendar_management.py         — マーケットカレンダー管理
    - news_collector.py              — RSS 収集ユーティリティ
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore 等）
    - audit.py                       — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum/value/vol）
    - feature_exploration.py          — 将来リターン / IC / 統計サマリー
  - (その他: strategy, execution, monitoring のパッケージが意図されている)

---

## ライセンス・貢献

- この README ではライセンスファイルや貢献ルールは含めていません。リポジトリの LICENSE / CONTRIBUTING を確認してください。

---

README は以上です。必要であれば、実行例の詳細スクリプト（ETL cron ジョブサンプル、Dockerfile、requirements.txt 例）も作成します。どのサンプルが必要か教えてください。