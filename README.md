# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群。データ取得（J‑Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・スキーマ管理などを含むモジュール群を提供します。

バージョン: 0.1.0

## プロジェクト概要

KabuSys は以下のレイヤーを備えた日本株自動売買システムの基盤ライブラリです。

- Data Platform（J‑Quants からのデータ取得、DuckDB スキーマ、ETL パイプライン）
- Research（ファクター計算・特徴量探索）
- Strategy（特徴量正規化 → シグナル生成）
- Execution / Audit（発注・約定・ポジション管理のためのスキーマとユーティリティ）
- News Collector（RSS からのニュース収集と銘柄抽出）

設計上の特徴:
- DuckDB をデータストアとして使用（ローカルファイルまたは :memory:）
- 冪等（idempotent）な保存ロジック（ON CONFLICT / INSERT ... DO UPDATE 等）
- ルックアヘッドバイアス回避（target_date 時点のデータのみを利用）
- API レート制御・リトライ・トークン自動リフレッシュ（J‑Quants クライアント）
- セキュアな RSS パース（SSRF 対策、defusedxml 使用）

## 主な機能一覧

- DuckDB スキーマ定義と初期化（kabusys.data.schema.init_schema）
- J‑Quants API クライアント（株価・財務・カレンダーの取得、保存）
  - レートリミット制御、リトライ、トークン自動リフレッシュ
- ETL パイプライン（差分取得・保存・品質チェック）
  - run_daily_etl（市場カレンダー → 株価 → 財務 → 品質チェック）
- ニュース収集（RSS 取得、記事前処理、銘柄抽出、DB 保存）
- ファクター計算（momentum / volatility / value）
- 特徴量生成（クロスセクション Z スコア正規化、ユニバースフィルタ）
- シグナル生成（ファクター + AI スコア統合 → BUY/SELL シグナル生成）
- カレンダー管理ユーティリティ（営業日判定、前後営業日計算）
- 監査ログ / 発注監査テーブル群の初期化

## 必要条件 / 推奨環境

- Python 3.10 以上（型ヒントに | 演算子を使用しているため）
- 必要なパッケージ（一例）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J‑Quants API、RSS ソースなど）

（プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。）

## 環境変数（設定）

kabusys は .env ファイルまたは環境変数から設定を読み込みます（自動ロードあり。プロジェクトルートの .env / .env.local を探索）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意/デフォルト値:
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

サンプル .env（例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

## セットアップ手順（ローカル）

1. Python 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージのインストール（プロジェクトに requirements ファイルがあればそれを使用）
   例:
   ```
   pip install duckdb defusedxml
   ```

3. リポジトリをローカルに配置し、必要な環境変数を設定（.env をプロジェクトルートに置くのが簡単です）。

4. DuckDB スキーマ初期化（Python REPL またはスクリプトで実行）:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")   # デフォルトパスと同じ
   ```

   またはインメモリでテスト:
   ```python
   conn = init_schema(":memory:")
   ```

## 使い方（主な API と実行例）

以下は代表的な利用例です。実際のバッチジョブやスケジューラ（cron / Airflow / systemd timer 等）から呼び出して利用します。

- DuckDB 接続作成とスキーマ初期化
  ```python
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")   # 初回のみ
  # 2回目以降は get_connection を使って既存 DB に接続
  conn = get_connection("data/kabusys.duckdb")
  ```

- 日次 ETL（市場カレンダー、株価、財務の差分取得）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)   # target_date を指定しなければ今日
  print(result.to_dict())
  ```

- 特徴量作成（features テーブルへ書込）
  ```python
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, target_date=date(2025, 3, 1))
  print(f"upserted features: {n}")
  ```

- シグナル生成（signals テーブルへ書込）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, target_date=date(2025, 3, 1))
  print(f"signals generated: {total}")
  ```

- ニュース収集（RSS 取得 → raw_news / news_symbols へ保存）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  known_codes = {"7203", "6758", "6501"}  # 有効な銘柄コード集合（DB から取得するのが実運用向け）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar entries saved: {saved}")
  ```

## 推奨ワークフロー（日次バッチの例）

1. schema 初期化（初回のみ）
2. calendar_update_job（先にカレンダーを取得して営業日判定に利用）
3. run_daily_etl（差分 ETL を実行）
4. build_features（target_date に対する特徴量を作成）
5. generate_signals（features と ai_scores を用いてシグナルを生成）
6. execution 層へ受渡し / 監査ログ出力 / Slack 通知 など

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュールは src/kabusys 以下に配置されています。主要ファイルを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py — J‑Quants API クライアント（取得 + 保存）
    - news_collector.py — RSS ニュース収集・前処理・保存
    - schema.py — DuckDB スキーマ定義 / init_schema / get_connection
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py — 市場カレンダー管理
    - audit.py — 監査ログテーブル DDL
    - features.py — data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — IC / 将来リターン / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — 特徴量正規化・ユニバースフィルタ・features への保存
    - signal_generator.py — final_score 計算・BUY/SELL の生成・signals への保存
  - execution/  — 発注関連（パッケージ化済みだが詳細は実運用に合わせて実装）
  - monitoring/  — 監視・メトリクス系（SQLite など）

（詳細は各モジュールの docstring を参照してください。README は要点のまとめです。）

## ロギングと実行モード

- 設定: KABUSYS_ENV = development / paper_trading / live
  - settings.is_dev / is_paper / is_live のフラグが利用可能
- ログレベルは LOG_LEVEL で設定（デフォルト INFO）

## セキュリティ／運用ノート

- J‑Quants のアクセストークンは安全に管理してください（環境変数またはシークレットマネージャを推奨）
- RSS フィード取得では SSRF 対策・応答サイズ制限・defusedxml を使用して安全性を高めていますが、外部フィードは常に潜在的リスクがあります
- 発注ロジック（execution 層）は実運用前にペーパートレードで十分に検証してください

## 貢献 / 開発のヒント

- 単体テストや統合テストでは環境変数自動ロードを無効化できます:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB の :memory: を使えば副作用なしのテストができます。
- jquants_client のネットワーク部分は id_token 注入やモジュール関数をモックすることでテストできます。

---

詳細は各モジュールの docstring（ソース内コメント）を参照してください。必要であれば README にジョブスケジューリング例（systemd / cron / Airflow）や運用チェックリストを追加できます。追加希望があれば教えてください。