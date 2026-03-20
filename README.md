KabuSys
=======

日本株向けの自動売買プラットフォームのライブラリ群です。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ・スキーマ定義など、投資システムの主要コンポーネントを含みます。

概要
----
KabuSys は以下のレイヤで構成されたシステムを想定しています。

- Data Layer（J-Quants からの取得 → DuckDB 保存）
- Processed / Feature Layer（prices_daily / features / ai_scores 等）
- Strategy Layer（特徴量合成 / シグナル生成）
- Execution / Audit Layer（シグナル → 発注 → 約定 / 監査ログ）
- Research ツール（factor 計算・IC・将来リターン解析 等）
- News Collector（RSS から記事収集・銘柄紐付け）

設計上の特徴：
- DuckDB を用いたローカル DB（オンディスクまたはインメモリ）
- J-Quants API とのやり取りはレートリミット・自動リフレッシュ・リトライを備えたクライアントで実装
- ETL は差分更新・バックフィル・品質チェックを考慮
- 戦略処理はルックアヘッドバイアスを避ける設計（target_date ベース）
- ニュース収集は SSRF 対策・XML 脆弱性対策を実装
- 冪等性（ON CONFLICT や idempotent な insert）を重視

主な機能一覧
-------------
- data.jquants_client: J-Quants から daily quotes / financial statements / market calendar の取得・保存
- data.schema: DuckDB のテーブル定義と初期化（init_schema）
- data.pipeline: 日次 ETL（run_daily_etl）＋個別 ETL（prices/financials/calendar）
- data.news_collector: RSS フィード収集・正規化・raw_news / news_symbols 保存
- data.calendar_management: 営業日判定、next/prev/get_trading_days、calendar 更新ジョブ
- data.stats: Z スコア正規化ユーティリティ
- research.factor_research, research.feature_exploration: ファクター計算、将来リターン、IC、統計サマリー
- strategy.feature_engineering: raw factor を統合して features テーブルを作成（build_features）
- strategy.signal_generator: features / ai_scores を統合して BUY/SELL シグナルを生成（generate_signals）
- audit: 監査ログ用のテーブル定義（signal_events, order_requests, executions 等）
- config: 環境変数の読み込み・管理（.env 自動読み込みの仕組み・settings オブジェクト）

セットアップ手順
----------------

前提
- Python 3.10 以上（型アノテーションで | を使用）
- 利用する環境に応じた J-Quants API トークン等が必要

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb defusedxml

   プロジェクトで追加の依存がある場合（例: Slack 通知等）は別途インストールしてください。

3. 環境変数の用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます（優先順位: OS 環境変数 > .env.local > .env）。
   - 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（execution 層で使用する場合）
- SLACK_BOT_TOKEN: Slack 通知を使う場合
- SLACK_CHANNEL_ID: Slack 通知先チャネル
（その他）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db

例 (.env)
- JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development

使い方（簡単な例）
-----------------

以下は Python REPL / スクリプトからの簡単な利用例です。

1) DuckDB スキーマ初期化
- from kabusys.config import settings
- from kabusys.data.schema import init_schema
- conn = init_schema(settings.duckdb_path)  # ":memory:" を渡すとインメモリ DB

2) 日次 ETL 実行（J-Quants からの差分取得）
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn)
- print(result.to_dict())

3) 特徴量作成
- from kabusys.strategy import build_features
- from datetime import date
- cnt = build_features(conn, date(2024, 1, 5))
- print(f"features upserted: {cnt}")

4) シグナル生成
- from kabusys.strategy import generate_signals
- total = generate_signals(conn, date(2024, 1, 5))
- print(f"signals written: {total}")

5) ニュース収集ジョブ
- from kabusys.data.news_collector import run_news_collection
- known_codes = {"7203", "6758", "9984"}  # 実際は prices_daily などから有効コードセットを作成
- results = run_news_collection(conn, known_codes=known_codes)
- print(results)

6) カレンダー更新ジョブ（夜間バッチ向け）
- from kabusys.data.calendar_management import calendar_update_job
- saved = calendar_update_job(conn)
- print(f"saved calendar rows: {saved}")

設定（settings）利用例
- from kabusys.config import settings
- settings.jquants_refresh_token  # 必須値が未設定なら ValueError を送出

自動 .env 読み込みの仕様
- プロジェクトルート（.git または pyproject.toml がある場所）を起点として .env と .env.local を読み込みます。
- 読み込み順: OS 環境変数 > .env.local（上書き） > .env（既存を上書きしない）
- テストや一時的に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

開発 / デバッグのヒント
- settings.log_level を参照してログ出力レベルを設定してください。
- テスト時は settings.duckdb_path = ":memory:" を使うとインメモリ DB で高速に動作します。
- jquants_client の呼出しはネットワーク依存なので、unittest では _request や _urlopen 等をモックすると良いです。
- news_collector._urlopen や jquants_client._request をモック注入できるよう実装済みの箇所があるため、単体テストの代替が容易です。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                              # 環境変数 / settings
    - data/
      - __init__.py
      - jquants_client.py                     # J-Quants API クライアント（取得・保存）
      - news_collector.py                     # RSS 収集・保存・銘柄抽出
      - schema.py                             # DuckDB スキーマ定義・init_schema
      - stats.py                              # zscore_normalize 等
      - pipeline.py                           # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py                # カレンダー管理 / calendar_update_job
      - features.py                            # features インターフェース再エクスポート
      - audit.py                               # 監査ログ DDL
    - research/
      - __init__.py
      - factor_research.py                    # mom/vol/val ファクター計算
      - feature_exploration.py                # forward_returns / IC / summary
    - strategy/
      - __init__.py
      - feature_engineering.py                # build_features
      - signal_generator.py                   # generate_signals
    - execution/                               # 発注関連（骨組み）
      - __init__.py
    - monitoring/                              # 監視・メトリクス関連（骨組み）

注意事項 / 制約
----------------
- このリポジトリは投資アルゴリズムを含みます。実運用前に必ず十分なテスト・バックテストを行い、リスク管理を適用してください。
- 本コードは一部外部サービス（J-Quants / kabuステーション / Slack 等）に依存します。実行にはそれらの認証情報が必要です。
- DuckDB の SQL は ON CONFLICT 等で冪等性を担保していますが、実際のデータ運用ではバックアップ・スキーマ管理を行ってください。

ライセンス
---------
（この README 生成時点でのライセンス表記はありません。実プロジェクトでは LICENSE を追加してください。）

サポート / 開発
----------------
- 開発者向け: 単体テストはネットワーク呼び出しをモックして実行してください（jquants_client._request や news_collector._urlopen 等を差し替え可能）。
- バグ報告・機能要望は Issue で管理してください。

以上が KabuSys の概要・セットアップ・基本的な使い方です。必要であれば README に「コマンドラインツールの使い方」「具体的な .env.example のテンプレート」「CI 設定例」などを追加できます。どの情報を追記したいか教えてください。