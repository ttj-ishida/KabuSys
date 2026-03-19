# KabuSys

日本株の自動売買 / データ基盤ライブラリ「KabuSys」のリポジトリ内パッケージ向け README（日本語）。

本ドキュメントはコードベースの主要機能・セットアップ・基本的な使い方・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムとデータプラットフォームのライブラリ群です。  
主に以下の目的で設計されています。

- J-Quants API から市場データ（株価・財務・市場カレンダー）を安全かつ冪等に取得・保存する ETL パイプライン
- DuckDB によるデータスキーマ／初期化・監査ログ・品質チェック
- ニュース（RSS）収集と銘柄抽出
- 研究（factor / feature）用の定量ファクター計算・IC/統計計算
- 戦略層・発注層・監視用のモジュール分離（strategy / execution / monitoring）

設計上の特徴：
- DuckDB を中心としたオンディスク DB（またはインメモリ）での扱い
- API レート制御・リトライ・トークンリフレッシュ等を備えた J-Quants クライアント
- RSS の SSRF 対策や受信サイズ制限など安全性を考慮したニュースコレクタ
- 品質チェックを通じて ETL の信頼性を担保

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env ファイル・環境変数の自動読み込み（プロジェクトルートに基づく）
  - 必須設定の取得（例: JQUANTS_REFRESH_TOKEN）
  - KABUSYS_ENV（development / paper_trading / live）等の検証

- kabusys.data
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・リトライ・トークン更新）
  - schema: DuckDB スキーマ定義 / init_schema, get_connection
  - pipeline / etl: 日次 ETL 実行（run_daily_etl 等）
  - news_collector: RSS フィード収集・前処理・DB保存・銘柄抽出
  - calendar_management: JPX カレンダー操作（営業日判定・更新ジョブ）
  - quality: データ品質チェック（欠損・重複・スパイク・日付整合性）
  - audit: 監査ログ用スキーマ（signal → order → execution のトレーサビリティ）
  - stats / features: 統計ユーティル（z-score 正規化等）

- kabusys.research
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー

- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - 戦略実装・発注処理・監視に関連するパッケージ（各層の実装を格納）

---

## セットアップ手順

推奨 Python バージョン: 3.10 以上（Union 型注釈（|）を使用）

1. リポジトリをクローン / ダウンロード

2. Python 仮想環境を作成・有効化（例: venv）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   - 最低限依存（コード中に利用される主要パッケージの例）:
     - duckdb
     - defusedxml
   - インストール例:
     ```
     pip install duckdb defusedxml
     ```
   - 開発用にパッケージ管理ファイルがある場合はそちらを利用してください（requirements.txt / pyproject.toml 等）。

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` / `.env.local` を配置すると自動読み込みされます（kabusys.config が自動的に読み込みます）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードの無効化
     - KABUSYS_API_BASE_URL — kabu API のベース URL（デフォルト localhost の想定）
     - DUCKDB_PATH, SQLITE_PATH — データベースファイルパス（デフォルト: data/kabusys.duckdb 等）

   - .env の簡単な例（実際のトークンは伏せる）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（基本例）

以下はライブラリを直接インポートして使う基本的なコード例です。必要に応じてスクリプト化やジョブスケジューラに組み込んでください。

- DuckDB スキーマの初期化
  ```python
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # ":memory:" を渡すとインメモリ DB になります
  ```

- 日次 ETL（市場カレンダー / 株価 / 財務 / 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集（RSS）と DB 保存（known_codes を渡して銘柄紐付けも実行）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は銘柄コードの集合（例: {"7203", "6758", ...}）
  result = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(result)  # {source_name: saved_count, ...}
  ```

- J-Quants API から株価を直接取得（ページネーション対応）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes

  records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
  ```

- ファクター計算（research）
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  results = calc_momentum(conn, date(2024, 1, 4))
  ```

- forward return / IC（研究用）
  ```python
  from kabusys.research import calc_forward_returns, calc_ic

  fwd = calc_forward_returns(conn, date(2024, 1, 4), horizons=[1,5,21])
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

注記:
- jquants_client は API 呼び出しに対して固定間隔のレート制御（120 req/min）、リトライ、401 時のトークン自動リフレッシュ等を行います。
- ETL / データ保存関数は冪等（ON CONFLICT DO UPDATE / DO NOTHING）になるよう設計されています。
- News Collector は SSRF 対策、コンテンツサイズ制限、XML の安全パース（defusedxml）等を実装しています。

---

## よく使うユーティリティ / API の説明

- init_schema(db_path)
  - DuckDB のテーブルをすべて作成して接続を返す。最初に必ず呼ぶこと。

- get_connection(db_path)
  - 既存 DuckDB DB への接続を返す（スキーマは初期化しない）。

- run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
  - 日次 ETL の高レベルエントリポイント。ETLResult オブジェクトを返す。

- jquants_client.fetch_* / save_*
  - API 取得と DuckDB への保存を分離。テスト時は id_token を注入可能。

- news_collector.fetch_rss / save_raw_news / run_news_collection
  - RSS の取得 → 前処理 → raw_news へ保存 → 必要に応じて news_symbols を保存するワークフローを提供。

- research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
  - DuckDB 接続（prices_daily や raw_financials）を使ってクロスセクションの因子や将来リターン、IC を計算する。

---

## 実行時の注意点 / 運用上のヒント

- 環境変数は .env / .env.local に保存し、機密情報（トークン等）は適切に管理してください。.env ファイルはリポジトリにコミットしないでください。
- KABUSYS_ENV によって運用モード（paper_trading / live 等）を切り替えられるため、live 運用時は必ず env を確認してください。
- jquants_client はレート制御を入れていますが、他の API 呼び出しやマルチプロセスでの同時呼び出し時は注意が必要です（外部レート制御を追加する等）。
- DuckDB のファイルはバックアップ・アクセス管理を行ってください。Schema による制約チェックは入っていますが、不慮のデータ破壊に注意してください。
- テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを抑止できます。

---

## ディレクトリ構成

リポジトリ内の主要なファイル／フォルダ構成（src/kabusys 配下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得 / 保存）
    - news_collector.py              — RSS 収集・前処理・保存
    - schema.py                      — DuckDB スキーマ定義・初期化関数
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL 結果型の公開
    - quality.py                     — データ品質チェック
    - calendar_management.py         — 市場カレンダー管理
    - audit.py                       — 監査ログスキーマ初期化
    - stats.py                       — 統計ユーティリティ（z-score）
    - features.py                    — features の公開インターフェース
  - research/
    - __init__.py
    - feature_exploration.py         — 将来リターン / IC / サマリー
    - factor_research.py             — momentum/value/volatility 等の計算
  - strategy/
    - __init__.py                    — 戦略層（実装はここに追加）
  - execution/
    - __init__.py                    — 発注／ブローカー連携（実装はここに追加）
  - monitoring/
    - __init__.py                    — 監視／アラート関連（実装はここに追加）

---

## ライセンス / 貢献

- 本 README はコードベースの説明書です。実運用前に必ずコードのレビュー、テスト、そして秘密情報（API トークン等）の安全な管理を行ってください。
- 外部 API（J-Quants / kabu station）を利用する場合、各サービスの利用規約・レート制限・課金体系に従ってください。

---

必要であれば以下の追加情報を作成できます：
- .env.example（テンプレート）
- デプロイ / Cron ジョブ例（ETL の定期実行）
- 開発用の単体テスト例（モック注入の方法）
- CLI スクリプト例（簡単な run_etl.py 等）

どれを優先して用意しましょうか？