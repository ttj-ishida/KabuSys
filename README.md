# KabuSys — 日本株自動売買プラットフォーム（README）

このリポジトリは「KabuSys」と呼ばれる日本株向けの自動売買／データプラットフォームのコアライブラリ実装です。データ取得（J-Quants）、DuckDB ベースのスキーマ・ETL、ニュース収集、ファクター計算（リサーチ用）や監査ログなどを含む設計になっています。

## プロジェクト概要
KabuSys は次の目的を持ったモジュール群を提供します。

- J-Quants API からの価格・財務・マーケットカレンダー取得（レート制御・リトライ・トークン管理）
- DuckDB を使ったデータスキーマ定義と冪等な保存
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と記事→銘柄紐付け
- ファクター計算（モメンタム、ボラティリティ、バリュー等）および特徴量探索（IC/統計）
- 監査ログ（信号→発注→約定のトレーサビリティ）
- 環境設定の集中管理（.env 自動ロード、必須/任意設定）

設計方針として、本ライブラリは本番口座や発注 API を直接呼び出さないモジュール（研究/データ層）と、発注・監査層を分離して実装しています。標準ライブラリのみで可能な処理は外部ライブラリ依存を最小化するように実装されていますが、DuckDB や defusedxml 等は必要です。

## 主な機能一覧
- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルート検出：.git / pyproject.toml）
  - 必須設定のチェック（例: JQUANTS_REFRESH_TOKEN）
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL 検証
- データ取得（kabusys.data.jquants_client）
  - 日足、四半期財務、マーケットカレンダーの取得（ページネーション対応）
  - レートリミット、リトライ、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存ユーティリティ（ON CONFLICT 処理）
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層の DuckDB DDL を定義・初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日を基に差分を計算）、バックフィル、品質チェックの統合
  - run_daily_etl 等の便利関数
- 品質チェック（kabusys.data.quality）
  - 欠損値、スパイク（前日比閾値）、重複、日付不整合を検出
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF 保護、gzip サイズ上限、XML パースに defusedxml を使用）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等保存
  - 銘柄コード抽出（4桁数字）と news_symbols への紐付け
- リサーチ（kabusys.research）
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
  - z-score 正規化ユーティリティの公開
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル初期化とインデックス
- 補助ユーティリティ（kabusys.data.stats, calendar_management, features...）

## 必要条件（予定）
- Python 3.10+
- pip パッケージ:
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt がある場合はそれを参照してください。ここに挙げたのはコードから明示された主要依存です。）

## セットアップ手順

1. リポジトリをクローン
   - 任意の場所で git clone を行ってください。

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （開発インストール）pip install -e .

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
   - 主要な必須環境変数（後述）を .env に設定してください。

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
   - これで必要なテーブルとインデックスが作成されます。

## 環境変数（主なもの）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注関連がある場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル

任意・デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

簡単な .env の例（.env.example を参照して作成してください）:
JQUANTS_REFRESH_TOKEN="your_refresh_token"
KABU_API_PASSWORD="your_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C0123456789"
KABUSYS_ENV=development
LOG_LEVEL=INFO

## 使い方（よく使う操作の例）

- スキーマの初期化
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得＋品質チェック）
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュース収集ジョブの実行
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  # known_codes は銘柄抽出に使う有効銘柄コードの集合（例: {"7203","6758",...}）
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
  print(res)

- J-Quants から日足取得（低レベル）
  from kabusys.data.jquants_client import fetch_daily_quotes
  quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))

- リサーチ / ファクター計算
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  res = calc_momentum(conn, target_date=date(2024,1,31))

- z-score 正規化ユーティリティ
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, columns=["mom_1m", "mom_3m"])

- 環境設定の読み取り
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path

## 主要 API の注意点・設計メモ
- jquants_client は API レート制限（120 req/min）を尊重するため内部で固定間隔レートリミッタを使用します。リトライや 401 自動リフレッシュのロジックも含まれます。
- ニュース収集は SSRF 対策・サイズ制限（10MB）・XML サニタイズを実装しています。記事 ID は正規化 URL のハッシュで冪等性を保ちます。
- DuckDB の INSERT は冪等（ON CONFLICT）で設計されており、外部から複数回ロードしても同一キーは上書きされます。
- calendar_management モジュールは market_calendar が未取得のケースを考慮した曜日ベースのフォールバックを持ちます。
- audit モジュールは監査ログ用の専用 DDL を提供し、UTC タイムゾーンを前提としています。

## ディレクトリ構成（抜粋）
リポジトリは src レイアウトの Python パッケージとして構成されています。主要ファイルは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得＋保存）
    - news_collector.py           — RSS ニュース収集と保存ロジック
    - schema.py                   — DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - features.py                 — 特徴量ユーティリティの公開
    - calendar_management.py      — マーケットカレンダー管理
    - audit.py                    — 監査ログ用スキーマ初期化
    - etl.py                      — ETL 公開インターフェース
    - quality.py                  — データ品質チェック
    - stats.py                    — z-score など統計ユーティリティ
  - research/
    - __init__.py
    - feature_exploration.py      — 将来リターン・IC・統計サマリ等
    - factor_research.py          — momentum/volatility/value の計算
  - strategy/                      — 戦略層（初期化済み）
  - execution/                     — 発注実行層（初期化済み）
  - monitoring/                    — モニタリング関連（初期化済み）

この README にある API 名・関数は主要なものを抜粋しています。詳細は各モジュールの docstring を参照してください。

## 開発・テストに関するヒント
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から行われます。テストで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に作成されます。テストでは ":memory:" を使ってインメモリ DB に接続できます（schema.init_schema(":memory:")）。
- ニュース RSS 取得関数や HTTP 呼び出しは内部の _urlopen 等をモックしてテスト可能です（コメントにもその注記あり）。

---

ご不明点があれば、どの機能（ETL、ニュース収集、ファクター計算、監査等）についてサンプルや詳細をもっと載せるか教えてください。README の具体的なコマンドや .env.example をより詳しく作成することもできます。