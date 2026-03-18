# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ群（データ取得・ETL・特徴量計算・監査など）

概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成をまとめた README です。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための基盤ライブラリ群です。主に次の責務を持ちます：

- J-Quants API からの市場データ（株価日足、財務データ、マーケットカレンダー）取得と DuckDB への永続化（冪等保存）
- RSS を用いたニュース収集と記事→銘柄紐付け
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算、IC・統計サマリー等のリサーチ機能
- DuckDB スキーマ定義・監査ログ（オーダー→約定までのトレーサビリティ）
- 環境設定管理（.env 自動読み込み、必須環境変数の取得）

設計方針の一部：
- DuckDB を中心に、SQL（ウィンドウ関数等）で効率的に処理
- 本番取引 API（kabu ステーション等）への発注部分は別モジュール（execution）に分離
- Look-ahead bias を防ぐためデータ取得時間（fetched_at）を記録
- 冪等性を重視した DB 保存（ON CONFLICT / DO UPDATE / DO NOTHING）

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（OS 環境変数優先）
  - 必須環境変数取得（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）

- データ取得（J-Quants）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）
  - レートリミット管理、リトライ（指数バックオフ）、401 の自動トークンリフレッシュ

- データ保存（DuckDB）
  - raw_prices / raw_financials / market_calendar 等への冪等保存関数（save_* 系）
  - スキーマ初期化（init_schema）、監査ログ用スキーマ（init_audit_schema / init_audit_db）

- ETL パイプライン
  - run_daily_etl: カレンダー→株価→財務の差分取得と品質チェックの統合ジョブ
  - 差分取得・バックフィルロジック、自動的な営業日調整

- データ品質チェック
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合（未来日など）検出
  - QualityIssue 型で検出結果を集約

- ニュース収集
  - RSS フィード収集（SSRF 保護、gzip 上限、XML の安全パース）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で冪等性確保
  - raw_news 保存、記事→銘柄紐付け（news_symbols）の一括保存

- リサーチ（特徴量 / 評価）
  - calc_momentum, calc_value, calc_volatility（prices_daily, raw_financials を参照）
  - calc_forward_returns, calc_ic（Spearman ランク相関）、factor_summary、rank
  - zscore_normalize（クロスセクション正規化）

- スキーマ・監査
  - DuckDB 上に Raw / Processed / Feature / Execution / Audit 層のテーブルを定義
  - 監査ログは order_request_id（冪等キー）等を用いてトレースを保証

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の union 型（|）などを使用）
- pip / 仮想環境の利用を推奨

例（Unix 系）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージのインストール（最低限）
   - pip install duckdb defusedxml

   実運用ではロギングや Slack クライアント、HTTP ライブラリを追加することがあります。

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml を検出）から自動で `.env` と `.env.local` を読み込みます。
   - 読み込み順: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabu ステーション API のパスワード（必須）
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知用（必須）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）

4. DuckDB スキーマ初期化
   - Python から:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - これにより必要なテーブルとインデックスが作成されます（冪等）。

---

## 使い方（主要な例）

以下は代表的な利用例です。実際にはロガーや例外処理、環境変数の設定を行ってください。

- DuckDB スキーマ初期化

  ```python
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  ```

- ETL（日次ジョブ）を実行する

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から日足を直接取得して保存する（テスト用途）

  ```python
  import duckdb
  from kabusys.data import jquants_client as jq
  from kabusys.config import settings

  conn = duckdb.connect(":memory:")
  # 事前に init_schema を呼ぶか、必要テーブルを作成してください
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- ニュース収集ジョブを実行する

  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes を与えると記事と銘柄の紐付けも行います
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- リサーチ（ファクター計算・IC）

  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  t = date(2024, 1, 31)
  momentum = calc_momentum(conn, t)
  vol = calc_volatility(conn, t)
  val = calc_value(conn, t)
  fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
  # 例: モメンタム mom_1m と 翌日リターン fwd_1d の IC
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- データ品質チェック

  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  ```

注意点：
- 実運用では J-Quants の API レート制限やトークン管理、エラーハンドリングを適切に行ってください（ライブラリはレートリミットとリトライを実装しています）。
- DuckDB のバージョンやファイルパスの権限に注意してください。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)。development がデフォルト
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）。INFO がデフォルト
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動読み込みを無効化

.env のパースはシェル形式（export 形式やクォート、コメント等）に柔軟に対応します。

---

## ディレクトリ構成

リポジトリの主要ファイル/モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - news_collector.py            — RSS ニュース収集・保存・銘柄抽出
    - schema.py                    — DuckDB スキーマ定義・初期化
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - features.py                  — 特徴量ユーティリティ公開（zscore_normalize）
    - calendar_management.py       — マーケットカレンダー管理ユーティリティ
    - audit.py                     — 監査ログ（order/events/executions）
    - etl.py                       — ETL 公開型（ETLResult の再エクスポート）
    - quality.py                   — データ品質チェック
  - research/
    - __init__.py                  — 研究用 API の公開（calc_momentum 等）
    - feature_exploration.py       — 将来リターン、IC、サマリー
    - factor_research.py           — Momentum/Value/Volatility の計算
  - strategy/
    - __init__.py                  — 戦略層（空のパッケージ、戦略実装を格納）
  - execution/
    - __init__.py                  — 発注・約定・ブローカー連携（別途実装）
  - monitoring/
    - __init__.py                  — 監視・メトリクス（未実装のプレースホルダ）

各モジュールは「DuckDB接続を受け取る」「外部発注APIには直接アクセスしない（研究・データ処理）」等の設計方針に基づいて実装されています。

---

## 開発時の注意 / 補足

- Python バージョン：3.10 以上を推奨（型アノテーションで | を利用）
- DuckDB は pip でインストール可能（pip install duckdb）
- RSS パーサーには defusedxml を利用して安全に XML をパースします（pip install defusedxml）
- 実運用での発注ロジック（execution パッケージ）は別途実装する想定です
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを抑制できます

---

必要があれば次の内容を追加で作成できます：
- .env.example のテンプレート
- requirements.txt / pyproject.toml 用の依存リスト
- 実運用でのデプロイ手順（systemd / cron / Airflow 等）
- strategy / execution 実装のサンプル

ご希望があれば上記のいずれかを作成します。