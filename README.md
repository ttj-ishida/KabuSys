# KabuSys

日本株向けの自動売買システム向けライブラリ群（KabuSys）。  
データ取得・ETL、特徴量計算、リサーチユーティリティ、ニュース収集、DuckDB スキーマ定義、監査ログなどを提供します。

---

## 概要

KabuSys は以下の目的に設計されたモジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得して DuckDB に保存する（差分取得・冪等保存）
- RSS ベースのニュース収集と記事→銘柄紐付け
- リサーチ／ファクター計算（モメンタム、ボラティリティ、バリュー等）と IC/統計サマリー
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレース）用スキーマ

設計上のポイント：
- DuckDB をデータ格納基盤として使用（ローカルファイルまたはインメモリ）
- J-Quants API 呼び出しはレートリミット・リトライ・トークンリフレッシュを考慮
- ニュース収集は SSRF 対策・サイズ制限・XML パース安全化（defusedxml）済み
- 本番発注 API へは直接アクセスしない（データ・研究機能は読み取り専用）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、トークン管理、保存ユーティリティ）
  - pipeline / etl: 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
  - news_collector: RSS から記事取得 → raw_news / news_symbols に保存
  - schema / audit: DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution / Audit）
  - quality: データ品質チェック（欠損、スパイク、重複、日付整合性）
  - stats: z-score 正規化等の統計ユーティリティ
  - calendar_management: 市場カレンダー管理・営業日判定
- research/
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）、ファクター統計
  - factor_research: momentum/value/volatility 等のファクター計算
- config: 環境変数管理（.env 自動ロード機能、必須チェック）
- audit: 監査ログ初期化ユーティリティ

---

## 前提条件

- Python 3.10+
  - コード中での型表記（X | Y）や型ヒントを使用しているため Python 3.10 以降を想定しています。
- 必要な Python パッケージ（抜粋）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

（プロジェクトの packaging / requirements.txt がある場合はそちらを参照してください。上記は最低限必要なものです。）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （他に必要なパッケージがあれば追加でインストール）

4. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成します。
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（主なもの）：
     - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - 任意 / デフォルト値を持つもの：
     - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/... （デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動ロード無効化
     - DUCKDB_PATH: data/kabusys.duckdb （デフォルト）
     - SQLITE_PATH: data/monitoring.db （デフォルト）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで schema.init_schema を実行して DB を初期化します（`DUCKDB_PATH` に基づく）。
   - 例:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```

6. 監査ログ（別 DB）初期化（必要なら）
   - 監査ログ専用 DB を作る場合:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（主要ユースケース例）

- 日次 ETL（市場カレンダー、株価、財務の差分取得と品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（初回のみ）
  conn = init_schema("data/kabusys.duckdb")

  # もしくは既存DBに接続
  # conn = get_connection("data/kabusys.duckdb")

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブの実行（RSS 取得 → raw_news / news_symbols へ保存）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes を与えると記事中の4桁コードを抽出して紐付ける
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count}
  ```

- ファクター計算 / リサーチ関数の利用例
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  from kabusys.data.stats import zscore_normalize
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  target = date(2024, 1, 31)

  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  # Zスコア正規化（例: mom の mom_1m を正規化）
  normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- 将来リターン・IC 計算（feature_exploration）
  ```python
  from datetime import date
  from kabusys.research import calc_forward_returns, calc_ic, rank
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

  # あるファクター（fact_records）と比較して IC を計算
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

---

## 環境変数一覧（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client が ID トークンを取得するために使用します。

- KABU_API_PASSWORD (必須)  
  kabu ステーションの API パスワード（実行環境での発注等に利用）。

- KABU_API_BASE_URL (任意)  
  kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）。

- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (必須)  
  モニタリング通知用 Slack トークンとチャネル ID。

- DUCKDB_PATH (任意)  
  DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）。

- SQLITE_PATH (任意)  
  監視用 SQLite のパス（デフォルト: data/monitoring.db）。

- KABUSYS_ENV (任意)  
  実行環境。development / paper_trading / live（デフォルト: development）。

- LOG_LEVEL (任意)  
  ログレベル（DEBUG/INFO/...、デフォルト: INFO）。

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、config モジュールによる .env の自動読み込みを無効化できます（テスト時に便利）。

---

## 注意事項 / 設計上の安全策

- J-Quants API 呼出しは内部でレートリミット制御、リトライ、401 時のトークン再取得を行います。
- news_collector は SSRF や XML Bomb、巨大レスポンス対策を実装しています。外部の RSS を扱う際も注意してください。
- DuckDB のスキーマは冪等（IF NOT EXISTS）で作成されます。監査スキーマ初期化時は UTC タイムゾーン固定等の処理があります。
- production 環境で発注を行うモジュールと連携する場合は、必ず paper_trading フラグや適切な安全ガードを導入してください（KABUSYS_ENV を利用）。

---

## ディレクトリ構成

以下はリポジトリの主要ファイル／モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（取得/保存）
    - news_collector.py                — RSS ニュース収集・保存
    - schema.py                        — DuckDB スキーマ定義・初期化
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETL 便利エクスポート（ETLResult）
    - quality.py                       — データ品質チェック
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - features.py                       — 特徴量ユーティリティの再エクスポート
    - calendar_management.py           — 市場カレンダー管理
    - audit.py                         — 監査ログスキーマ・初期化
  - research/
    - __init__.py
    - feature_exploration.py           — 将来リターン、IC、summary
    - factor_research.py               — momentum/value/volatility 等
  - strategy/                           — 戦略層（雛形）
  - execution/                          — 発注 / execution 層（雛形）
  - monitoring/                         — モニタリング関連（雛形）

---

## 貢献・拡張

- 新たなデータソースを追加する場合は data/ にクライアントと save_* 関数を実装し、schema.py に必要なテーブル定義を追加してください。
- 研究用ファクターは research/ 以下に追加し、既存の zscore_normalize 等を利用してください。
- 発注ロジックは execution/ 以下に実装し、audit スキーマを介してトレース可能にすることを推奨します。

---

必要であれば README に実際のコマンド例（cron / systemd / GitHub Actions での ETL スケジュール実行）や、より詳細な環境変数のサンプル `.env.example` を追記します。ご希望あれば教えてください。