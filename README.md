# KabuSys — 日本株自動売買プラットフォーム（README）

注意: ここに記載する使い方・環境変数は、リポジトリ内のソースコードを参照して作成しています。実行前に .env.example に合わせて .env を作成し、必要な環境変数を設定してください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリ群です。データ収集（J-Quants）、DuckDB ベースのデータモデル、ETL パイプライン、ニュース収集、ファクター/特徴量計算、監査ログ（発注→約定のトレーサビリティ）などを含みます。Research（ファクター評価）とData（ETL / 管理）モジュールは本番の発注系ロジックと分離して設計されています。

主な設計方針：
- DuckDB を利用したローカル DB（冪等な保存ロジック）
- J-Quants API に対するレート制御・リトライ・トークン自動更新
- RSS ニュース収集での SSRF / XML bomb 対策
- 品質チェック（欠損／スパイク／重複／日付不整合）
- 監査ログ（order_request → executions までのトレーサビリティ）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）

- Data（データ層）
  - J-Quants API クライアント（jquants_client）
    - 日次株価、財務データ、マーケットカレンダーの取得（ページネーション対応）
    - レートリミット、リトライ、401 時自動トークン更新
    - DuckDB へ冪等保存（ON CONFLICT）
  - DuckDB スキーマ定義 / 初期化（schema）
  - ETL パイプライン（pipeline）
    - 日次 ETL（run_daily_etl） — カレンダー、株価、財務の差分取得 + 品質チェック
  - ニュース収集（news_collector）
    - RSS 取得、HTML/URL 前処理、記事ID生成、raw_news への冪等保存、銘柄紐付け
    - SSRF 対策、受信サイズ制限、gzip 対応
  - カレンダー管理（calendar_management）
    - 営業日判定、next/prev_trading_day、calendar 更新ジョブ
  - 品質チェック（quality）
    - 欠損、スパイク、重複、日付不整合チェック
  - 監査ログ（audit）
    - signal_events / order_requests / executions の初期化とインデックス

- Research（調査層）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC（Information Coefficient）計算
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）

- Execution / Strategy / Monitoring
  - パッケージ階層は準備済み（実際の発注ロジック等は該当モジュールを実装）

---

## 必須・代表的な環境変数

アプリケーション設定は `kabusys.config.settings` から取得します。必須となる代表的なキー：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション等の API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 動作環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

自動 .env ロードはデフォルトで有効。無効化する場合は環境変数を設定：
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

注意: settings のプロパティは必須値が無いと ValueError を投げます（例: JQUANTS_REFRESH_TOKEN が未設定の場合）。

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.9+（typing の | 記法が使われているため）
- DuckDB を利用するためネイティブモジュールが必要

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （テストや開発用に logger など追加する場合は requirements を整備してください）

4. 環境変数を準備
   - リポジトリルートに .env（と必要なら .env.local）を作成
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

   - 自動読み込みの挙動:
     - OS 環境変数 > .env.local > .env の順で設定が適用されます
     - プロジェクトルートは .git または pyproject.toml を基準に self-detect されます

5. DB スキーマ初期化（DuckDB）
   - Python REPL またはスクリプトで次を実行:

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - これにより必要なテーブル群とインデックスが作成されます。

---

## 使い方（主要ユースケースの例）

以下は代表的な利用例です。実運用ではエラーハンドリングやログ出力を追加してください。

- DuckDB スキーマ初期化

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  # settings.duckdb_path は .env で指定可能
  conn = init_schema(settings.duckdb_path)
  ```

- 日次 ETL 実行（run_daily_etl）

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)  # 初回のみ
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ実行（RSS → raw_news）

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes: 事前に有効銘柄コードセットを取得して渡す（抽出フィルタ用）
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- ファクター計算 / IC（Research）

  ```python
  from datetime import date
  import duckdb
  from kabusys.research import (
      calc_momentum, calc_volatility, calc_value,
      calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
  )

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2024, 1, 5)
  momentum = calc_momentum(conn, target)
  value = calc_value(conn, target)
  vol = calc_volatility(conn, target)

  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  # 例: mom_1m と fwd_1d の IC
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC (mom_1m vs fwd_1d):", ic)
  ```

- J-Quants からの日次株価取得を直接呼ぶ（テスト・デバッグ）

  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  from kabusys.config import settings
  from datetime import date

  token = get_id_token()  # settings.jquants_refresh_token が必要
  rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,5))
  print(len(rows))
  ```

---

## 開発時のヒント

- 環境変数自動ロードを無効にしてテストしたい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境に設定してパッケージをインポートしてください。テスト内で意図的に環境を操作する際に有用です。

- DuckDB の接続は軽量なので、ユニットテストでは ":memory:" を使って init_schema(":memory:") でインメモリ DB を作成できます。

- NewsCollector のネットワーク関数（_urlopen など）はモック可能に設計されています。ユニットテストで HTTP を差し替える際はこの関数をモックしてください。

- jquants_client は内部でレート制御とリトライを実装していますが、テストでは id_token を注入して外部 API 呼び出しを避けることができます（関数の id_token 引数を利用）。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主なパッケージとファイル:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定読み込み（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント、保存ユーティリティ
    - news_collector.py         — RSS 収集と raw_news 保存、銘柄抽出
    - schema.py                 — DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - features.py               — 特徴量ユーティリティのインターフェース
    - stats.py                  — zscore_normalize 等の統計ユーティリティ
    - calendar_management.py    — 市場カレンダー管理 (is_trading_day 等)
    - etl.py                    — ETL 公開インターフェース
    - quality.py                — データ品質チェック（欠損/スパイク/重複等）
    - audit.py                  — 監査ログ（signal/order/execution）初期化
  - research/
    - __init__.py
    - factor_research.py        — momentum / volatility / value 計算
    - feature_exploration.py    — 将来リターン / IC / summary / rank
  - strategy/
    - __init__.py               — 戦略層（拡張用）
  - execution/
    - __init__.py               — 発注実装（拡張用）
  - monitoring/
    - __init__.py               — 監視/アラート（拡張用）

---

## 追加情報 / 注意事項

- 本コードベースはデータ取得（research/data）と発注（execution/strategy）を明確に分離しています。production での実行前に、発注部分の実装・安全性確認（リスク管理・二重発注防止・監査ログ）を必ず行ってください。
- 監査ログは UTC タイムゾーンで保存する想定です（init_audit_schema は TimeZone を UTC に固定します）。
- ニュース収集や外部 API 呼び出しはネットワーク依存で失敗する可能性があります。run_daily_etl 等は個別ステップでエラーを捕捉して継続する設計ですが、ログやエラー集約を実装して運用上の可観測性を確保してください。

---

必要であれば README にサンプル .env.example、CI 実行例、詳細なテーブル定義（DDL）や API 呼び出しシーケンス図などを追加できます。どの情報を優先して追加しましょうか？