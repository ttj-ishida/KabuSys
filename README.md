# KabuSys

日本株向け自動売買基盤（KabuSys）。データ収集（J-Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム取引基盤を構成するライブラリ群です。主な目的は以下です。

- J-Quants API からの市場データ・財務データ・カレンダー取得（レートリミット・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution 層）の管理とスキーマ初期化
- ETL（差分取得・バックフィル・品質チェック）を行う日次パイプライン
- 研究（research）で算出したファクターを正規化して戦略用特徴量を構築
- 特徴量＋AIスコアから最終スコアを計算し売買シグナルを生成（BUY / SELL）
- RSS からのニュース収集と銘柄抽出（SSRF対策・サイズ制限・トラッキングパラメータ除去）
- 発注／約定／ポジション管理のためのスキーマと監査ログ

設計上、発注層（broker API）への依存は最小化されており、戦略ロジックは発注実行層に依存しないようになっています。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得と検証（env 値検査、KABUSYS_ENV の検証等）
- データ取得（J-Quants）
  - 日足（OHLCV）・財務データ・マーケットカレンダーのページネーション対応フェッチ
  - レート制限／指数バックオフリトライ／401時のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT を使用）
- ETL パイプライン
  - 差分取得（最終取得日判定）・バックフィル・品質チェック
  - run_daily_etl による一括処理
- データスキーマ管理
  - DuckDB の全テーブル／インデックス作成（init_schema）
  - Raw / Processed / Feature / Execution 層を定義
- 研究支援（research）
  - momentum/value/volatility 等のファクター計算
  - 将来リターン計算（forward returns）、IC 計算、ファクターサマリー
  - z-score 正規化ユーティリティ
- 特徴量生成（strategy.feature_engineering）
  - ファクター統合、ユニバースフィルタ（株価・流動性）、Zスコア正規化、features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator）
  - 各コンポーネントスコア算出（momentum/value/volatility/liquidity/news）
  - AI レジーム判定（Bear 判定）に基づく BUY 抑制
  - BUY / SELL の判定と signals テーブルへの日付単位置換（冪等）
- ニュース収集（data.news_collector）
  - RSS 取得、前処理（URL除去・空白正規化）、記事IDの生成（正規化URL の SHA-256）
  - SSRF 対策、レスポンスサイズ制限、defusedxml を使用した安全な XML パース
  - raw_news / news_symbols への冪等保存
- マーケットカレンダー管理（data.calendar_management）
  - DBのカレンダー優先の営業日判定・前後営業日取得・範囲内営業日取得
- 監査ログ（data.audit）
  - signal → order_request → execution までトレース可能なテーブル定義

---

## セットアップ手順

以下は開発・実行に必要な最低限の手順です。実環境では OS や Python バージョンに合わせて調整してください。

1. リポジトリをクローンする
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell/CMD)
   ```

3. 必要なパッケージをインストール
   - このコードベースでは少なくとも以下が必要になります:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - 実運用では HTTP リクエスト用に urllib が標準で使われているため追加ライブラリは最小です。プロジェクトに requirements.txt があればそちらを使用してください。

4. 環境変数の設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV — 環境 (development|paper_trading|live)。デフォルト: development
     - LOG_LEVEL — ログレベル（DEBUG, INFO, ...）。デフォルト: INFO
     - DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — SQLite（監視用）パス。デフォルト: data/monitoring.db

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. データベーススキーマ初期化
   - DuckDB を初期化してスキーマを作成します。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - ":memory:" を指定するとインメモリ DB が使えます（テスト等）。

---

## 使い方（簡易サンプル）

以下は Python REPL またはスクリプトで使う基本的な例です。

1. DB 初期化（1度実行）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL 実行（J-Quants からデータ取得して保存）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # target_date を指定しなければ今日
   print(result.to_dict())
   ```

3. 特徴量のビルド（strategy.feature_engineering）
   ```python
   import duckdb
   from datetime import date
   from kabusys.strategy import build_features

   conn = duckdb.connect("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2024, 1, 5))
   print(f"features upserted: {n}")
   ```

4. シグナル生成
   ```python
   import duckdb
   from datetime import date
   from kabusys.strategy import generate_signals

   conn = duckdb.connect("data/kabusys.duckdb")
   count = generate_signals(conn, target_date=date(2024, 1, 5))
   print(f"signals written: {count}")
   ```

5. ニュース収集ジョブ（RSS から raw_news 保存）
   ```python
   import duckdb
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = duckdb.connect("data/kabusys.duckdb")
   # known_codes: 抽出に使用する有効銘柄コードセットを渡すと銘柄紐付けを行う
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
   print(res)
   ```

6. カレンダー更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   conn = duckdb.connect("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"saved calendar rows: {saved}")
   ```

注意:
- 上記の多くは J-Quants の API トークンやネットワークアクセスを伴うため、事前に環境変数を設定してください。
- 取引（発注）部分については発注 API との接続層（execution）実装が別途必要です。本リポジトリは戦略・シグナル生成とデータ基盤を中心に提供します。

---

## 環境変数一覧（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（get_id_token に使用）
  - KABU_API_PASSWORD — kabu API パスワード
  - SLACK_BOT_TOKEN — Slack bot token（通知用）
  - SLACK_CHANNEL_ID — Slack channel id（通知用）
- デフォルト値あり / オプション
  - KABUSYS_ENV — development / paper_trading / live（default: development）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（default: INFO）
  - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite パス（default: data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合は "1" を設定

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（フェッチ・保存）
    - news_collector.py — RSS ニュース収集と保存
    - schema.py — DuckDB スキーマ定義と初期化（init_schema）
    - stats.py — z-score 等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - features.py — データユーティリティの公開（zscore_normalize）
    - calendar_management.py — マーケットカレンダー更新／営業日判定
    - audit.py — 監査ログ用スキーマ（signal_events, order_requests, executions）
    - (その他 execution / monitoring 用のモジュール群)
  - research/
    - __init__.py
    - factor_research.py — momentum/value/volatility 等のファクター計算
    - feature_exploration.py — 将来リターン, IC, 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル構築（build_features）
    - signal_generator.py — signals 生成（generate_signals）
  - execution/ — 発注層（空の __init__.py 等）
  - monitoring/ — 監視・メトリクス関連（未記載のモジュールが入る想定）

---

## 設計上の注意点 / 運用上のヒント

- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。プロダクションでは永続ストレージに配置してください。
- J-Quants レートリミット（120 req/min）を意識しており、クライアント側で固定間隔スロットリングを行います。大量の同期フェッチは避けてください。
- ETL は差分取得を行い、デフォルトでバックフィル（直近数日再取得）をするため API の後出し修正を吸収できます。
- features / signals の処理は「日付単位置換（DELETE + BULK INSERT）」で冪等性を保っています。再実行しても重複が発生しません。
- ニュース収集は SSRF 対策やレスポンス上限、XML の安全パース（defusedxml）を組み込んでいますが、外部フィードの取り扱いは十分注意してください。
- KABUSYS_ENV を `live` に設定すると is_live が True になり、稼働環境として扱われます。paper_trading など運用ポリシーの差分をコードで扱っている箇所に注意してください。

---

## 付録 / 参考

- 主要 API:
  - init_schema(db_path) — DuckDB スキーマ初期化
  - run_daily_etl(conn, target_date=None, ...) — 日次 ETL
  - build_features(conn, target_date) — 特徴量生成
  - generate_signals(conn, target_date, ...) — シグナル生成
  - calendar_update_job(conn, lookahead_days=90) — カレンダー夜間更新
  - run_news_collection(conn, sources, known_codes) — ニュース収集

---

README に書かれている以外の実行スクリプトや CLI は別途用意してください。本 README はコードベースの主要機能と使い方のサマリを提供することを目的としています。追加で CI やデプロイ手順、テストの実行方法、.env.example の具体的なテンプレートなどを含めたい場合はその旨を教えてください。