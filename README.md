# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのためのライブラリ群です。  
データ収集（J-Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、監査・実行レイヤの管理まで含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスの排除（target_date 時点のデータのみ使用）
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全）
- 外部依存は最小化（DuckDB を中心に標準ライブラリで実装）
- 運用モード（development / paper_trading / live）を想定した設定管理

バージョン: 0.1.0

---

## 機能一覧

主要モジュールと提供機能（抜粋）

- kabusys.config
  - .env / .env.local から環境変数を自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL 管理

- kabusys.data
  - jquants_client: J-Quants API クライアント（ページネーション、リトライ、トークン自動更新、レート制御）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution レイヤ）
  - pipeline: 日次 ETL（市場カレンダー・株価・財務の差分取得＋品質チェック）
  - news_collector: RSS からニュース収集、前処理、DB 保存、銘柄抽出（SSRF 対策、サイズ制限）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats / features: Zスコア正規化等の統計ユーティリティ

- kabusys.research
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）やファクター統計

- kabusys.strategy
  - feature_engineering.build_features: research モジュールの生ファクターを正規化し features テーブルへ保存
  - signal_generator.generate_signals: features + ai_scores を統合して BUY/SELL シグナルを生成して signals テーブルへ書込

- kabusys.data.audit
  - 監査ログ（signal_events / order_requests / executions など）のスキーマと管理

（execution / monitoring 含む外部システム連携は個別実装を想定）

---

## セットアップ手順

前提
- Python 3.9+（typing の | 型などを使用）
- DuckDB
- ネットワークアクセス（J-Quants API、RSS 等）

1. リポジトリをクローン、インストール（開発用）
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   pip install -e .
   ```
   または依存パッケージを個別にインストール:
   ```bash
   pip install duckdb defusedxml
   ```

2. 環境変数の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を作成すると自動で読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な必須環境変数:
   - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API パスワード（execution 層で使用）
   - SLACK_BOT_TOKEN — Slack 通知用トークン
   - SLACK_CHANNEL_ID — Slack 通知先チャネルID

   任意 / デフォルト:
   - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）

   .env の例（抜粋）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマ初期化
   Python REPL またはスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   これにより必要なテーブルとインデックスが作成されます。

---

## 使い方（代表的な操作例）

以下は主なユースケースの短いサンプルです。すべて DuckDB 接続（kabusys.data.schema.get_connection / init_schema）経由で実行します。

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量の構築（strategy 層へ保存）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")  # 既に init_schema 済みを想定
  n = build_features(conn, target_date=date(2025, 1, 20))
  print(f"build_features: {n} 銘柄")
  ```

- シグナル生成（features, ai_scores, positions を参照して signals に書込）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025,1,20))
  print(f"generate_signals: total={total}")
  ```

- ニュース収集ジョブ（RSS -> raw_news、news_symbols）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄セットを準備
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- J-Quants からの株価フェッチ（直接呼出し）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  from kabusys.config import settings
  data = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

注意点:
- run_daily_etl など多くの処理は冪等に設計されています（同一日付の上書きが安全）。
- AI スコアなど外部モデルからの入力は ai_scores テーブルに事前登録しておくと generate_signals が利用します。
- signal の実際の発注は execution 層（証券会社 API 連携）を別途実装して下さい。本パッケージは signals / signal_queue / orders / trades / positions の管理とスキーマを提供します。

---

## 設定の詳細

- 自動 .env ロード:
  - パッケージは import 時にプロジェクトルート（.git または pyproject.toml）から `.env` / `.env.local` を自動で読み込みます。
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

- 必須環境変数取得:
  - settings.jquants_refresh_token -> JQUANTS_REFRESH_TOKEN
  - settings.kabu_api_password -> KABU_API_PASSWORD
  - settings.slack_bot_token -> SLACK_BOT_TOKEN
  - settings.slack_channel_id -> SLACK_CHANNEL_ID

- システム設定:
  - KABUSYS_ENV: "development", "paper_trading", "live" のいずれか。無効値は ValueError。
  - LOG_LEVEL: "DEBUG","INFO","WARNING","ERROR","CRITICAL"。無効値は ValueError。
  - DUCKDB_PATH / SQLITE_PATH: デフォルトは data/ 配下に置かれます。

---

## ディレクトリ構成

以下は主要なファイル/ディレクトリの抜粋（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存ロジック）
    - schema.py               — DuckDB スキーマ定義と初期化
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - news_collector.py       — RSS 収集・保存（SSRF 対策・前処理）
    - calendar_management.py  — 営業日管理・カレンダー更新ジョブ
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - features.py             — features の公開インターフェース（再エクスポート）
    - audit.py                — 監査ログスキーマ（signal_events 等）
    - ...                     — quality, other utilities（存在想定）
  - research/
    - __init__.py
    - factor_research.py      — momentum / volatility / value の計算
    - feature_exploration.py  — forward returns / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py  — build_features（正規化・ユニバースフィルタ）
    - signal_generator.py     — generate_signals（final_score 計算・BUY/SELL 生成）
  - execution/                — 発注・ブローカー連携（実装の入口）
  - monitoring/               — 監視・アラート（sqlite 等への蓄積想定）

---

## 開発 / 運用上の注意

- DuckDB はファイルロックや並列アクセスに注意してください。複数プロセスから同一 DB を操作する場合の設計を検討してください。
- ニュース収集は外部 RSS に依存するため、タイムアウトやサイズ上限（デフォルト 10MB）を設定しています。fetch_rss のログを確認して運用してください。
- J-Quants API はレート制限（120 req/min）に合わせた RateLimiter を組み込んでいますが、大量データ取得や複数インスタンス運用時は更にレート管理が必要です。
- シグナル生成は features / ai_scores / positions の状態に依存します。テスト環境 / 本番環境での振る舞いを切り替えるには KABUSYS_ENV を利用してください（is_live / is_paper / is_dev の判定が可能）。

---

## ライセンス・貢献

（リポジトリに LICENSE があればここに記載してください。）

バグ報告や機能提案は Issue を通じてお願いします。プルリクエスト歓迎です。

---

本 README はコードベースの主要 API と運用手順を簡潔にまとめたものです。詳細な設計（DataPlatform.md, StrategyModel.md 等）や運用手順は別ドキュメントを参照してください。