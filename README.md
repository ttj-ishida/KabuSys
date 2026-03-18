KabuSys
======

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
J-Quants や RSS ニュースなど外部データを取得して DuckDB に保存し、品質チェックや戦略／発注のためのスキーマ・ユーティリティを提供します。

主な目的
- J-Quants API から株価・財務・マーケットカレンダーを安全に取得して保存
- RSS フィードからニュースを収集・正規化して保存し、銘柄紐付けを行う
- ETL（差分更新）や品質チェック、カレンダー管理、監査ログスキーマを提供
- 発注・約定・ポジション管理のためのスキーマ（Execution / Audit 層）

特徴
- J-Quants API クライアント
  - レートリミット制御（120 req/min）
  - リトライ（指数バックオフ）、401 の自動リフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead バイアスを防止
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集
  - RSS を安全に取得（defusedxml、SSRF 対策、レスポンスサイズ制限等）
  - URL 正規化（トラッキングパラメータ除去）、SHA-256 による記事ID生成で冪等性
  - raw_news / news_symbols への効率的なバルク保存
- データ基盤（DuckDB）スキーマ
  - Raw / Processed / Feature / Execution 層を定義
  - 監査ログ（signal_events / order_requests / executions 等）を別モジュールで初期化可能
- ETL パイプライン
  - 差分更新（最終取得日を見て必要範囲のみ取得）、バックフィル設定あり
  - 品質チェックモジュール（欠損・スパイク・重複・日付不整合検出）
- カレンダー管理
  - market_calendar ベースで営業日判定、next/prev_trading_day、範囲取得等を提供

必要条件（想定）
- Python 3.10+
- パッケージ依存（主なもの）:
  - duckdb
  - defusedxml
  - （標準ライブラリ: urllib, datetime, logging, gzip, hashlib, re, ipaddress, socket 等）

インストール（開発時の例）
- 仮想環境を作成して依存をインストールしてください。パッケージ化されている前提がないため、ソース直下で pip install -e . や requirements.txt を用いることを想定します。

環境変数 / 設定
- 自動ロード:
  - パッケージはプロジェクトルート（.git または pyproject.toml を探索）にある .env および .env.local を自動で読み込みます（OS 環境変数を上書きしない / .env.local は上書き）。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主要な環境変数（必須・任意）
  - JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD (必須)   : kabuステーション API パスワード
  - KABU_API_BASE_URL (任意)  : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN (必須)    : Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID (必須)   : Slack 通知先チャンネル ID
  - DUCKDB_PATH (任意)        : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH (任意)        : SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV (任意)        : 実行環境 ("development" | "paper_trading" | "live")（デフォルト "development"）
  - LOG_LEVEL (任意)          : ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")（デフォルト "INFO"）

セットアップ手順（例）
1. 仮想環境作成・依存インストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれに従う）

2. .env の準備
   - リポジトリルートに .env を作成し、上記の必須環境変数を設定
   - 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

3. DuckDB スキーマ初期化
   - 下記のサンプルコードで DB を初期化します（初回のみ）。
   - 例:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

4. （任意）監査ログ用 DB 初期化
   - 監査テーブルのみ別 DB に作る場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

使い方（代表的な API）
- J-Quants 認証トークン取得
  - from kabusys.data.jquants_client import get_id_token
  - id_token = get_id_token()  # settings.jquants_refresh_token を利用して POST で取得

- スキーマ初期化（DuckDB）
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を省略すると本日が対象
  - result は ETLResult オブジェクトで、fetched / saved / quality_issues / errors を確認できます

- ニュース収集ジョブ（RSS を fetch → raw_news に保存 → 銘柄紐付け）
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
  - sources を省略するとデフォルトの RSS ソースが使われます（DEFAULT_RSS_SOURCES）

- 市場カレンダー夜間更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)

- 品質チェック個別実行
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=None)

運用上の注意（抜粋）
- J-Quants のレート制限（120 req/min）を尊重するため、ライブラリ内部でスロットリングを行います。大量の取得や同時実行には注意してください。
- RSS 取得は SSRF / gzip bomb / XML 攻撃対策を実装していますが、外部 URL を扱うため運用環境ではネットワークポリシーを検討してください。
- DuckDB のスキーマは ON CONFLICT / RETURNING を活用して冪等性を保ちます。既存データの扱い（上書き方針）は関数ごとに異なりますので実行前にログを確認してください。
- KABUSYS_ENV を "live" に設定すると本番相当の振る舞いを期待するコードパスが有効になることを想定しています（実装により安全対策を別途確認してください）。

ディレクトリ構成（本リポジトリの主なファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数読み込み・Settings クラス（必須設定の取得、.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py     — RSS ニュース取得・前処理・DB 保存・銘柄抽出
    - pipeline.py           — ETL パイプライン（差分更新・品質チェック統合）
    - schema.py             — DuckDB スキーマ定義と初期化ロジック
    - calendar_management.py— 市場カレンダー管理（営業日判定やバッチ更新）
    - audit.py              — 監査ログ（signal/order/execution）スキーマと初期化
    - quality.py            — データ品質チェックモジュール
  - strategy/
    - __init__.py           — 戦略層（プレースホルダ／拡張ポイント）
  - execution/
    - __init__.py           — 発注実行層（プレースホルダ／拡張ポイント）
  - monitoring/
    - __init__.py           — 監視・メトリクス用（プレースホルダ）
- pyproject.toml, README.md 等（プロジェクトルートに存在する想定）

開発者向けメモ
- モジュールはテスト容易性を考慮して設計されています（id_token 注入、_urlopen のモック差替え等）。
- ログは各モジュールで logger = logging.getLogger(__name__) を使っており、呼び出し元で logging.basicConfig / dictConfig して運用してください。
- DuckDB のトランザクションは明示的に使用している箇所があります（news_collector の一括挿入等）。複数スレッド／プロセスから同一ファイルにアクセスする際は注意してください。

貢献・拡張
- strategy/ や execution/ 下に実際の売買戦略・ブローカー API 連携実装を追加してください。
- モニタリング、アラート（Slack 送信など）は monitoring モジュールに追加する想定です。

ライセンス
- 本コードのライセンス情報はリポジトリの LICENSE を参照してください（ここには明示されていません）。

---

ご不明点や README に追加したい具体的な使用例（cron での ETL スケジュール例や Docker 化手順など）があれば教えてください。それに合わせて README を拡張します。