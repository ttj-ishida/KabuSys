# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（ミニマル実装）。  
データ取得・ETL、特徴量生成、シグナル生成、ニュース収集、監査スキーマなどを含むモジュール化されたコードベースです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引のための基盤ライブラリです。主に以下を提供します。

- J-Quants API からの市場データ・財務データ・カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution 層）のスキーマ定義と初期化
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算・特徴量正規化（research）
- 戦略向けの特徴量合成（feature_engineering）とシグナル生成（signal_generator）
- RSS ベースのニュース収集と銘柄紐付け（news_collector）
- マーケットカレンダー管理（calendar_management）
- 監査ログ（audit）・発注/約定/ポジション管理用テーブル群

設計思想として「ルックアヘッドバイアスの排除」「冪等性（DB保存はON CONFLICT等）」「外部APIへの過度な依存を避ける」「テスト容易性」を重視しています。

---

## 主な機能一覧

- データ取得
  - J-Quants クライアント（jquants_client）
    - 株価（日足）、財務データ、マーケットカレンダーの取得
    - レートリミット管理、リトライ、トークン自動更新
- データ格納・スキーマ
  - DuckDB 用スキーマ定義と初期化（data.schema.init_schema）
  - Raw / Processed / Feature / Execution 層のテーブルを定義
- ETL パイプライン
  - 日次 ETL（data.pipeline.run_daily_etl）
  - 差分取得（価格・財務）、カレンダー先読み、品質チェック
- 研究（research）
  - momentum / volatility / value 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Spearman）計算等（research.feature_exploration）
- 戦略（strategy）
  - 特徴量構築（strategy.feature_engineering.build_features）
  - シグナル生成（strategy.signal_generator.generate_signals）
- ニュース収集
  - RSS 取得・正規化・DB保存（data.news_collector.run_news_collection）
  - 銘柄コード抽出と紐付け
- カレンダ管理
  - 営業日判定、次/前営業日、カレンダー更新ジョブ（data.calendar_management）
- 監査ログ
  - signal_events / order_requests / executions 等の監査テーブル（data.audit）

---

## セットアップ手順

以下は開発・実行環境の基本手順例です。実運用時は適宜追加の依存やセキュリティ設定を行ってください。

1. Python 環境
   - 推奨: Python 3.10 以上（型注釈に union の | を使用）
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール
   - 必要なパッケージ（例）
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （必要に応じて lint/test ライブラリ等を追加）
4. 環境変数設定
   - .env をプロジェクトルートに置くと自動で読み込まれます（読み込み無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注連携時）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot Token
     - SLACK_CHANNEL_ID — 通知先チャンネル ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — データベースファイル（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. データベース初期化
   - DuckDB のスキーマを作成します（初回のみ）。
   - Python REPL やスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ':memory:' も可
     ```

---

## 使い方（簡単な例）

以下は代表的なワークフローの例です。

1. DuckDB スキーマ初期化（既に初期化済みであればスキップ可）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL を実行（市場カレンダー・株価・財務を差分取得）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   res = run_daily_etl(conn)  # target_date を指定可能
   print(res.to_dict())
   ```

3. 特徴量（features）を構築
   ```python
   from kabusys.strategy import build_features
   from datetime import date
   n = build_features(conn, date(2024, 1, 10))
   print(f"features upserted: {n}")
   ```

4. シグナル生成（BUY/SELL を signals テーブルへ保存）
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date
   total = generate_signals(conn, date(2024, 1, 10))
   print(f"signals generated: {total}")
   ```

5. ニュース収集と銘柄紐付け
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

6. カレンダー更新ジョブ（夜間バッチ想定）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"calendar rows saved: {saved}")
   ```

注意点:
- すべての ETL / 生成処理は DuckDB 接続（conn）を直接受け取ります。
- 各処理は冪等に実装されており、同一日付分は日付単位で置換（DELETE + INSERT）します。
- 実際の発注（ブローカー連携）は execution 層で実装予定（現状はテーブル定義と監査周りのロジック中心）。

---

## よく使う API 一覧（抜粋）

- kabusys.config.settings — 環境変数から設定を取得
- data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- data.schema.get_connection(db_path) — 既存DBへ接続
- data.jquants_client.fetch_daily_quotes(...) / save_daily_quotes(...) — API取得・保存
- data.pipeline.run_daily_etl(...) — 日次 ETL（市場カレンダー → 価格 → 財務 → 品質チェック）
- data.news_collector.run_news_collection(...) — RSS 収集 & 保存 & 銘柄紐付け
- strategy.build_features(conn, target_date) — features テーブル構築
- strategy.generate_signals(conn, target_date, threshold, weights) — signals 生成
- research.calc_momentum / calc_volatility / calc_value — 研究用ファクター計算
- data.calendar_management.is_trading_day / next_trading_day / prev_trading_day

---

## ディレクトリ構成

主なファイル・モジュール構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - (その他: quality 等の補助モジュールが想定)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  (モジュールの雛形/監視用実装を想定)

各モジュールの責務はファイル冒頭の docstring に記載されています。特に data/schema.py にスキーマ定義がまとまっており、全テーブル構造・インデックス・DDL順序が定義されています。

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | ...) — default: INFO

自動 .env ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 開発・貢献

- コードはモジュール単位で分割されており、関数に対して依存注入（例: id_token の注入）が可能なため単体テストが書きやすくなっています。
- DB 関連は DuckDB を利用しており、テストでは ':memory:' を使って高速な検証が可能です。
- 外部ネットワークアクセス部分（HTTP）をモックすることでエンドツーエンドテストの再現が可能です。

---

## 免責 / ライセンス

このリポジトリはサンプル実装です。実際の運用にあたってはリスク管理・法規制・証券会社 API 仕様（kabuステーション等）の確認・テストを必ず行ってください。ライセンス情報はリポジトリに合わせて追記してください。

---

必要であれば README に「運用時の Cron 例」「データバックアップ方針」「監視・アラート設定」「CI/CD 簡易手順」などを追加できます。どの情報を追記したいか教えてください。