# KabuSys

日本株向けの自動売買システム基盤ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル算出、ニュース収集、DuckDBベースのスキーマ／監査を含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の機能を備えた、研究〜運用までを想定した日本株アルゴリズム取引の基盤ライブラリです。

主な設計方針：
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみを使用）
- DuckDB をデータ格納基盤に採用（ローカルファイル / in-memory をサポート）
- API 呼び出しに対してレート制御・リトライ・トークンリフレッシュを備えたクライアント
- ETL・品質チェック・特徴量生成・シグナル算出は冪等（idempotent）に設計
- ニュース収集は SSRF や XML 攻撃対策を実装

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env と OS 環境変数の自動ロード（必要に応じて無効化可能）
  - 必須設定値の取得ラッパー

- データ取得（J-Quants）
  - 株価日足、財務データ、JPX カレンダーの取得（ページネーション対応）
  - レート制御、リトライ、401 の自動トークンリフレッシュ
  - DuckDB への冪等保存（ON CONFLICT を利用）

- データベーススキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - index 作成、init_schema による初期化

- ETL パイプライン
  - 日次差分 ETL（市場カレンダー、株価、財務データ）
  - バックフィル / 品質チェックフック
  - run_daily_etl により一括実行

- 研究（research）
  - モメンタム / ボラティリティ / バリューといったファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- 特徴量生成（strategy）
  - 複数ファクターを統合して Z スコア正規化 / クリップし features テーブルへ保存

- シグナル生成（strategy）
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム判定、BUY/SELL シグナル生成、SELL はエグジット条件を評価

- ニュース収集
  - RSS フィード取得、テキスト前処理、記事IDの生成、raw_news への冪等保存
  - 銘柄コード抽出（4桁コード）、news_symbols への紐付け
  - SSRF/サイズ制限/defusedxml による安全対策

- カレンダー管理
  - JPX カレンダー更新ジョブ、営業日判定ユーティリティ（next/prev/get_trading_days 等）

- 監査ログ（audit）
  - signal → order_request → execution のトレーサビリティを保持するスキーマ

---

## セットアップ手順

前提:
- Python 3.9+（型注釈の Union 表現等に依存）
- DuckDB がインストールされること（pip 経由でも可）
- ネットワークで J-Quants API にアクセス可能であること（トークン必要）

1. リポジトリをクローン / パッケージをインストール（例: 開発環境）
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 必要な環境変数を設定（.env をルートに置くか OS 環境変数を設定）
   - 必須（Settings クラス参照）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まない

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマの初期化
   Python コンソールやスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" でメモリ DB 可
   ```

4. 必要依存の追加パッケージ
   - defusedxml（RSS パーシングの安全化）
   - duckdb
   （パッケージ一覧は pyproject.toml / setup.cfg を参照）

---

## 使い方（主要 API と実行例）

以下はライブラリを使った基本的な操作例です。

- DuckDB 接続の初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9432"}  # など
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from kabusys.research import calc_momentum
  from datetime import date
  records = calc_momentum(conn, date(2024, 1, 31))
  ```

- 特徴量ビルド（features テーブルへ保存）
  ```python
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, date(2024, 1, 31))
  print(f"upserted {n} features")
  ```

- シグナル生成（signals テーブルへ保存）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2024, 1, 31), threshold=0.6)
  print(f"generated {total} signals")
  ```

- J-Quants からデータ取得（低レベル）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  rows = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, rows)
  ```

- 環境設定の取得（settings）
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path  # pathlib.Path オブジェクト
  ```

注意点:
- generate_signals / build_features は target_date を基準にデータを参照します。運用では market_calendar を先に更新し、target_date を営業日に調整することを推奨します（pipeline.run_daily_etl はこの順序を実装しています）。
- ETL / API 呼び出しはネットワーク・API レート制限に依存します。J-Quants の仕様（120 req/min）に従って実装済みです。

---

## ディレクトリ構成

主要なモジュールとファイル一覧（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定読み込み
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - news_collector.py            — RSS 取得・記事保存・銘柄紐付け
    - schema.py                    — DuckDB スキーマ定義 & init_schema
    - stats.py                     — zscore_normalize 等統計ユーティリティ
    - pipeline.py                  — ETL パイプライン（run_daily_etl など）
    - calendar_management.py       — カレンダー更新 / 営業日判定
    - features.py                  — data.stats の再エクスポート
    - audit.py                     — 監査ログスキーマ
    - (その他 quality 等 モジュール想定)
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py       — features テーブル構築
    - signal_generator.py          — final_score 計算と BUY/SELL シグナル生成
  - execution/                     — 発注 / execution 層（パッケージ用意）
  - monitoring/                    — 監視 / モニタリング用（パッケージ用意）

（上記は主要ファイルを抜粋したものです。詳細はソースツリーを参照してください。）

---

## 環境変数 / 設定一覧（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development, paper_trading, live）
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動で .env を読み込まない

---

## 運用上の注意

- 本ライブラリは「戦略ロジック」と「発注実行」を分離しています。strategy 層は signals テーブルを生成しますが、実際の発注は execution 層（発注 API への接続）で別途実装・統合してください。
- DB スキーマは冪等性を意識しており ON CONFLICT を使用していますが、トランザクションとエラーハンドリングによりデータ整合性を保つために、init_schema / 各保存関数の戻り値を確認して運用してください。
- ニュース収集では外部 RSS を扱うため SSRF や大容量レスポンスの防御策を実装しています。それでも未知のケースがあるため、収集運用時はログを監視してください。
- J-Quants の API 権限・利用規約、証券会社 API（kabuステーション等）の利用ルールを遵守してください。実運用（特に live 環境）では十分な検証とリスク管理を行ってください。

---

必要があれば、README に含める実行スクリプト例（systemd タイマー / cron / Airflow ジョブのサンプル）や、品質チェックの使い方、テスト方法、CI 設定のテンプレートも追加します。どの項目を追加したいか教えてください。