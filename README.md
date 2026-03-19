# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL・データ品質チェック、特徴量生成、リサーチ用ファクター計算、ニュース収集、DuckDB スキーマ／監査ログなどのユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の戦略実行やリサーチのための内部ユーティリティ群をまとめたパッケージです。主に以下を目的とします。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークンリフレッシュ対応）
- DuckDB を用いたデータベーススキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得、保存、品質チェック）
- ニュース RSS 収集と銘柄紐付け（SSRF 対策・トラッキング除去・冪等保存）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と IC 評価、Z スコア正規化
- 監査ログ（signal → order → execution のトレーサビリティ）

安全性・堅牢性に配慮した設計（レートリミット、再試行、SSRF対策、トランザクション、冪等性など）を重視しています。

---

## 機能一覧

主要モジュールと提供機能（抜粋）:

- kabusys.config
  - .env/.env.local の自動ロード（プロジェクトルート検出）
  - 環境変数ラッパー（必須変数チェック）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - レート制御、リトライ、トークン自動更新
- kabusys.data.schema
  - DuckDB のスキーマ定義・初期化（init_schema）
- kabusys.data.pipeline
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の ETL 実行
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
- kabusys.data.news_collector
  - fetch_rss / save_raw_news / save_news_symbols / run_news_collection
  - RSS 正規化、トラッキング除去、SSRF 回避、記事IDのハッシュ化（冪等保存）
- kabusys.data.quality
  - 欠損、スパイク、重複、日付不整合のチェック（run_all_checks）
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize を利用した正規化ユーティリティ
- kabusys.data.audit
  - 監査ログ用テーブル群定義・初期化（signal_events / order_requests / executions）

---

## 必要な環境変数

（必須・任意を README に明記しておくと便利です）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知を使う場合）

任意（デフォルトあり）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — SQLite（監視DBなど）パス。デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 を設定）

.env ファイルの自動読み込み:
- プロジェクトルート（.git または pyproject.toml を起点）から `.env` と `.env.local` を自動で読みます。
- 読み込み優先度: OS環境変数 > .env.local > .env
- 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 依存パッケージ（主要）

- Python 3.9+
- duckdb
- defusedxml

（独自の環境で使う場合はその他ユーティリティ・HTTP 標準ライブラリのみで動作する箇所もあります）

---

## セットアップ手順

1. Python 環境を準備（例: pyenv / venv）
   - 推奨: Python 3.9 以上

2. 必須ライブラリをインストール
   - 例:
     pip install duckdb defusedxml

   - パッケージ化されている場合:
     pip install -e .

3. 環境変数を設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

4. DuckDB スキーマの初期化（例: デフォルトパスを使う場合）
   - 実行例（Python）:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

---

## 基本的な使い方（コード例）

以下は最小限の利用例です。

- DuckDB スキーマ初期化:
  ```python
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しなければ今日
  print(result.to_dict())
  ```

- J-Quants から株価を手動で取得して保存:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from datetime import date

  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  ```

- ニュース収集ジョブを実行:
  ```python
  from kabusys.data.news_collector import run_news_collection

  # known_codes: 銘柄抽出に使う有効なコード集合（省略可能）
  res = run_news_collection(conn, known_codes={"7203", "6758"})
  print(res)  # ソースごとの新規保存件数の dict
  ```

- リサーチ（ファクター計算と IC 計算）:
  ```python
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
  from datetime import date

  target = date(2024, 1, 31)
  momentum = calc_momentum(conn, target)
  forward = calc_forward_returns(conn, target, horizons=[1,5])
  ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- Z スコア正規化:
  ```python
  from kabusys.data.stats import zscore_normalize

  normalized = zscore_normalize(momentum, ["mom_1m", "ma200_dev"])
  ```

---

## 主要ディレクトリ構成

パッケージは src/kabusys 配下に配置されています。主なファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・settings 提供
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存）
    - news_collector.py         — RSS ニュース収集・保存
    - schema.py                 — DuckDB スキーマ定義・初期化
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - quality.py                — データ品質チェック
    - stats.py                  — 統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py    — 市場カレンダー管理ユーティリティ
    - audit.py                  — 監査ログ（signal/order/execution）スキーマ
    - features.py               — 特徴量ユーティリティ公開インターフェース
    - etl.py                    — ETLResult の公開インターフェース
  - research/
    - __init__.py               — 研究用関数のエクスポート
    - feature_exploration.py    — 将来リターン・IC・サマリー等
    - factor_research.py        — momentum/value/volatility 計算
  - strategy/                   — 戦略関連（拡張ポイント）
  - execution/                  — 発注関連（拡張ポイント）
  - monitoring/                 — 監視用（拡張ポイント）

---

## 注意事項 / 運用上のヒント

- J-Quants のレート制限と API リトライの実装はありますが、大量連続リクエスト時は運用側でもレートに留意してください。
- ETL は差分取得ロジックを備えていますが、初回ロードや大きなバックフィルは時間がかかります。
- .env の誤設定は secret の漏洩や誤動作につながるため、git などに含めないでください。`.env.local` を使ってローカル設定を上書きできます。
- DuckDB ファイルは単一ファイルで管理されるため、バックアップや配置に注意してください。
- ニュース収集は RSS ソース外部に依存するため、フェッチ失敗が発生してもジョブは他ソースへ継続するように設計されています。
- 監査ログ（audit）用テーブルは UTC でタイムスタンプを保存します。DB 初期化時に TimeZone を UTC にセットする処理を行います。

---

## 貢献・拡張ポイント

- strategy / execution / monitoring パッケージは拡張点です。実際の売買ロジックや発注実装、監視アラートを追加してください。
- 追加の品質チェックや統計解析（ファクター生成、機械学習前処理）を research 側に実装できます。
- 外部依存（例: Slack 通知、kabu API 実装）を統合して運用用パイプラインを構築してください。

---

必要があれば、サンプルの .env.example、CI 用の軽量 ETL 実行スクリプト、Dockerfile などの追加ドキュメントも作成できます。どの部分を詳しく知りたいか教えてください。