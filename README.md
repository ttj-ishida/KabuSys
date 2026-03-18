# KabuSys

日本株向けの自動売買基盤コンポーネント群（データ収集・ETL・特徴量生成・研究用ユーティリティ・監査ログ等）です。  
本リポジトリは DuckDB を中心としたローカルデータレイクを前提に、J-Quants API や RSS を使ったデータ収集、ETL、品質チェック、研究用ファクター計算を提供します。

バージョン: 0.1.0

## 主な特徴
- J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ対応）
- DuckDB スキーマ定義と初期化ユーティリティ（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース収集（RSS -> 前処理 -> DuckDB への冪等保存・銘柄紐付け）
- データ品質チェック（欠損・スパイク・重複・日付整合性の検出）
- 研究用関数（モメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン・IC 計算、Zスコア正規化）
- 監査ログ（シグナル→発注→約定のトレースを可能にする監査スキーマ）

## 機能一覧（概要）
- data/
  - jquants_client: J-Quants API からのデータ取得 & DuckDB への保存関数
  - schema: DuckDB のテーブル定義・初期化（init_schema, get_connection）
  - pipeline: 日次 ETL 実行（run_daily_etl, run_prices_etl, ...）
  - news_collector: RSS 取得・前処理・保存・銘柄抽出
  - quality: データ品質チェック（run_all_checks 等）
  - calendar_management: 市場カレンダー管理（営業日判定・更新ジョブ）
  - audit: 監査ログ用スキーマ初期化
  - stats / features: 汎用統計ユーティリティ（zscore_normalize など）
- research/
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリー 等
- config: 環境変数・設定管理（.env 自動読み込み機能）
- strategy, execution, monitoring: 発注・戦略・監視のためのパッケージプレースホルダ

## 必要条件
- Python 3.10+
- 以下の主な Python パッケージ（最小限）:
  - duckdb
  - defusedxml

インストール例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb defusedxml

（プロジェクト配布の setup.cfg / pyproject.toml / requirements.txt がある場合はそちらを参照してください）

## 環境変数 / 設定
パッケージ起動時、プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を探索し、`.env` / `.env.local` を自動で読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に使用する環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API ベースURL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (任意) — DuckDB のパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

.env の例（重要なキーのみ）:
  JQUANTS_REFRESH_TOKEN=...
  KABU_API_PASSWORD=...
  SLACK_BOT_TOKEN=...
  SLACK_CHANNEL_ID=...
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development

## セットアップ手順（簡易）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. Python 仮想環境作成・有効化
   python -m venv .venv
   source .venv/bin/activate

3. 必要パッケージをインストール
   pip install duckdb defusedxml

   （プロジェクトにパッケージ管理ファイルがあれば pip install -e . や pip install -r requirements.txt を実行）

4. .env を作成して必要な環境変数を設定
   - ルートに .env / .env.local を作成すると自動で読み込まれます。
   - テスト時など自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. DuckDB スキーマを初期化
   Python から実行例:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   これにより必要なテーブル・インデックスが作成されます。

6. 監査ログ DB（任意）を初期化
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")

## 使い方（代表的な操作例）

- 日次 ETL 実行
  Python から:
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn)  # target_date を指定可能
    print(result.to_dict())

  run_daily_etl は市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック を行い ETLResult を返します。

- ニュース収集ジョブ（RSS）
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  # known_codes は銘柄抽出に利用（任意）
  known_codes = {r[0] for r in conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall()}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数, ...}

- 研究用ファクター計算
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

  conn = duckdb.connect("data/kabusys.duckdb")
  tgt = date(2024, 1, 31)
  momentum = calc_momentum(conn, tgt)
  volatility = calc_volatility(conn, tgt)
  value = calc_value(conn, tgt)

  # 将来リターンと IC 計算
  fwd = calc_forward_returns(conn, tgt, horizons=[1,5,21])
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC (mom_1m vs fwd_1d):", ic)

- Zスコア正規化（クロスセクション）
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

- J-Quants API からの直接取得（例: 日足）
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  saved = save_daily_quotes(conn, records)

注意:
- jquants_client は内部でレートリミットとリトライを行います。大量リクエスト時は仕様を守ってください。
- fetch や save は idempotent（ON CONFLICT DO UPDATE/DO NOTHING）です。

## ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動読み込み / settings
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント、保存ユーティリティ
    - news_collector.py — RSS 取得・前処理・保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義 / init_schema / get_connection
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - features.py, stats.py — 統計・正規化ユーティリティ
    - calendar_management.py — market_calendar 管理、営業日判定
    - audit.py — 監査ログスキーマ初期化
    - quality.py — データ品質チェック
    - etl.py — ETLResult の公開
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value の計算
    - feature_exploration.py — 将来リターン、IC、summary、rank
  - strategy/, execution/, monitoring/ — モジュールプレースホルダ

（実際のファイルはリポジトリルートの src/kabusys 以下を参照してください）

## 運用上の注意
- 本システムは本番発注機能（kabu API 等）との連携を想定しています。発注・約定関連を運用する場合は必ず paper_trading 環境で十分に検証してください。
- 環境変数に機密情報（トークン等）を格納するため .env の管理には注意してください（Git 管理対象から除外する等）。
- DuckDB ファイルは適切にバックアップしてください。大規模データではファイルサイズが大きくなります。
- news_collector は外部 URL を取得します。SSRF 対策・応答サイズ上限などを実装していますが、運用時はソースの管理を行ってください。

## 開発 / 貢献
バグレポート・機能提案は Issue をご利用ください。Pull Request での貢献も歓迎します。  
コードスタイルやテスト方針はリポジトリ内の開発ドキュメント（存在する場合）に従ってください。

---

README に書かれている使い方は代表例です。各関数の詳細な API や引数・戻り値はソースコードの docstring を参照してください。必要であれば README に CLI やサンプルスクリプトを追加しますので要望をお知らせください。