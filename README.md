# KabuSys — 日本株自動売買システム

簡潔な説明
- KabuSys は日本株向けのデータ収集・加工・特徴量生成・シグナル生成を行うライブラリ群です。J-Quants API からのマーケットデータ取得、DuckDB による永続化、リサーチ向けファクター計算、戦略用の特徴量構築・スコアリング、RSS ニュース収集などを含みます。
- 設計方針として「ルックアヘッドバイアス防止」「冪等性」「外部 API のリトライとレート制御」「DB トランザクションによる原子性」を重視しています。

主な機能一覧
- データ取得・保存
  - J-Quants API クライアント（ページネーション・トークン自動リフレッシュ・レート制限・リトライ）
  - 株価（raw_prices）・財務（raw_financials）・マーケットカレンダーの取得/保存
  - RSS フィードからのニュース収集と記事→銘柄紐付け
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
- ETL / パイプライン
  - 差分更新（最終取得日に基づく差分フェッチ + バックフィル）
  - 日次 ETL（calendar → prices → financials → 品質チェック）
- リサーチ（research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ
- 特徴量・戦略（strategy）
  - 特徴量の正規化・ユニバースフィルタ適用（build_features）
  - 正規化済み特徴量 + AI スコアを統合して売買シグナルを生成（generate_signals）
  - BUY / SELL の閾値・重み・Bear レジーム抑制・エグジット判定（ストップロス等）
- ユーティリティ
  - クロスセクション Z スコア正規化（data.stats）
  - マーケットカレンダー管理（営業日判定 / next/prev_trading_day 取得）
  - 監査ログ（audit）: シグナル→発注→約定のトレース用スキーマ設計

セットアップ手順（開発ローカル向け）
1. Python 環境
   - 推奨: Python 3.10+（typing 表記等を利用しています）
   - 仮想環境を作成・有効化:
     ```sh
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows (PowerShell 等)
     ```

2. 必要パッケージのインストール（最低限）
   - 必須（本リポジトリの機能を使うのに最低必要なもの）:
     ```sh
     pip install duckdb defusedxml
     ```
   - 実運用では HTTP リクエストやロギングに追加依存を入れることがあります。requirements.txt があればそれを使用してください。

3. 環境変数（.env）
   - プロジェクトルートに .env / .env.local を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD：kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN：Slack 通知に使う Bot トークン（必須）
     - SLACK_CHANNEL_ID：通知先チャンネル ID（必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env の読み込みを無効化）
     - DUCKDB_PATH（DuckDB のパス、デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（モニタリング用 SQLite、デフォルト: data/monitoring.db）
   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

使い方（主要なワークフロー例）
- DuckDB スキーマ初期化
  ```py
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # デフォルト: data/kabusys.duckdb
  ```

- 日次 ETL 実行（J-Quants からデータ取得して保存）
  ```py
  from kabusys.data.pipeline import run_daily_etl
  # conn は init_schema の戻り値
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 特徴量の構築（指定日）
  ```py
  from kabusys.strategy import build_features
  import datetime

  count = build_features(conn, datetime.date(2025, 1, 10))
  print(f"features upserted: {count}")
  ```

- シグナル生成（指定日）
  ```py
  from kabusys.strategy import generate_signals
  import datetime

  total_signals = generate_signals(conn, datetime.date(2025, 1, 10))
  print(f"signals written: {total_signals}")
  ```

- ニュース収集ジョブ（RSS から raw_news 保存 / 銘柄紐付け）
  ```py
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # known_codes: 既知の銘柄コードセット (例: {"7203","6758",...})
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
  print(results)
  ```

- カレンダー更新ジョブ（夜間）
  ```py
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  ```

- テスト / 開発時のヒント
  - DuckDB のインメモリを使う:
    ```py
    from kabusys.data.schema import init_schema
    conn = init_schema(":memory:")
    ```
  - 自動 .env ロードを無効化するには環境変数をセット:
    ```sh
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理（自動 .env ロード、必須キー取得）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch/save 関連）
    - news_collector.py       — RSS 取得・前処理・DB 保存
    - schema.py               — DuckDB スキーマ定義・初期化
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - pipeline.py             — ETL パイプライン（差分取得・daily_etl 等）
    - calendar_management.py  — market_calendar 管理・営業日ロジック
    - features.py             — features などの公開インターフェース
    - audit.py                — 監査ログ用スキーマ DDL
    - (その他: quality, audit の続き等が想定される)
  - research/
    - __init__.py
    - factor_research.py      — momentum/volatility/value ファクター計算
    - feature_exploration.py  — forward returns, IC, factor_summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py  — build_features（ユニバースフィルタ / 正規化 / UPSERT）
    - signal_generator.py     — generate_signals（スコア計算 / BUY/SELL 判定）
  - execution/                — 発注周り（ディレクトリ存在、実装は別）
  - monitoring/               — 監視・モニタリング（ディレクトリ存在、実装は別）

補足・設計上のポイント
- 冪等性:
  - DB への保存は原則 ON CONFLICT による UPSERT / DO NOTHING を使用し冪等性を担保しています。
  - ETL / feature / signal の各処理は「日付単位で削除→挿入」することで日単位の置換（idempotent）を実現しています。
- ルックアヘッドバイアス対策:
  - 戦略・研究用の計算は target_date 時点の情報のみを用いる設計です（future 情報を参照しない）。
  - 外部データの fetched_at を UTC で記録し、いつデータがシステムに到達したかトレース可能にしています。
- ネットワーク & セキュリティ:
  - J-Quants クライアントはレート制御・リトライ・401 の自動トークン再取得を実装。
  - RSS 取得では SSRF 対策（リダイレクト先検査・プライベート IP 拒否）や XML 攻撃対策（defusedxml）を組み込んでいます。

よくある質問
- Q: どの DB を使えばいいですか？
  - A: 時系列マーケットデータや大規模な分析は DuckDB（本実装）が想定されています。監視や軽量なメタデータには SQLite を併用できます（設定可能）。
- Q: 本番運用での注意点は？
  - A: KABUSYS_ENV を "live" に設定するとライブ運用用のフラグが有効になります。実際に発注する execution 層は十分なテストとリスク管理が必要です（本リポジトリの execution ディレクトリを参照）。

貢献・拡張
- 新しいフィードの追加やファクターの追加、execution 層のブローカー統合など拡張が容易なモジュール構成です。Pull Request や Issue を歓迎します。

以上が README の概要です。必要であれば「実行例（スクリプト）」「.env.example の完全版」「API レート / リトライの細かいパラメータ」「DB スキーマの ER 図」などを追記できます。どれを優先して追加しますか？