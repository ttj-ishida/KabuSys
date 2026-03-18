# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（モジュール群）。  
DuckDB をデータ基盤として、J-Quants API からのデータ取得、ETL パイプライン、データ品質チェック、特徴量計算、ニュース収集、監査ログ用スキーマなどを提供します。

主な設計方針は「実運用を想定した堅牢性」で、API のレート制御やリトライ、冪等保存、SSRF 対策、DB トランザクションなどが考慮されています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡単なコード例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株自動売買およびデータ基盤（Data Platform / Research / Execution / Monitoring）向けの共通モジュール群です。本コードベースは以下のレイヤーを含みます。

- data: J-Quants API クライアント、DuckDB スキーマ定義、ETL パイプライン、ニュース収集、カレンダー管理、品質チェック、統計ユーティリティ
- research: ファクター計算（モメンタム / バリュー / ボラティリティ）や将来リターン・IC 計算等
- execution / strategy / monitoring: 発注・戦略・監視関連のパッケージ（骨組み）
- config: 環境変数の読み込み・管理（.env 自動ロード、必須変数チェック）

設計ポイントの例:
- J-Quants の API はレート制御、リトライ、トークン自動更新に対応
- DuckDB への保存は冪等（ON CONFLICT で更新）
- RSS ニュース取得は SSFR 対策・XML 攻撃対策（defusedxml）・トラッキングパラメータ除去などを実装
- データ品質チェック（欠損、スパイク、重複、日付不整合）を実装

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数の取得（例: JQUANTS_REFRESH_TOKEN）
  - 環境（development / paper_trading / live）とログレベル検証

- kabusys.data
  - jquants_client
    - J-Quants API との通信（トークン取得、自動リフレッシュ、ページネーション、レート制御、リトライ）
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - DuckDB へ冪等保存する save_* 関数
  - schema
    - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
    - init_schema(db_path) で初期化
  - pipeline
    - 差分 ETL（run_prices_etl/run_financials_etl/run_calendar_etl / run_daily_etl）
    - 品質チェックの呼び出し
  - news_collector
    - RSS 取得（SSRF・gzip 対応・XML パース保護）
    - raw_news への保存 / 銘柄抽出（4桁コード）
  - calendar_management
    - 営業日判定・前後営業日取得・カレンダー更新ジョブ
  - quality
    - 欠損、スパイク、重複、将来日付 / 非営業日チェック
  - stats / features
    - zscore_normalize などの統計ユーティリティ

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize の再エクスポート

- audit（data.audit）
  - 監査ログ（signal_events / order_requests / executions 等）用のスキーマ初期化

---

## セットアップ手順

前提
- Python 3.9+ を推奨（型アノテーションに Union | を使用しているため）
- DuckDB、defusedxml 等の外部ライブラリを使用

1. 仮想環境を作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要なパッケージをインストール
   最低限必要なパッケージ:
   - duckdb
   - defusedxml

   例:
   ```
   pip install duckdb defusedxml
   ```
   （実運用ではロギングや Slack 連携、テスト用の追加パッケージが必要になることがあります）

3. リポジトリを Python パッケージとして利用する方法
   - 開発インストール（もし setup や pyproject がある場合）:
     ```
     pip install -e .
     ```
   - 直接 PYTHONPATH に追加するか、プロジェクト直下でスクリプトを実行します。

4. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必要な環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN : Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
     - DUCKDB_PATH (任意) : デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH (任意) : 監視用 sqlite のパス、デフォルト "data/monitoring.db"
     - KABUSYS_ENV (任意) : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL (任意) : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

   .env のパースはシェル風の書式に柔軟に対応します（export プレフィックス、クォート、コメント等）。

---

## 使い方（簡単なコード例）

以下は主要な操作のサンプルです。実運用では例外処理やログ設定を追加してください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
  ```

- 監査ログ用 DB 初期化（分離した DB にする場合）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 日次 ETL 実行（J-Quants から差分取得して保存）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 現在日で実行
  print(result.to_dict())
  ```

- ニュース収集ジョブの実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)  # {source_name: saved_count}
  ```

- ファクター計算（Research）
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  d = date(2024, 1, 31)
  mom = calc_momentum(conn, d)
  vol = calc_volatility(conn, d)
  val = calc_value(conn, d)
  # 結果は list[dict] （各 dict に date, code, ファクター列）
  ```

- 将来リターンと IC 計算
  ```python
  from kabusys.research import calc_forward_returns, calc_ic

  fwd = calc_forward_returns(conn, date(2024, 1, 31), horizons=[1,5,21])
  # factor_records は例えば calc_momentum の戻り値を想定
  ic = calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- J-Quants API を直接利用してデータを取得する（トークン自動更新・ページネーション対応）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

  # fetch_daily_quotes はページネーション対応で全件を返す
  quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 環境変数の読み取り（settings）
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.is_live)
  ```

---

## 注意点 / 運用上のヒント

- J-Quants API はレート制限（デフォルト 120 req/min）に準拠する実装です。過度の同時実行は避けてください。
- ETL は差分更新 + backfill を行うため、連続実行時には取得範囲が自動判定されます。
- ニュース収集は RSS の構造差に対するフォールバックを持ちますが、ソースによっては独自処理が必要になることがあります。
- DuckDB のバージョン差異により FK/ON DELETE の挙動や一部機能が異なるため、運用環境の DuckDB バージョンを確認してください。
- テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを抑止できます。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - execution/               — 発注周りのパッケージ（雛形）
  - strategy/                — 戦略周りのパッケージ（雛形）
  - monitoring/              — 監視周り（雛形）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS 収集 / 前処理 / 保存
    - schema.py              — DuckDB スキーマ定義と init_schema
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - features.py            — 特徴量インターフェース（再エクスポート）
    - audit.py               — 監査ログ用スキーマ初期化
    - etl.py                 — ETLResult 再エクスポート
    - quality.py             — データ品質チェック
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py — 将来リターン / IC / summary / rank

---

もし README に含めたい追加情報（例: 実運用時の Docker / systemd 設定、CI/CD の流れ、サンプル .env.example、ユニットテストの実行方法など）があれば教えてください。必要に応じて具体的なセットアップ手順や運用例（cron, Airflow, Argo Workflows など）も追記します。