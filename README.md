# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（部分実装）。  
このリポジトリはデータ取得（J‑Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどの主要コンポーネントを提供します。

主な想定用途：研究環境でのファクター開発 → DuckDB でのデータ基盤構築 → 戦略特徴量生成 → シグナル生成 → （別モジュールで）発注フローへ連携

---

## 機能一覧

- 環境変数 / 設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（無効化可能）
  - 必須設定の取得と検証

- Data（データ層）
  - J‑Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - DuckDB スキーマの定義と初期化
  - ETL パイプライン（差分更新・バックフィル・品質チェック呼び出し）
  - ニュース収集（RSS → raw_news、SSRF／サイズ／XML攻撃対策）
  - マーケットカレンダー管理（営業日判定/next/prev/get_trading_days）
  - 汎用統計ユーティリティ（Zスコア正規化 等）

- Research（研究用ユーティリティ）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ

- Strategy（戦略層）
  - 特徴量エンジニアリング（build_features：ファクター統合・ユニバースフィルタ・正規化・DB保存）
  - シグナル生成（generate_signals：最終スコア計算、BUY/SELL 生成、エグジット判定）

- Audit / Execution（監査・発注層）
  - 監査ログ用 DDL（signal_events, order_requests, executions 等）を含むスキーマ定義（DuckDB）

---

## 前提 / 必要なもの

- Python 3.10+
- 必須ライブラリ（最低限）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

（プロジェクトで別途 requirements.txt / poetry を用意することを推奨します）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   ```

3. 環境変数設定
   プロジェクトルートに `.env`（または `.env.local`）を配置します。自動ロードはデフォルトで有効です（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   最低限設定が必要な変数（例）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API（発注を行う場合）
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack（通知用）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789

   # DB パス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
   - 必須の env は Settings プロパティで明確に取得され、未設定だと ValueError を投げます。

4. DuckDB スキーマ初期化（例）
   以下は Python でスキーマを初期化する簡単な例です：
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

---

## 使い方（代表的な操作例）

以下は代表的なワークフロー例です。各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

- データベース初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL（市場カレンダー、株価、財務データの差分取得）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）を作成
  ```python
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 31))
  print(f"Built features for {n} symbols")
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 1, 31))
  print(f"Signals generated: {total}")
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット（例）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"market_calendar saved: {saved}")
  ```

注意:
- 上記のサンプルは同期的な呼び出しです。実運用ではスケジューラ（cron / Airflow など）から実行する想定です。
- 発注（kabu API）との接続部分は execution パッケージに依存する予定ですが、今回提示されたコード群では発注実装は含まれていません（スキーマのみ含む）。

---

## 環境変数（主なキー）

- JQUANTS_REFRESH_TOKEN: J‑Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注機能利用時）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視DB）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env をロードする機能を無効化します（テスト用途等）

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（version）
- config.py — 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py — J‑Quants API クライアント（取得・保存ロジック）
  - news_collector.py — RSS ニュース収集・保存
  - schema.py — DuckDB スキーマ定義と初期化
  - stats.py — 統計ユーティリティ（zscore）
  - pipeline.py — ETL（run_daily_etl、run_prices_etl 等）
  - calendar_management.py — マーケットカレンダー管理・バッチ
  - features.py — data.stats の再エクスポート
  - audit.py — 監査ログ用 DDL（signal_events, order_requests, executions）
- research/
  - __init__.py
  - factor_research.py — momentum/volatility/value ファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py — build_features（正規化・ユニバースフィルタ）
  - signal_generator.py — generate_signals（最終スコア計算・BUY/SELL）
- execution/ — 発注層（今回のコードでは空ディレクトリ）
- monitoring/ — 監視系（今回のコードでは SQLite 接続想定の設定等）

---

## 開発・拡張メモ

- 型アノテーションとロギングを重視した実装で、テスト容易性を考慮しています。
- 外部 API の扱い（J‑Quants）ではレート制御やトークン自動更新、リトライを実装済みです。運用時は API 制限や料金ポリシーに注意してください。
- DuckDB をデータ層に採用しているため、軽量でローカル分析が行いやすい設計です。大規模運用では別の永続層／データレイクと連携することを検討してください。
- ニュース収集は RSS ベース。将来的に Web スクレイピングや外部 NLP サービス連携を追加できますが、セキュリティ（SSRF 等）への配慮をそのまま維持してください。

---

必要であれば、README に以下を追加できます：
- より詳しい実行例（cron / systemd / Airflow）
- 開発用の docker-compose / Makefile サンプル
- CI / テスト方法（pytest ベースの例）
- API 使用に必要な J‑Quants の取得手順

どの追加情報が必要か教えてください。