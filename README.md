# KabuSys

日本株向け自動売買基盤ライブラリ / ツール群

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォームを構成するライブラリ群です。  
主に以下の機能を提供します。

- 外部データ取得（J-Quants API から株価、財務、JPXカレンダー取得）
- RSS ベースのニュース収集と記事の前処理・DB保存
- DuckDB を使ったデータスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL （差分取得・バックフィル・品質チェック）パイプライン
- マーケットカレンダー管理（営業日判定・前後営業日取得等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマ
- データ品質チェック（欠損、スパイク、重複、日付不整合検出）

設計上の主要ポイントは「レート制御・堅牢なリトライ・冪等性・SSRF 等のセキュリティ対策・品質チェックの分離」です。

---

## 主な機能一覧

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - API レートリミット（120 req/min）を守る固定間隔スロットリング
  - 再試行（指数バックオフ）/ 401 時の自動トークンリフレッシュ / ページネーション対応
  - 取得時刻（fetched_at）を UTC で保持、DuckDB へ冪等保存（ON CONFLICT）

- ニュース収集（RSS）
  - RSS フィードから記事収集、URL 正規化、トラッキングパラメータ除去
  - 記事ID は正規化URL の SHA-256 を短縮して使用（冪等性）
  - defusedxml を用いた XML 攻撃防御、SSRF 防御（スキーム検査・プライベートIP 拒否）
  - 受信サイズ上限・gzip 対応・DB へのチャンク挿入とトランザクション管理
  - 記事→銘柄コード紐付け（テキストから 4 桁銘柄抽出）機能

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - 初期化関数（init_schema / init_audit_db）で一括作成
  - インデックス定義、外部キー考慮の作成順序

- ETL パイプライン
  - 差分取得（DB の最終取得日を参照）、バックフィル、保存
  - 市場カレンダーを先に取得して営業日に調整
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実行して結果を返却

- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - DB データがない場合は曜日ベースのフォールバック（主に土日除外）

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルによるトレーサビリティ
  - order_request_id による冪等制御、UTC タイムゾーン固定

---

## セットアップ手順

前提:
- Python 3.9+（typing の union 表記等を使用）
- Git リポジトリのルートに .env / .env.local を置くことで環境変数を自動読み込み（後述）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必要な主要ライブラリ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

4. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に .env または .env.local を置くと、自動的に読み込まれます。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID（必須）

オプション/デフォルト
- KABU_API_BASE_URL     : kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 実行環境（development / paper_trading / live） デフォルト: development
- LOG_LEVEL             : ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）デフォルト: INFO

.env のパースはシンプルな実装を備え、export 付きや引用符付き値、コメント対応を行います。詳細は kabusys.config を参照してください。

---

## 使い方（サンプル）

以下は主なモジュールの利用例です。Python スクリプトや REPL で実行できます。

- DuckDB スキーマ初期化（最初に一度だけ）
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
  - print(result.to_dict())

- J-Quants トークン取得 / 株価取得
  - from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  - token = get_id_token()  # settings.jquants_refresh_token を使用
  - records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- ニュース収集ジョブ（RSS を収集して DuckDB に保存）
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, known_codes={"7203","6758"})
  - print(results)  # {source_name: 新規保存件数}

- 監査ログ初期化（監査専用DB）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

注意点・設計に関する補足:
- jquants_client はモジュールレベルで ID トークンをキャッシュし、401 受信時は一度だけ自動リフレッシュして再試行します。
- ニュース収集は SSRF / Gzip Bomb / 大きすぎるレスポンスに対する保護を備えています。
- DuckDB への保存は ON CONFLICT ... DO UPDATE（あるいは DO NOTHING）で冪等に実行されます。
- ETL の各ステップは独立して例外処理されるので、1 ステップ失敗でも残りは継続されます。結果は ETLResult に収集されます。

---

## ディレクトリ構成

主要ファイル/モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存）
    - news_collector.py               — RSS ニュース収集・DB保存
    - schema.py                       — DuckDB スキーマ定義・初期化
    - pipeline.py                     — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py          — マーケットカレンダー管理（営業日判定等）
    - audit.py                        — 監査ログ（シグナル→発注→約定）
    - quality.py                      — データ品質チェック
    - audit.py
  - strategy/
    - __init__.py                     — 戦略層のエントリ（将来的に実装）
  - execution/
    - __init__.py                     — 発注実行層（将来的に実装）
  - monitoring/
    - __init__.py                     — 監視モジュール（将来的に実装）

その他:
- .env / .env.local（プロジェクトルートに配置して環境変数を管理）
- data/（デフォルトで生成される DB ファイル用ディレクトリ）

---

## 注意事項 / 運用のヒント

- 本ライブラリは実際の資金での運用を想定する場合、KABUSYS_ENV を `paper_trading` や `live` に切り替えて運用する前に、十分なテストとレビューを行ってください。
- J-Quants の API レート制限（120 req/min）を守るため、jquants_client のレートリミッタを尊重してください。複数プロセスから同時にアクセスするとレート超過になる可能性があります。
- DuckDB ファイルは単一プロセスでの読み書きを前提とする運用が簡単です。複数プロセスで同時書き込みする場合はロックや外部同期が必要になることがあります。
- ニュース収集では外部 RSS を取得するため、ネットワークやフィードの変更によりパースエラーが発生することがあります。fetch_rss はエラーをログに出力して空リストを返す設計です。

---

## さらに詳しく / ソース参照

各機能の詳細は該当モジュールの docstring と実装を参照してください。特に以下を推奨:

- kabusys.config: .env 自動読み込みと settings の利用方法
- kabusys.data.jquants_client: API リトライ / トークン管理 / 保存ロジック
- kabusys.data.news_collector: RSS 前処理 / SSRF 対策 / DB 挿入の実装
- kabusys.data.schema: 全テーブル定義と初期化手順
- kabusys.data.pipeline: 日次 ETL のフローと ETLResult

---

README に記載の無い点や具体的な利用例（CLI ラッパーやデプロイ手順、CI/CD の設定など）が必要であれば、実行環境や目的（ローカル開発 / 本番運用 / コンテナ化 等）を教えてください。それに合わせてサンプルスクリプトやデプロイ手順を追加します。