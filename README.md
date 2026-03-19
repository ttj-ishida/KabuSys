KabuSys — 日本株自動売買システム
=================================

バージョン: 0.1.0

概要
----
KabuSys は日本株のデータ取得（J-Quants）・ETL・特徴量作成・シグナル生成・ニュース収集・監査ログ管理を行うためのライブラリ群です。DuckDB をデータレイクとして使用し、研究（research）→ データ（data）→ 戦略（strategy）→ 実行（execution）層を分離した設計になっています。ルックアヘッドバイアスや冪等性、API レート制御、SSRF 対策など運用を考慮した実装方針が盛り込まれています。

主な機能
--------
- J-Quants API クライアント（差分取得・ページネーション・トークン自動リフレッシュ・レート制御）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系で DuckDB に冪等保存
- ETL パイプライン（差分取得、バックフィル、品質チェック統合）
  - run_daily_etl を中心とした日次処理
- 市場カレンダー管理（営業日判定、next/prev trading day 取得、夜間更新ジョブ）
- ニュース収集（RSS フェッチ、前処理、SSRF/サイズ制限、銘柄抽出、DB 保存）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）および特徴量生成
  - calc_momentum / calc_volatility / calc_value
  - build_features: 正規化・ユニバースフィルタ・features テーブルへの書き込み
- シグナル生成（正規化済み特徴量 + AI スコア → final_score → BUY/SELL 判定）
  - generate_signals: signals テーブルへの冪等書き込み
- DuckDB スキーマ定義・初期化（init_schema）
- 監査ログ / 発注トレーサビリティ用テーブル群の定義
- 汎用統計ユーティリティ（Zスコア正規化 等）
- 設定管理（環境変数・.env 自動読み込み）

セットアップ手順
----------------
1. Python 環境を用意
   - 推奨: Python 3.9+（プロジェクトの pyproject.toml/CI 設定に合わせてください）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - 必要な主な依存:
     - duckdb
     - defusedxml
   - 例（requirements.txt がある場合）:
     - pip install -r requirements.txt
   - ソースから開発インストールする場合:
     - pip install -e .

3. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（優先順位: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。
   - 必須環境変数（Settings 参照、未設定時は ValueError）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|...) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
   - サンプル:
     - JQUANTS_REFRESH_TOKEN=your_refresh_token
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで init_schema を呼び出します:
     - from kabusys.data.schema import init_schema
       conn = init_schema(settings.duckdb_path)
   - ":memory:" を渡すとインメモリ DB になります（テスト時に便利）。

使い方（主要な処理例）
---------------------

- 簡易インポート例（先に settings を適切に設定してください）:
  - from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.schema import init_schema, get_connection
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.strategy import build_features, generate_signals

- DB 初期化（1回実行）:
  - conn = init_schema(settings.duckdb_path)

- 日次 ETL の実行（市場カレンダー・株価・財務の差分取得）:
  - from datetime import date
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- 特徴量のビルド（指定日）:
  - build_count = build_features(conn, target_date=date(2026, 1, 31))
  - print(f"features upserted: {build_count}")

- シグナル生成（指定日）:
  - total_signals = generate_signals(conn, target_date=date(2026, 1, 31))
  - print(f"signals generated: {total_signals}")

- ニュース収集（RSS）:
  - from kabusys.data.news_collector import run_news_collection
    results = run_news_collection(conn, sources=None, known_codes=set(['7203','6758']))
    # results は {source_name: saved_count} の辞書

- J-Quants 生データ取得（低レベル）:
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    recs = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
    saved = save_daily_quotes(conn, recs)

設定（Settings）
----------------
設定は kabusys.config.Settings から読み取ります。主なプロパティ:
- jquants_refresh_token
- kabu_api_password
- kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
- slack_bot_token
- slack_channel_id
- duckdb_path (Path)
- sqlite_path (Path)
- env, log_level, is_live, is_paper, is_dev

.env ファイルの自動読み込み
- プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動で読み込みます。
- OS 環境変数は保護され、.env の値で上書きされません（ただし .env.local は override=True で上書き可能）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効にできます。

ディレクトリ構成
----------------
以下はソースルート（src/kabusys）配下の主なファイル・ディレクトリです（抜粋）。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                    -- 環境変数/Settings 管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント (fetch/save)
    - news_collector.py         -- RSS 収集・前処理・DB保存
    - schema.py                 -- DuckDB スキーマ定義・init_schema
    - stats.py                  -- zscore_normalize 等の統計ユーティリティ
    - pipeline.py               -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    -- market_calendar 管理・営業日ロジック
    - features.py               -- data レイヤの公開インターフェース（再エクスポート）
    - audit.py                  -- 監査ログ（signal_events / order_requests / executions）
    - ...（その他 data 用ユーティリティ）
  - research/
    - __init__.py
    - factor_research.py        -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py    -- forward returns / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py    -- build_features（正規化・ユニバースフィルタ）
    - signal_generator.py       -- generate_signals（final_score 計算・BUY/SELL）
  - execution/                  -- 発注周り（現状空のパッケージ）
  - monitoring/                 -- 監視・外部通知（Slack 等）用（実装箇所は config や audit を参照）

設計上の注意点
-------------
- ルックアヘッドバイアスを避けるように、各処理は target_date 時点でシステムが知り得るデータのみを参照する方針です（取得時刻/fetched_at を明確に保存）。
- DuckDB 側の INSERT は冪等（ON CONFLICT）を基本にしています。
- API への再試行・レート制御・トークンリフレッシュ等は jquants_client に実装されています。
- ニュース取得では SSRF 対策、gzip サイズ上限、XML パースの安全化（defusedxml）を行っています。
- production（live）モードでは KABUSYS_ENV を "live" に設定し、実行ロジックでの挙動分岐（例: 発注抑制など）を有効にしてください。

テストと開発
--------------
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを無効にできます。
- DuckDB の ":memory:" を使うとテスト用にインメモリ DB が使えます:
  - conn = init_schema(":memory:")

最後に
-----
本 README はコードベース（src/kabusys 以下）から抽出した主要機能・使い方を簡潔にまとめたものです。実運用向けには .env.example を作成して必要な環境変数を明示し、監視・リトライ・例外ハンドリング・シークレット管理（Vault 等）を整備してください。質問や追加ドキュメントが必要であれば教えてください。