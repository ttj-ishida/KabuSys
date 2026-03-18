# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（部分実装）。  
主にデータ取得・ETL、データ品質チェック、ファクター/リサーチ、ニュース収集、DuckDB スキーマ管理、および J-Quants API クライアント等を提供します。

---

## プロジェクト概要

KabuSys は日本株のデータプラットフォームと戦略リサーチ基盤を想定した Python パッケージです。  
設計上の特徴：

- DuckDB を用いたオンディスク（またはインメモリ）データベースで Raw / Processed / Feature / Execution 層を管理
- J-Quants API からの株価・財務・マーケットカレンダー取得（レートリミット・リトライ・トークン自動更新対応）
- RSS ベースのニュース収集（SSRF対策・トラッキングパラメータ除去・gzip対応・冪等保存）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター計算（Momentum / Volatility / Value など）、IC計算、Z スコア正規化
- データ品質チェック、監査ログスキーマ（発注/約定のトレース用）

このリポジトリはライブラリ本体（src/kabusys）を含みます。

---

## 主な機能一覧

- data/jquants_client:
  - J-Quants API クライアント（ページネーション、レート制御、リトライ、トークン自動更新）
  - 生データを DuckDB に冪等保存する save_* 関数
- data/pipeline:
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
- data/schema, data/audit:
  - DuckDB のスキーマ初期化（init_schema / init_audit_schema）
- data/news_collector:
  - RSS 取得・前処理・正規化・DB保存・銘柄抽出（SSRF 対策、gzip、XML 安全パーサ）
- data/quality:
  - 欠損・重複・スパイク・日付不整合チェック
- research:
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- 設定管理:
  - 環境変数の読み込み（.env / .env.local を自動読み込み、プロジェクトルートは .git または pyproject.toml で検出）
  - 必須項目チェック（Settings クラス）

---

## 前提・依存パッケージ

最低限必要なパッケージ（代表）:

- Python 3.9+
- duckdb
- defusedxml

（プロジェクトに requirements.txt がある場合はそれを利用してください）

インストール例（pip）:

pip install duckdb defusedxml

※ 実行環境で追加のパッケージが必要な場合があります。パッケージ管理はプロジェクト側の指示に従ってください。

---

## 環境変数 / .env

自動で .env ファイルをプロジェクトルート（.git または pyproject.toml 上位で検出）から読み込みます。  
自動ロードを無効化するには環境変数を設定します:

export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（必須と既定値）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例 (.env):

JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate

3. 依存パッケージをインストール
   pip install duckdb defusedxml

   （requirements.txt がある場合は `pip install -r requirements.txt`）

4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、環境変数をエクスポートしてください。
   - 必須変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

5. DuckDB スキーマ初期化（例）
   - Python コンソール/スクリプトから:

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

   これで必要なテーブルが作成されます。

---

## 使い方（簡易クイックスタート）

- スキーマ初期化

  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants からデータを取得して保存、品質チェック）

  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # 省略で今日を対象に実行
  print(result.to_dict())

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）

  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203","6758", ...}  # 既知の銘柄コードセットを用意
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)  # ソース毎の新規保存数

- 研究 / ファクター計算

  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  conn = init_schema("data/kabusys.duckdb")
  from datetime import date
  d = date(2024, 1, 31)
  mom = calc_momentum(conn, d)
  vol = calc_volatility(conn, d)
  val = calc_value(conn, d)
  fwd = calc_forward_returns(conn, d)
  ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")

- 監査スキーマ初期化（発注/約定監査用）

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 主要 API の説明（ポイント）

- settings (kabusys.config.settings)
  - 環境変数アクセスラッパ。必須変数が未設定の場合は ValueError を投げる。

- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - 内部でレート制御（120 req/min）・リトライ・401 の場合はトークンを refresh して再試行。

- ETL（kabusys.data.pipeline）
  - run_daily_etl: カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック。例外は個別に処理して継続。

- ニュース収集（kabusys.data.news_collector）
  - fetch_rss: SSRF 対策・gzip ハンドリング・XML 安全パース。記事 ID は正規化 URL の SHA-256（先頭32文字）で冪等性を確保。
  - save_raw_news, save_news_symbols: DuckDB に冪等的に保存（トランザクション・チャンク処理）。

- 研究（kabusys.research）
  - ファクター計算は DuckDB の prices_daily / raw_financials テーブルのみ参照（本番発注 API にはアクセスしない設計）。
  - IC（Spearman ρ）や z-score 正規化などのユーティリティを提供。

- データ品質（kabusys.data.quality）
  - 欠損、重複、スパイク、日付整合性などを検出し QualityIssue のリストで返す。ETL はこれらを参照して運用判断可能。

---

## ログ設定

- 環境変数 LOG_LEVEL でログレベルを指定できます（デフォルト INFO）。
- KABUSYS_ENV = development / paper_trading / live により動作モードを切替可能。settings.is_live などの判定に利用。

---

## ディレクトリ構成

リポジトリ内の主要ファイル／モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集・保存
    - schema.py              — DuckDB スキーマ定義 / init_schema / get_connection
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - features.py            — 特徴量ユーティリティ（再エクスポート）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — カレンダー管理ユーティリティ / バッチジョブ
    - audit.py               — 監査ログ（order_requests / executions 等）
    - etl.py                 — ETL 公開インターフェース（ETLResult 再エクスポート）
    - quality.py             — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
    - factor_research.py     — Momentum/Volatility/Value ファクター計算
  - strategy/                 — 戦略層（空 __init__.py / 拡張ポイント）
  - execution/                — 発注/実行管理（空 __init__.py / 拡張ポイント）
  - monitoring/               — モニタリング（現在は empty module）

---

## 運用上の注意点

- J-Quants API のレート制限を尊重するため、fetch 関数は内部でスロットリングしています。大量取得やバックフィル実行時は時間に注意してください。
- DuckDB スキーマの初期化は冪等化されていますが、初回は init_schema を呼び出してください。
- ニュース収集に際しては外部 URL を扱うため SSRF 対策・サイズ制限等の保護が組み込まれています。追加のフィードを登録する際は信頼できるソースを設定してください。
- 本ライブラリは「データ取得・研究」層に重点を置き、実際の証券会社への発注実装（kabuステーション接続のラッパーや実運用のリスク管理）は別実装を想定しています。

---

## 貢献・開発

- 新しい機能やバグ修正は Pull Request をお願いします。
- テストコード（unit / integration）を追加してから PR を作成してください。ETL / 外部 API を含む機能はモックやインテグレーションテストの整備を推奨します。

---

README に書かれている API 名やモジュールを起点に、目的に応じてスクリプトやバッチを実装してください。質問や具体的な使い方（例: フル ETL スクリプト、ニュースフィードの追加方法、ファクターの拡張など）があれば、必要に応じて具体例を提示します。