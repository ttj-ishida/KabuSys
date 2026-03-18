# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）  
バージョン: 0.1.0

このリポジトリは、J-Quants 等から市場データを取得して DuckDB に保存するデータパイプライン、品質チェック、特徴量計算、ニュース収集、および監査（オーダー／約定トレース）等を提供する Python モジュール群です。研究（Research）用途のファクター計算や ETL の実行エントリポイントも含みます。

主な設計方針:
- DuckDB を中心としたローカルデータストア（冪等な INSERT / ON CONFLICT）  
- Look-ahead bias を避けるための fetched_at の記録・営業日調整  
- ネットワーク・XML・SSRF 等へのセキュリティ対策（例: defusedxml、URL 検査）  
- 外部ライブラリに依存しないユーティリティ実装（pandas 等は限定的）  

---

## 機能一覧

- 環境設定読み込み（.env 自動読み込み、必要環境変数の検証）
- J-Quants API クライアント
  - 日足（OHLCV）・財務・マーケットカレンダー取得
  - レートリミット管理・リトライ・トークン自動リフレッシュ
  - DuckDB へ冪等保存（save_* 関数群）
- ETL パイプライン
  - 差分取得（最終取得日からの差分）・バックフィル
  - 市場カレンダー / 株価 / 財務データの一括処理（run_daily_etl）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）
  - URL 正規化・トラッキング除去・SSRF 対策
  - raw_news への冪等保存、記事→銘柄紐付け
- データスキーマ管理
  - DuckDB のスキーマ定義と初期化（init_schema, init_audit_schema）
  - Raw / Processed / Feature / Execution 層のテーブル群
- 研究用モジュール（Research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算（forward returns）・IC（Spearman）計算
  - Zスコア正規化ユーティリティ
- 監査（Audit）
  - シグナル → 発注要求 → 約定を追跡する監査テーブル群

---

## セットアップ手順

1. Python 環境の用意（推奨: 3.10+）

2. 仮想環境作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   基本的に以下パッケージが必要です（プロジェクト環境に合わせて追加してください）。
   ```bash
   pip install duckdb defusedxml
   # 開発時にパッケージとしてインストールする場合
   pip install -e .
   ```

4. 環境変数の設定
   プロジェクトルートに `.env` / `.env.local` を配置すると自動読み込みされます（モジュールがプロジェクトルートを検出できる場合）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）

   任意 / デフォルト:
   - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-....
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（代表的な例）

以下はライブラリの主要な利用例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN）を設定してください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # settings.duckdb_path には .env 等で指定したパスが入る（デフォルト: data/kabusys.duckdb）
  conn = init_schema(settings.duckdb_path)
  # あるいはメモリ DB
  # conn = init_schema(":memory:")
  ```

- 日次 ETL 実行（run_daily_etl）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = get_connection("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # デフォルト: 今日をターゲットに ETL を実行
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は銘柄コード集合（抽出時のフィルタ用）
  known_codes = {"7203", "6758", "9432"}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants から日足を取得して保存（個別）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  print("saved:", saved)
  ```

- 研究用ファクター計算 / IC 計算
  ```python
  from kabusys.research import calc_momentum, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  target = date(2024, 1, 31)

  momentum = calc_momentum(conn, target)
  volatility = calc_volatility(conn, target)

  # 正規化
  momentum_z = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])

  # 将来リターンと IC 計算
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC (mom_1m vs fwd_1d):", ic)
  ```

- 監査スキーマ初期化（監査専用 DB を分けたい場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

---

## 主要モジュールの説明

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）
  - Settings クラス: 環境変数取得・必須項目検証・フラグ（is_live / is_paper / is_dev）
- kabusys.data.jquants_client
  - J-Quants API の HTTP 呼び出し、トークン取得、ページネーション対応、保存用ユーティリティ
- kabusys.data.schema
  - DuckDB の DDL（Raw / Processed / Feature / Execution / Audit 周辺）とスキーマ初期化
- kabusys.data.pipeline
  - 日次 ETL 実行ロジック（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- kabusys.data.news_collector
  - RSS フィード取得、記事前処理、ID 生成、DB 保存、銘柄抽出
- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合の検出ロジック
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.audit
  - シグナル→発注→約定の監査ログ用テーブル定義と初期化

---

## ディレクトリ構成

（重要ファイル/モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - execution/         (発注実装のための空ディレクトリ / 拡張用)
  - strategy/          (戦略実装用の空ディレクトリ / 拡張用)
  - monitoring/        (監視・メトリクス用の空ディレクトリ)
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - etl.py
    - quality.py
    - stats.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

--- 

## 実運用に関する注意事項

- 本ライブラリはデータ取得・特徴量計算・監査ログ等を提供しますが、実際の発注行為（ライブ注文）を行う際は十分なテストおよびリスク管理を行ってください。
- settings.is_live が True の場合は本番口座・API の設定が有効になっている可能性があります。環境変数の管理には注意してください。
- J-Quants のレート制限や証券会社 API の仕様に従ってください。
- DuckDB のファイルはバックアップ・運用監視が必要です。監査データは削除しない運用を推奨します。
- XML / RSS パースや HTTP 取得に対しては防御ロジックを入れていますが、外部入力には常に注意してください。

---

もし README に含めたい追加の使用例、CI / テストの説明、デプロイ手順、あるいは依存リスト（requirements.txt）を生成してほしい場合はお知らせください。