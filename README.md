# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys の README（日本語）。

概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株を対象としたデータ収集・品質管理・ETL・監査・発注基盤のための Python モジュール群です。  
主要な設計方針は次のとおりです。

- J-Quants API や RSS フィードからのデータ取得を行い、DuckDB に冪等的に格納する
- API レート制御、リトライ、トークン自動リフレッシュなど堅牢な HTTP 処理
- ニュース収集で SSRF / XML Bomb 対策やトラッキングパラメータ削除を実施
- ETL（差分取得、バックフィル、品質チェック）を実装
- 監査ログ（シグナル→発注→約定のトレース）を独立したスキーマで管理
- データ品質チェック（欠損、スパイク、重複、日付不整合）の自動検出

パッケージはモジュール分割されており、ライブラリとして他のアプリケーションから呼び出すことを想定しています。

---

## 主な機能一覧

- 環境設定管理
  - .env/.env.local からの自動ロード（プロジェクトルート判定）
  - 必須環境変数の取得ラッパ（Settings）
- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 日足（OHLCV）、四半期財務、JPX カレンダーなどを取得
  - レートリミット（120 req/min）制御、指数バックオフリトライ、401時のトークン自動更新
  - DuckDB への冪等保存（ON CONFLICT 句を利用）
- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィード収集、記事ID生成（URL 正規化→SHA-256）、本文前処理
  - SSRF/XML 攻撃対策、サイズ上限、重複排除、銘柄コード抽出と紐付け
- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義・初期化
- ETL パイプライン (`kabusys.data.pipeline`)
  - 差分取得、バックフィル、品質チェックの一括実行（run_daily_etl）
- マーケットカレンダー管理 (`kabusys.data.calendar_management`)
  - 営業日判定、前後営業日取得、夜間カレンダー更新ジョブ
- 監査ログ（audit） (`kabusys.data.audit`)
  - signal_events / order_requests / executions の監査スキーマと初期化
- 品質チェック (`kabusys.data.quality`)
  - 欠損、スパイク、重複、日付整合性チェック（run_all_checks）
- その他
  - strategy/, execution/, monitoring/ のプレースホルダモジュール（拡張用）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに | を使用しているため）
- Git 等でリポジトリをクローンしていること

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール
   - 必要な主要パッケージ（例）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトで requirements.txt / pyproject.toml がある場合はそれに従ってください）

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成してください。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - オプション:
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
     - LOG_LEVEL=DEBUG|INFO|...  （デフォルト: INFO）
     - DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
     - SQLITE_PATH=data/monitoring.db
   - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース初期化（例）
   - Python REPL やスクリプト内で:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")

---

## 使い方（基本例）

以下に代表的な操作例を示します。

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- J-Quants トークン取得 / データ取得
  - from kabusys.data import jquants_client as jq
  - id_token = jq.get_id_token()  # settings.jquants_refresh_token を利用
  - records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  - jq.save_daily_quotes(conn, records)

- 日次 ETL 実行（カレンダー取得→株価→財務→品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # 戻り値は ETLResult（詳細を保持）

- RSS ニュース収集 / 保存
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  - results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})

- 品質チェック単体実行
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=None)

- カレンダーヘルパー
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
  - is_trading_day(conn, date.today())
  - next_trading_day(conn, date.today())

- 監査スキーマ初期化（監査ログを別DBで管理したい場合）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

注意点
- HTTP は標準ライブラリ urllib を使用しており、J-Quants へは rate limiter / retry が組み込まれています。
- ニュース収集時は外部URLを検証し、プライベートアドレス等へのアクセスをブロックします。
- ETL の各ステップは独立してエラーを処理し、部分的失敗でも可能な限り処理を続行します。結果は ETLResult に記録されます。

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション等の API パスワード
- SLACK_BOT_TOKEN — Slack 通知の Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合は "1"

（プロジェクトに .env.example がある想定です。設定漏れ時は Settings プロパティが ValueError を上げます。）

---

## ディレクトリ構成

リポジトリ内の主なファイル・モジュール構成は次のとおりです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得・保存）
    - news_collector.py    — RSS ニュース収集・保存・銘柄抽出
    - schema.py            — DuckDB スキーマ定義と初期化
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — カレンダー更新・営業日判定
    - audit.py             — 監査ログスキーマと初期化
    - quality.py           — データ品質チェック
  - strategy/
    - __init__.py          — 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py          — 発注実行モジュール（拡張ポイント）
  - monitoring/
    - __init__.py          — 監視用モジュール（拡張ポイント）

この構成により、データ収集・ETL・監査・品質チェック・戦略/実行の責務を分離しています。

---

## 開発メモ / 注意事項

- Python 3.10 以上を使用してください（型ヒントに union operator | を利用）。
- ネットワーク・外部 API に対する堅牢性（レート制御、リトライ、トークン更新）を優先して実装していますが、API の仕様変更や認証情報の有効期限には注意してください。
- DuckDB のファイルはデフォルトで data/ 配下に生成されます。バックアップやローテーションは運用側で設計してください。
- ニュース収集では最大応答サイズや圧縮解凍後のサイズも検査しており、安全性を重視しています。
- テスト実行や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを抑制できます。

---

README に書かれていない細かな API（各関数の引数や戻り値、エラー挙動など）は、ソースの docstring を参照してください。必要であれば、サンプルスクリプトや拡張のための追加ドキュメントも作成できます。