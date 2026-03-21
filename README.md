KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株を対象とした自動売買プラットフォーム向けのライブラリ群です。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査・スキーマ管理などの機能をモジュール化して提供します。  
設計上の主な方針は「ルックアヘッドバイアスの排除」「冪等性」「ロギングとトレーサビリティ」「外部依存の最小化（標準ライブラリ中心）」です。

主な機能一覧
-------------
- データ取得・保存
  - J-Quants API クライアント（jquants_client）: 日足・財務・マーケットカレンダー等を取得、DuckDB へ冪等保存
- ETL パイプライン（data.pipeline）
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- スキーマ管理（data.schema）
  - DuckDB のスキーマ定義と初期化（init_schema）
- 特徴量計算（research.factor_research / strategy.feature_engineering）
  - Momentum / Volatility / Value 等のファクター計算、Z スコア正規化、ユニバースフィルタ
- シグナル生成（strategy.signal_generator）
  - 正規化済みファクター＋AI スコア統合による final_score 計算、BUY/SELL シグナル生成・保存
- ニュース収集（data.news_collector）
  - RSS 取得、前処理、raw_news 保存、銘柄抽出（SSRF 対策、gzip 上限、トラッキングパラメータ除去）
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定、next/prev_trading_day、夜間カレンダー更新ジョブ
- 監査ログ（data.audit）
  - シグナル→発注→約定のトレース用テーブル群（冪等キー・履歴保持）

前提条件 / 必要環境
------------------
- Python 3.10 以上（型注釈に | を使用）
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース）
- 任意: kabuステーション API（発注連携を行う場合）

セットアップ手順
----------------
1. リポジトリをクローンし仮想環境を作成
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
2. パッケージと依存をインストール
   - pip install -e . もしくは
   - pip install duckdb defusedxml
   （プロジェクト配布物に requirements.txt / pyproject.toml がある場合はそちらを利用）
3. 環境変数の設定
   - プロジェクトルートの .env / .env.local を自動で読み込みます（設定は kabusys.config.Settings 経由で参照）。
   - 必須の環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - KABU_API_PASSWORD=<kabu_api_password>
     - SLACK_BOT_TOKEN=<slack_bot_token>
     - SLACK_CHANNEL_ID=<slack_channel_id>
   - オプション:
     - KABUSYS_ENV=development|paper_trading|live  (default: development)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - LOG_LEVEL (DEBUG/INFO/...)
   - 自動 .env 読み込みを無効化するには:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行われます。
4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     - from kabusys.config import settings
       from kabusys.data.schema import init_schema
       init_schema(settings.duckdb_path)
   - :memory: を渡すとインメモリ DB も利用可能です。

基本的な使い方（コード例）
-------------------------

- DuckDB 接続とスキーマ初期化
  - from kabusys.config import settings
    from kabusys.data.schema import init_schema, get_connection
    conn = init_schema(settings.duckdb_path)  # 存在しなければファイル作成＋テーブル作成

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)  # target_date を指定可能
    print(result.to_dict())

- 特徴量作成（strategy 用 features テーブルへの保存）
  - from kabusys.strategy import build_features
    from datetime import date
    count = build_features(conn, date(2025, 1, 31))

- シグナル生成（features / ai_scores / positions を参照して signals を作成）
  - from kabusys.strategy import generate_signals
    total = generate_signals(conn, date(2025, 1, 31))
    print(f"signals written: {total}")

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
  - from kabusys.data.news_collector import run_news_collection
    results = run_news_collection(conn, sources=None, known_codes={'7203','6758'})
    print(results)

- J-Quants API 直接使用例
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    records = fetch_daily_quotes(date_from=..., date_to=...)
    saved = save_daily_quotes(conn, records)

運用・スケジューリングのヒント
------------------------------
- ETL は通常夜間バッチで実行します（cron/systemd timer 等）。run_daily_etl を呼ぶのが標準。
- calendar_update_job はマーケットカレンダーの先読み（lookahead）更新に使用します。
- 実口座（KABUSYS_ENV=live）では log_level を INFO/WARNING に設定し、発注実行前に paper_trading で十分な検証を推奨します。
- 監査テーブル（data.audit）を有効にしてシグナル→発注→約定のトレーサビリティを確保してください。

よく使う環境変数（要設定）
--------------------------
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須：発注連携時）
- KABU_API_BASE_URL — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — システム通知用 Slack Bot Token（必須：Slack 通知を使う場合）
- SLACK_CHANNEL_ID — 通知先の Slack チャンネル ID（必須：Slack 通知を使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development|paper_trading|live)
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/...)

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                        — 環境変数／設定管理
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント + 保存ロジック
  - news_collector.py              — RSS 収集・前処理・保存
  - schema.py                      — DuckDB スキーマ定義・初期化
  - stats.py                       — 統計ユーティリティ（zscore_normalize 等）
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py         — カレンダー管理（営業日判定・更新ジョブ）
  - features.py                    — features の公開インターフェース
  - audit.py                       — 監査ログ用テーブル定義
- research/
  - __init__.py
  - factor_research.py             — Momentum/Volatility/Value 計算
  - feature_exploration.py         — IC/forward returns/summary
- strategy/
  - __init__.py
  - feature_engineering.py         — 特徴量合成・正規化・features テーブルへ保存
  - signal_generator.py            — final_score 計算・BUY/SELL シグナル生成・保存
- execution/                         — （発注/実行層：ファイルは存在するが詳細は実装に依存）
- monitoring/                        — 監視・アラート関連（DB 監視等）

設計上の注意点・トラブルシューティング
------------------------------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストなどで自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API はレート制限（120 req/min）に対応する内部レートリミッタを備えています。大量取得時は時間を要します。
- RSS 収集は SSRF や大容量レスポンスに対する対策（スキーム検証、プライベートホスト検知、サイズ上限、gzip 解凍後検査）を実装していますが、外部ソースを追加する際には注意してください。
- DuckDB schema 初期化は冪等化されています。既存テーブルがあっても安全に実行できます。
- strategy・research モジュールは prices_daily / raw_financials / features 等のテーブルを前提としています。ETL → スキーマ初期化 → 特徴量生成 → シグナル生成の順で実行してください。
- 発注（execution）や実運用での外部証券会社連携は安全性（重複発注防止、監査ログ）を重視してください。KabuSys は監査用のテーブル群と冪等キー設計を提供しますが、具体的なブローカー向け実装は別途実装が必要です。

ライセンス・貢献
----------------
（ここにはプロジェクトのライセンス情報や貢献ガイドラインを記載してください。）

最後に
------
この README はコードベースの概要と利用のガイドラインを短くまとめたものです。各モジュールには詳細な docstring と実装コメントが付与されていますので、より深い利用方法や拡張は該当モジュールのコードとコメントを参照してください。必要であれば詳しい導入スクリプトや運用例（systemd timer, Docker Compose）も追加で作成可能です。