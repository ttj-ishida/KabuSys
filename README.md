# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL、ファクター計算、特徴量作成、シグナル生成、ニュース収集、監査ログなどを備えた、研究→運用を想定したモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアス回避（各処理は target_date 時点のデータのみ使用）
- 冪等性（DB への保存は ON CONFLICT 等で重複を排除）
- 安全性（API レート制御、XML/SSRF 対策、トランザクションでの原子性）
- テスト容易性（id_token 注入や :memory: DuckDB 対応）

バージョン: 0.1.0

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（レート制御・リトライ・自動トークン更新）
  - 日足・財務（四半期）・市場カレンダーの差分取得と保存
  - DuckDB スキーマの初期化（DataLayer の DDL 一括作成）
  - ETL パイプライン（run_daily_etl）で市場カレンダー → 株価 → 財務 → 品質チェックを実行

- データ整備 / ユーティリティ
  - raw → processed 層のテーブル定義（prices_daily, fundamentals, market_calendar 等）
  - 統計ユーティリティ（クロスセクション Z スコア正規化など）
  - ニュース収集（RSS 取得、前処理、ID 正規化、銘柄抽出、DB 保存）
  - マーケットカレンダー管理（営業日判定、前後営業日の計算、夜間更新ジョブ）

- 研究・ファクター計算
  - Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials ベース）
  - 将来リターン・IC（Spearman）・ファクターサマリー等の探索ツール

- 戦略層
  - 特徴量エンジニアリング（生ファクターの正規化・ユニバースフィルタ・features テーブル保存）
  - シグナル生成（features + ai_scores を統合して final_score を算出し BUY / SELL を signals テーブルへ保存）
  - エグジット判定（ストップロス等のルール実装）

- 監査 / 実行（骨格）
  - 監査テーブル群（signal_events / order_requests / executions 等）の DDL（トレーサビリティを考慮）

---

## 必要な環境変数（主なもの）

以下は本プロジェクトで利用している主要な環境変数です。`.env` に記載してプロジェクトルートに置くと、自動的に読み込まれます（ただしテスト等で無効化可能）。

必須：
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注層使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知を行う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルト有り：
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)。デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG / INFO / WARNING / ERROR / CRITICAL)。デフォルト: INFO
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB 等、デフォルト: data/monitoring.db）

自動ロードを無効にする:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env のパースは Bash 風の export/クォートやコメントをある程度サポートします。

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.10+）
2. 依存ライブラリをインストール（例: duckdb 等。requirements.txt がある場合はそれを使用）
   - 例（pip）:
     ```
     pip install duckdb defusedxml
     ```
   - パッケージとしてローカル開発インストール:
     ```
     pip install -e .
     ```

3. プロジェクトルートに `.env` を作成（`.env.example` を参考に必須キーを設定）
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

4. DuckDB スキーマを初期化
   - Python で実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
     conn.close()
     ```
   - メモリ DB を使う場合:
     ```python
     conn = init_schema(":memory:")
     ```

---

## 使い方（主要な操作例）

以下はライブラリを使った基本的なワークフロー例です。すべて Python スクリプトや REPL から実行できます。

- DuckDB 接続 / スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")  # 初期化して接続を返す
  # 既存 DB に接続する場合
  # conn = get_connection("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しなければ今日
  print(result.to_dict())
  ```

- 特徴量の構築（features テーブルへ保存）
  ```python
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, target_date=date(2025, 1, 31))
  print(f"features upserted: {n}")
  ```

- シグナル生成（signals テーブルへ保存）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, target_date=date(2025, 1, 31), threshold=0.6)
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → news_symbols 紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  known_codes = {"7203", "6758", ...}  # 有効銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- J-Quants から日足データを直接取得して保存
  ```python
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

---

## 重要な注意点 / 設計メモ

- ルックアヘッド防止:
  - ファクター計算・特徴量構築・シグナル生成は target_date 時点までのデータのみを使用する設計です。
  - また、J-Quants 取得データは fetched_at を UTC で保存し「いつデータが取得可能になったか」を追跡できます。

- 冪等性:
  - raw テーブルへの保存は ON CONFLICT DO UPDATE / DO NOTHING を多用し再実行可能にしています。
  - features / signals の書き込みは日付単位で DELETE → INSERT を行い「日次置換（idempotent）」を実現します（トランザクションで原子性を確保）。

- 外部接続の安全性:
  - J-Quants クライアントは 120 req/min のレート制御、リトライ（指数バックオフ）、401 トークンリフレッシュを実装しています。
  - ニュース収集は XML パースに defusedxml、SSRF 対策、最大レスポンスサイズ制限、リダイレクト検査などを実装しています。

- DB 初期化と運用:
  - init_schema() は必要な DDL を全て作成します。初回はこれを必ず実行してください。
  - DuckDB パスは環境変数 DUCKDB_PATH で指定できます。":memory:" を利用して単体テスト可能です。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールの構成（src/kabusys 以下）です。実際にはさらに細かいファイルが含まれますが、代表的なものを示します。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + 保存関数
    - schema.py                     — DuckDB スキーマ定義 / init_schema
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - news_collector.py             — RSS 収集・保存
    - calendar_management.py        — マーケットカレンダー管理
    - stats.py                      — zscore_normalize 等の統計ユーティリティ
    - features.py                   — data 側の特徴量再エクスポート
    - audit.py                      — 監査ログ DDL（signal_events / order_requests / executions 等）
    - quality.py?                   — 品質チェック（コードベースに依存: pipeline から呼ばれる想定）
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Volatility / Value の計算
    - feature_exploration.py        — 将来リターン / IC / サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py        — features を作る処理（正規化・ユニバースフィルタ）
    - signal_generator.py           — final_score 計算と signals 生成
  - execution/
    - __init__.py                    — 実行層（発注・ブローカー連携）は拡張領域
  - monitoring/                      — 監視用モジュール（存在想定）

（注）README に記載したファイル一覧はこのコードベースで確認できる主要ファイルを抜粋しています。

---

## 開発・デプロイ上のヒント

- 環境ごとに KABUSYS_ENV を切り替える（development / paper_trading / live）。
  - is_live / is_paper / is_dev が Settings クラスで利用可能。
- ログレベル調整は LOG_LEVEL で制御。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動ロードを抑制できます。
- DuckDB の :memory: はユニットテストで便利（init_schema(":memory:")）。

---

## 参考

- 主なエントリポイント
  - SCHEMA 初期化: kabusys.data.schema.init_schema
  - ETL 実行: kabusys.data.pipeline.run_daily_etl
  - 特徴量構築: kabusys.strategy.build_features
  - シグナル生成: kabusys.strategy.generate_signals
  - ニュース収集: kabusys.data.news_collector.run_news_collection

---

不明点や README に追加したい具体的な例（cronジョブ例や Dockerfile、CI 設定など）があれば教えてください。必要に応じて追記します。