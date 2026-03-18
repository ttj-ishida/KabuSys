# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
DuckDB をデータストアとして用い、J-Quants API や RSS ニュースを取り込み、特徴量計算・品質チェック・ETL・監査ログなどを備えた設計になっています。

バージョン: 0.1.0

## 概要
- 市場データ（株価日足）、財務データ、マーケットカレンダー、ニュースを取得・保存する ETL パイプラインを提供します。
- DuckDB にスキーマを定義・初期化するユーティリティを持ち、冪等性（ON CONFLICT）を考慮した保存処理が行えます。
- 研究 (research) 用のファクター／特徴量計算、Z スコア正規化、将来リターン・IC 計算などを備え、戦略評価・研究に利用できます。
- ニュース収集では SSRF 対策・レスポンスサイズ制限・URL 正規化など安全性を考慮しています。
- データ品質チェック（欠損、スパイク、重複、日付不整合）や監査ログ（シグナル→発注→約定のトレース）が備わっています。

## 主な機能一覧
- データ取得 / 保存
  - J-Quants API クライアント（株価日足・財務・カレンダー取得、トークン自動リフレッシュ、レート制御、リトライ）
  - RSS フィードからのニュース収集（正規化・前処理・DB 保存・銘柄抽出）
  - DuckDB 用スキーマ定義 / 初期化 / 既存 DB 接続
- ETL / パイプライン
  - 差分取得（最終取得日を参照して新規のみ取得）、バックフィルのサポート
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
- 研究 / 特徴量
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を用いたファクター計算）
  - calc_forward_returns（将来リターン）、calc_ic（スピアマンランク相関）、factor_summary（統計サマリ）
  - zscore_normalize（クロスセクション Z スコア正規化）
- データ品質チェック
  - 欠損データ、スパイク、重複、日付不整合の検出
- 監査（Audit）
  - signal_events / order_requests / executions 等の監査テーブルと初期化ユーティリティ
- カレンダー管理
  - 営業日判定、前後営業日取得、JPX カレンダー更新ジョブ

## 必要条件
- Python 3.9+
- duckdb
- defusedxml
- （標準ライブラリ以外の依存はモジュール用途に応じて必要。requirements.txt があればそれに従ってください。）

例:
pip install duckdb defusedxml

（プロジェクトの packaging/requirements によっては追加パッケージが必要です）

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - もし requirements.txt があれば: pip install -r requirements.txt
4. 環境変数を用意
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時等）。
5. DuckDB スキーマ初期化
   - Python REPL / スクリプトで次を実行して DB を初期化します（デフォルトパスは data/kabusys.duckdb）。
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)

## 必要な環境変数
以下はコード中で必須扱いされる環境変数です（不足時は ValueError が発生します）。

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）

任意（デフォルトあり）：
- KABUSYS_ENV           : 実行環境 (development | paper_trading | live)。デフォルト: development
- LOG_LEVEL             : ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)。デフォルト: INFO
- DUCKDB_PATH           : DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH           : 監視用 SQLite パス。デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動読み込みを無効化

※ .env.example を参考に .env を作成してください（プロジェクトルートに配置すると自動読み込みされます）。

## 使い方（主要例）

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（market calendar / prices / financials を取得して保存）
  - from kabusys.data.pipeline import run_daily_etl
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn)  # 引数で target_date や id_token を指定可能
    print(result.to_dict())

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
    conn = init_schema("data/kabusys.duckdb")
    known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット（省略可）
    stats = run_news_collection(conn, known_codes=known_codes)
    print(stats)  # {source_name: saved_count, ...}

- J-Quants から株価を直接フェッチして保存
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    records = fetch_daily_quotes(date_from=..., date_to=...)
    saved = save_daily_quotes(conn, records)

- ファクター／研究用関数（例: モメンタム・IC 計算）
  - from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
    conn = init_schema("data/kabusys.duckdb")
    recs = calc_momentum(conn, target_date=some_date)
    forwards = calc_forward_returns(conn, target_date=some_date)
    ic = calc_ic(recs, forwards, factor_col="mom_1m", return_col="fwd_1d")
    normalized = zscore_normalize(recs, ["mom_1m", "mom_3m", "mom_6m"])

- 品質チェック
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=some_date)
    for i in issues:
        print(i)

- 監査テーブル初期化（監査ログ専用 DB）
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")

注意:
- J-Quants API へはレート制御とリトライが組み込まれています。トークンは自動リフレッシュされます。
- ETL や API 呼び出しでは例外が発生しうるため、呼び出し側で適切にハンドルしてください。
- research / data モジュールは本番発注 API にはアクセスしません（読み取り専用での分析向け）。

## ディレクトリ構成（主要ファイル）
以下はパッケージ内の主要モジュールと役割の一覧です（src/kabusys 以下）。

- __init__.py
  - パッケージメタ情報（__version__）とサブパッケージの公開設定

- config.py
  - 環境変数の読み込み（.env/.env.local 自動読み込み）、設定取得用 Settings クラス

- data/
  - jquants_client.py : J-Quants API クライアント（フェッチ・保存）
  - news_collector.py : RSS ニュース収集・正規化・保存
  - schema.py         : DuckDB スキーマ定義と init_schema/get_connection
  - pipeline.py       : ETL パイプライン（run_daily_etl 等）
  - features.py       : 特徴量関連の公開ユーティリティ（zscore 再エクスポート）
  - stats.py          : 汎用統計ユーティリティ（zscore_normalize）
  - calendar_management.py : マーケットカレンダー更新・営業日判定ロジック
  - audit.py          : 監査ログ（signal / order_request / executions）初期化
  - etl.py            : ETLResult の公開インターフェース
  - quality.py        : データ品質チェック

- research/
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー、ランク関数
  - factor_research.py     : mom/volatility/value 等のファクター計算
  - __init__.py            : 研究用 API の再エクスポート

- strategy/
  - （空の __init__.py。戦略ロジックはここに置く想定）

- execution/
  - （発注・ブローカー連携ロジックを配置する場所）

- monitoring/
  - （監視関連モジュールのためのプレースホルダ）

実際のファイルツリー（抜粋）:
src/kabusys/
  __init__.py
  config.py
  data/
    jquants_client.py
    news_collector.py
    schema.py
    pipeline.py
    etl.py
    stats.py
    features.py
    calendar_management.py
    quality.py
    audit.py
  research/
    feature_exploration.py
    factor_research.py
    __init__.py
  strategy/
    __init__.py
  execution/
    __init__.py
  monitoring/
    __init__.py

## 開発・テストに関する補足
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml の位置）を基準に行われます。テスト時に自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- J-Quants API クライアント内ではテスト容易性のため id_token を注入可能です（関数引数で指定できます）。
- RSS フィード取得では内部的に _urlopen を呼んでおり、テストではモック差し替えが容易にできる設計です。

---

ご不明な点や README に追加したい利用例（具体的な ETL スケジュール例や Slack 通知の使い方など）があれば教えてください。README に追記して整備します。