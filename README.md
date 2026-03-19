# KabuSys

日本株向けの自動売買プラットフォーム向けユーティリティ集。データ収集（J-Quants）、DuckDB スキーマ管理、ETL パイプライン、ニュース収集、ファクター計算（リサーチ用）、監査ログ（発注 → 約定トレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの市場データ・財務データ・マーケットカレンダー取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）のスキーマ定義と初期化
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、銘柄抽出）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と IC / 統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ

設計方針として、本番口座・発注 API へ直接アクセスしないモジュール群と、発注／監視など別レイヤを分離して実装しています。標準ライブラリ中心で実装されている箇所も多く、外部依存は最小化されています（ただし DuckDB / defusedxml 等は必要）。

---

## 主な機能一覧

- 環境設定管理（.env 自動読み込み、必須チェック）
- J-Quants クライアント
  - 日足（OHLCV）/ 財務データ / マーケットカレンダーの取得（ページネーション対応）
  - レート制御（120 req/min）、リトライ、401 時のトークン自動リフレッシュ
  - DuckDB へ冪等的に保存するユーティリティ
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス・DDL を含む初期化関数
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックの一括実行（run_daily_etl）
  - 個別 ETL ジョブ（価格・財務・カレンダー）
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合の検出
- ニュース収集
  - RSS 取得（SSRF 対策、gzip チェック、XML パース保護）
  - 記事ID の冪等生成（正規化URL → SHA-256 の先頭 32 文字）
  - raw_news / news_symbols への保存
- 研究ツール
  - モメンタム / ボラティリティ / バリューのファクター計算
  - 将来リターン計算（forward returns）、IC（Spearman rank）計算
  - Z スコア正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions のスキーマと初期化関数

---

## 必要条件（Prerequisites）

- Python 3.10 以上（型注釈に `|` 演算子を使用）
- 必要なライブラリ（最小）
  - duckdb
  - defusedxml

インストール例:
pip を使ってローカルで動かす最低限の依存を入れる場合:

    python -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install duckdb defusedxml

（プロジェクトが pyproject.toml 等で配布可能なら `pip install -e .` を行ってパッケージを editable install する想定です。）

---

## 環境変数（.env）

プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしテスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。主要なキー:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

環境変数が必須の項目は `kabusys.config.settings` でアクセスすると未設定の場合に例外が発生します。

---

## セットアップ手順（概要）

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記）
4. `.env` をプロジェクトルートに作成し、必要なキーを設定
5. DuckDB スキーマを初期化

DuckDB スキーマ初期化の例:

    from kabusys.config import settings
    from kabusys.data.schema import init_schema

    conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成・初期化

監査ログ専用 DB を別に作る場合:

    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主な API と実行例）

以下はインタプリタや簡単なスクリプトからの利用例です。

- 設定の利用:

    from kabusys.config import settings
    print(settings.duckdb_path)        # Path オブジェクト
    print(settings.is_live)            # 実行環境チェック

- DuckDB スキーマ初期化:

    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行:

    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl

    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn)  # デフォルトは今日をターゲット
    print(result.to_dict())

- ニュース収集ジョブ:

    from kabusys.data.news_collector import run_news_collection

    # known_codes は銘柄抽出に使う有効なコードの集合（例: prices_daily から取得）
    known_codes = {"7203", "6758", "9984"}
    stats = run_news_collection(conn, known_codes=known_codes)
    print(stats)  # {source_name: saved_count, ...}

- J-Quants から個別取得:

    from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

    records = fetch_daily_quotes(date_from=date(2024, 1, 1), date_to=date(2024, 1, 31))
    saved = save_daily_quotes(conn, records)

- 研究（ファクター計算）:

    from kabusys.research import calc_momentum, calc_volatility, calc_forward_returns, calc_ic, factor_summary
    from datetime import date

    target = date(2025, 1, 10)
    mom = calc_momentum(conn, target)
    vol = calc_volatility(conn, target)
    fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
    ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
    summary = factor_summary(mom, ["mom_1m", "ma200_dev"])

- Zスコア正規化:

    from kabusys.data.stats import zscore_normalize
    normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])

- 監査スキーマ初期化（既存接続への追加）:

    from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)

注意点:
- J-Quants の API レートや認証の扱いは jquants_client に組み込まれています。id_token を直接渡すことでテスト性を向上できます。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を自動検出して行います。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイルと説明）

以下はパッケージ内部の主要ファイル一覧（src/kabusys 以下）。各ファイルは README の該当機能に対応しています。

- src/kabusys/
  - __init__.py                   — パッケージ定義、バージョン
  - config.py                      — 環境変数/.env 管理（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py           — RSS ニュース収集・保存（SSRF 対策、ID 生成）
    - schema.py                   — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py                    — zscore_normalize 等統計ユーティリティ
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - features.py                 — features 用インターフェース（再エクスポート）
    - calendar_management.py      — 市場カレンダー管理・営業日ロジック
    - audit.py                    — 監査ログ（signal/order/execution）スキーマ初期化
    - etl.py                      — ETLResult の再エクスポート
    - quality.py                  — データ品質チェック
  - research/
    - __init__.py                 — 研究用関数の再エクスポート
    - feature_exploration.py      — 将来リターン・IC・統計サマリ
    - factor_research.py          — モメンタム/ボラティリティ/バリュー計算
  - strategy/
    - __init__.py                 — 戦略関連（未実装の部分などに配置）
  - execution/
    - __init__.py                 — 発注/実行関連（拡張ポイント）
  - monitoring/
    - __init__.py                 — 監視ツール用（拡張ポイント）

各モジュールはソースコード内に詳細な docstring があり、関数ごとの使い方・設計方針・注意点が書かれています。実際の利用時は該当モジュールの docstring を参照してください。

---

## 運用上の注意

- 本プロジェクトはデータ収集・分析基盤を提供します。実際の発注（売買）を行う前に十分な検証・モック化を行ってください。特に本番（live）モードは `KABUSYS_ENV=live` を設定した場合に有効にする等の運用ルールを推奨します。
- DuckDB のファイルはバックアップ方針を組んでください。監査ログ用 DB を別ファイルに分けることを推奨します。
- ニュース収集や外部 URL 取得は SSRF / XML Bomb 等を考慮した実装を行っていますが、運用環境に合わせてタイムアウトやリトライ、取得対象の制限を設定してください。
- J-Quants の API レート制約・認証仕様に従って使ってください。リフレッシュトークンは安全に管理してください。

---

この README はコードベースの概要と基本的な操作例に焦点を当てています。より詳細な運用手順や戦略実装の仕様（StrategyModel.md 等）は別ドキュメントに記載されている想定です。追加で「使い方の具体的なスクリプト例」や「デプロイ手順（cron / Airflow 等）」のサンプルが必要であれば教えてください。