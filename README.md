KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買・データプラットフォームのための Python パッケージ骨格です。  
主に以下を目的としたモジュール群を含みます。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いたデータスキーマ定義・永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、保存、品質チェック）
- RSS ベースのニュース収集と記事→銘柄紐付け
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と IC/統計解析ユーティリティ
- マーケットカレンダー管理、監査ログ（発注〜約定のトレーサビリティ）

設計方針は「冪等性」「Look-ahead bias の防止」「API レート制限の遵守」「DuckDB による高速なローカル集計」にあります。

主な機能一覧
--------------
- data/jquants_client.py
  - J-Quants API クライアント（ページネーション対応、トークン自動リフレッシュ、再試行、レート制御）
  - データ保存用の save_* 関数（raw_prices, raw_financials, market_calendar など。冪等）
- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）と init_schema 関数
- data/pipeline.py
  - 日次 ETL（run_daily_etl）／個別 ETL ジョブ（prices、financials、calendar）
  - 差分更新・バックフィル・品質チェック連携
- data/news_collector.py
  - RSS 収集、前処理、記事保存、銘柄抽出・紐付け（SSRF防止・gzip制限・XML攻撃対策）
- data/quality.py
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue を返す）
- data/calendar_management.py
  - 営業日判定、前後営業日取得、カレンダー更新バッチジョブ
- data/audit.py
  - 発注〜約定フローの監査テーブル定義（tracing/冪等性確保）
- research/
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- data/stats.py
  - 共通統計ユーティリティ（zscore_normalize）

必要条件
--------
- Python 3.10 以上（モジュール内で PEP 604 型記法などを使用）
- pip により以下パッケージをインストールすることを想定
  - duckdb
  - defusedxml
  - （実際の運用では requests 等を追加することがありますが、本コードは標準 urllib を使用しています）

インストール（開発環境）
-----------------------
推奨: 仮想環境を作成して利用してください。

例（Unix/macOS）:
- python3 -m venv .venv
- source .venv/bin/activate
- pip install --upgrade pip
- pip install duckdb defusedxml

パッケージとしてのインストール（開発モード、パッケージ化されている場合）:
- pip install -e .

環境変数（.env）
----------------
config.py により .env/.env.local が自動で読み込まれます（プロジェクトルートは .git または pyproject.toml を基に検出）。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN  — J-Quants の refresh token（jquants_client で使用）
- KABU_API_PASSWORD      — kabuステーション API のパスワード（発注連携がある場合）
- SLACK_BOT_TOKEN        — Slack 通知用（使う場合）
- SLACK_CHANNEL_ID       — Slack チャネル ID

任意・デフォルト:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db

簡易 .env.example:
    JQUANTS_REFRESH_TOKEN=your_refresh_token_here
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C12345678
    KABUSYS_ENV=development
    LOG_LEVEL=INFO
    DUCKDB_PATH=data/kabusys.duckdb

セットアップ手順（DB 初期化）
-----------------------------
1. DuckDB ファイルを作成してスキーマを初期化する例:

Python REPL / スクリプトの例:
    from kabusys.data import schema
    conn = schema.init_schema("data/kabusys.duckdb")  # ディレクトリを自動作成
    # あるいはインメモリ:
    # conn = schema.init_schema(":memory:")

2. 監査ログ専用 DB を初期化する（必要なら）:
    from kabusys.data import audit
    conn = audit.init_audit_db("data/kabusys_audit.duckdb")

使い方（代表的なユースケース）
-----------------------------

- 日次 ETL（株価・財務・カレンダー取得＋品質チェック）
    from datetime import date
    import duckdb
    from kabusys.data import schema, pipeline

    conn = schema.init_schema("data/kabusys.duckdb")
    result = pipeline.run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- ニュース収集ジョブ（RSS 取得→保存→銘柄紐付け）
    from kabusys.data import news_collector
    conn = duckdb.connect("data/kabusys.duckdb")
    known_codes = {"7203", "6758", "9984"}  # 事前に保持している銘柄コードセット
    results = news_collector.run_news_collection(conn, sources=None, known_codes=known_codes)
    print(results)  # {source_name: saved_count, ...}

- J-Quants から日足データを直接取得（テスト・デバッグ用途）
    from kabusys.data import jquants_client as jq
    from datetime import date
    recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
    print(len(recs))

- 研究・ファクター計算（DuckDB 接続を渡す）
    from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
    from kabusys.data.stats import zscore_normalize
    conn = duckdb.connect("data/kabusys.duckdb")
    d = date(2024, 1, 31)
    mom = calc_momentum(conn, d)
    vol = calc_volatility(conn, d)
    val = calc_value(conn, d)
    fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
    ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
    normalized = zscore_normalize(mom, ["mom_1m", "ma200_dev"])

- マーケットカレンダー操作
    from kabusys.data import calendar_management as cm
    conn = duckdb.connect("data/kabusys.duckdb")
    is_trading = cm.is_trading_day(conn, date(2024, 1, 2))
    next_td = cm.next_trading_day(conn, date(2024, 1, 2))

運用上の注意
--------------
- J-Quants API のレート制限（120 req/min）に従う設計になっています。大量取得時は注意してください。
- トークン自動リフレッシュは実装されていますが、必須環境変数が未設定の場合はエラーになります。
- ETL は各ステップで例外ハンドリングを行い続行する設計ですが、品質チェック結果（error レベル）を見て運用判断をしてください。
- news_collector は外部 RSS を取得するため、SSRF 対策やレスポンスサイズ上限（10MB）等の安全対策を組み込んでいます。
- DuckDB の SQL を直接実行する箇所が多いので、データ構造（スキーマ）を変更する場合は影響範囲をよく確認してください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py           — J-Quants API クライアント（fetch/save）
  - news_collector.py           — RSS 収集・保存・銘柄抽出
  - schema.py                   — DuckDB スキーマと init_schema / get_connection
  - pipeline.py                 — ETL パイプライン（run_daily_etl 他）
  - quality.py                  — データ品質チェック
  - calendar_management.py      — 営業日判定・カレンダー更新ジョブ
  - audit.py                    — 監査ログスキーマ（注文トレーサビリティ）
  - stats.py                    — 統計ユーティリティ（zscore_normalize）
  - features.py                 — features の公開インターフェース（再エクスポート）
  - etl.py                      — ETLResult の再エクスポート
- research/
  - __init__.py                 — 研究向け関数のエクスポート
  - feature_exploration.py      — 将来リターン / IC / summary
  - factor_research.py          — momentum/value/volatility の計算
- strategy/
  - __init__.py                 — （戦略モジュールのエントリ）
- execution/
  - __init__.py                 — （発注/約定管理のエントリ）
- monitoring/
  - __init__.py                 — （監視関連）

貢献・拡張
-----------
- strategy / execution / monitoring 部分は拡張前提で空のパッケージを用意しています。実際の売買ロジックやブローカー連携はここに実装してください。
- DuckDB スキーマは DataPlatform.md / StrategyModel.md を想定した設計になっています。必要に応じてテーブルやインデックスを追加できますが、互換性・データ整合性に注意してください。

サポート
--------
このリポジトリはボイラープレート／基盤実装を目的としています。利用や拡張にあたっては各モジュールの docstring（ソース内に詳細仕様）を参照してください。さらに詳細な運用手順や本番接続のガイドラインが必要であれば教えてください。README やサンプルを追加します。