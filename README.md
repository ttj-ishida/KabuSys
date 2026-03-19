# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。データ取得（J‑Quants）、DuckDB ベースのスキーマ管理、ETL パイプライン、データ品質チェック、特徴量計算、ニュース収集、監査ログなど、戦略開発〜運用に必要な基盤機能を提供します。

この README は主に開発者向けの導入・利用方法を説明します。

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（短いコード例）
- 環境変数
- ディレクトリ構成
- よくある注意点 / トラブルシューティング

---

## プロジェクト概要

KabuSys は以下のような要件を満たすことを目指したモジュール群です。

- J‑Quants API からの株価・財務・市場カレンダーの取得（レート制御・リトライ・トークン自動更新）
- DuckDB を用いた永続化（Raw / Processed / Feature / Execution 層を想定したスキーマ）
- ETL（差分取得・バックフィル・品質チェック）を一括実行するパイプライン
- ニュース（RSS）収集と銘柄抽出
- 研究用のファクター計算（モメンタム・ボラティリティ・バリューなど）と特徴量探索ユーティリティ
- 発注・監視・監査（スキーマやユーティリティを提供。実際のブローカー連携は別実装）

設計上、本番口座や証券会社 API への直接アクセスはこのコードベース内に埋め込まず、データ取得・特徴量や監査の土台を提供します。

---

## 主な機能（機能一覧）

- 環境・設定管理
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN 等）

- データ（kabusys.data）
  - jquants_client: J‑Quants API クライアント（レートリミット、リトライ、トークン自動更新）
  - news_collector: RSS フィード → raw_news 保存（SSRF 対策、ID生成、前処理）
  - schema: DuckDB スキーマ定義と init（Raw / Processed / Feature / Execution 層）
  - pipeline / etl: 差分 ETL（株価・財務・カレンダーの差分取得と保存）、run_daily_etl の実装
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - calendar_management: 市場カレンダー管理（営業日判定・次営業日/前営業日取得）
  - audit: 監査ログ用スキーマ初期化（signal/events/order_requests/executions）
  - stats / features: Zスコア正規化などの統計ユーティリティ

- 研究（kabusys.research）
  - factor_research: モメンタム、ボラティリティ、バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- その他
  - settings API による KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL などの取得

---

## セットアップ手順

前提
- Python >= 3.10（Union 型（A | B）等の構文を使用）
- git
- ネットワーク環境（J‑Quants API を利用する場合）
- DuckDB（Python パッケージとしてインストール）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows (PowerShell 等)
   ```

3. 必要パッケージをインストール
   最低限の依存:
   - duckdb
   - defusedxml

   例:
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を作成してください（下の「環境変数」セクション参照）。
   - 自動ロードは OS 環境変数 > .env.local > .env の順で行われます。
   - テストや明示的に自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB スキーマ初期化（Python REPL で例）
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   conn = init_schema(settings.duckdb_path)
   ```
   デフォルトのパスは `data/kabusys.duckdb`（settings.duckdb_path）。

---

## 使い方（短い例）

以下は基本的なユースケースの例です。

- ETL（日次）
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # デフォルトで今日を対象に ETL を実行
  print(result.to_dict())
  ```

- 市場カレンダー更新ジョブ
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # known_codes は有効銘柄コードのセット（抽出用）
  results = run_news_collection(conn, sources=None, known_codes=set(["7203", "6758"]))
  print(results)
  ```

- 研究用：ファクター計算 / IC 算出
  ```python
  import datetime
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  target_date = datetime.date(2025, 1, 10)
  momentum = calc_momentum(conn, target_date)
  volatility = calc_volatility(conn, target_date)
  value = calc_value(conn, target_date)

  forward = calc_forward_returns(conn, target_date, horizons=[1,5])
  ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- Zスコア正規化
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, columns=["mom_1m", "atr_pct"])
  ```

---

## 環境変数（主なもの）

このライブラリは環境変数から設定を取得します。以下は主要なキーと簡単な説明です。

- JQUANTS_REFRESH_TOKEN (必須)
  - J‑Quants のリフレッシュトークン（get_id_token に使用）

- KABU_API_PASSWORD (必須 for kabu-station API integration)
  - kabu ステーション用のパスワード（将来的な発注モジュールで使用）

- KABUS_API_BASE_URL
  - kabu ステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）

- SLACK_BOT_TOKEN (必須 if Slack notifications used)
- SLACK_CHANNEL_ID (必須 if Slack notifications used)

- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）

- KABUSYS_ENV
  - 環境: development / paper_trading / live（デフォルト: development）
  - settings.is_live / is_paper / is_dev で判定できます

- LOG_LEVEL
  - ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 を設定すると .env 自動読み込みを無効化（テストで有用）

注意: Settings のプロパティ（settings.jquants_refresh_token 等）は未設定の場合 ValueError を投げます。`.env.example` を参考に必須項目を設定してください（プロジェクトに存在する場合）。

---

## ディレクトリ構成

主要なファイルと役割を示します（リポジトリの `src/kabusys` 相対）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定の読み込みロジック（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py
      - J‑Quants API クライアント（取得・保存関数、レート制御・リトライ）
    - news_collector.py
      - RSS フィード収集・前処理・raw_news 保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema(), get_connection()
    - pipeline.py
      - ETL パイプラインの主要実装（run_daily_etl 等）
    - etl.py
      - ETLResult の再エクスポート
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py
      - features の公開インターフェース（zscore_normalize を再エクスポート）
    - calendar_management.py
      - market_calendar の管理、営業日判定ユーティリティ、calendar_update_job
    - audit.py
      - 監査ログスキーマの定義と初期化（signal_events / order_requests / executions）
    - pipeline.py
      - （ETL 実行フロー。パイプライン処理を含む）
  - research/
    - __init__.py
    - feature_exploration.py
      - 将来リターン計算、IC、要約統計
    - factor_research.py
      - momentum / volatility / value 等のファクター計算
  - strategy/
    - __init__.py
    - （戦略関連モジュールを配置する想定）
  - execution/
    - __init__.py
    - （発注・ブローカー連携を実装する想定）
  - monitoring/
    - __init__.py
    - （運用監視用モジュールを配置する想定）

---

## よくある注意点 / トラブルシューティング

- Python バージョン
  - このコードは Python 3.10+ を想定しています（A | B 型など）。

- .env 自動読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動ロードします。テスト時に自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 必須環境変数が未設定だと Settings のプロパティ呼び出しで ValueError が発生します。エラーメッセージに従って .env を用意してください。

- DuckDB 初期化
  - init_schema() はテーブルを冪等的に作成します。DB ファイルの親ディレクトリが存在しない場合は自動作成します。

- ネットワーク / API エラー
  - jquants_client はレート制御、リトライ、401 に対するトークンリフレッシュを備えていますが、API キーやネットワーク設定が正しいか確認してください。
  - 429 レスポンスの Retry-After ヘッダを尊重します。

- RSS / ニュース収集
  - defusedxml を使って XML 攻撃を防いでいます。RSS の最終 URL によるリダイレクトは SSRF 対策で検査されます。

---

必要であれば、具体的なユースケース（例: 定期ジョブとしての systemd / cron 連携、Airflow／Prefect でのラッピング、監査 DB の分離運用方法など）に合わせた使い方例も作成します。どの部分のドキュメントを充実させたいか教えてください。