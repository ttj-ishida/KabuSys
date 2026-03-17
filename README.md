# KabuSys

日本株向け自動売買プラットフォームのライブラリ（KabuSys）。  
J-Quants API や RSS ニュースを取り込み、DuckDB に保存・整備して戦略層・実行層に渡すためのデータ基盤・ETL・監査・品質チェック機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（基本例）
- 環境変数（.env）
- セキュリティ・設計上の注意点
- ディレクトリ構成

---

プロジェクト概要
- J-Quants API から株価日足・財務データ・市場カレンダーを取得し、DuckDB に冪等的（idempotent）に保存します。
- RSS フィードからニュースを収集して前処理・正規化・銘柄紐付けを行い、raw_news / news_symbols に保存します。
- ETL パイプライン（差分更新・バックフィル・品質チェック）を提供して、日次ジョブでデータを更新します。
- 監査ログ（シグナル→発注→約定のトレース）用スキーマを提供します。
- データ品質チェック（欠損・スパイク・重複・日付不整合）を実装し、ETL 後に検査できます。

主な機能一覧
- J-Quants クライアント
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - 内部でレート制限（120 req/min）、再試行、401トークン自動リフレッシュを実装
- DuckDB スキーマ管理
  - init_schema(db_path) — Raw / Processed / Feature / Execution 層のテーブルとインデックスを作成
  - get_connection(db_path)
- ETL パイプライン
  - run_daily_etl(conn, target_date=None, ...) — カレンダー取得 → 株価 → 財務 → 品質チェックの一括実行
  - run_prices_etl / run_financials_etl / run_calendar_etl — 個別ジョブ
- ニュース収集
  - fetch_rss(url, source, timeout=30) — RSS 取得と記事前処理（URL 正規化・tracking パラメータ除去）
  - save_raw_news(conn, articles) — raw_news に冪等保存（INSERT ... RETURNING）
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30) — ソースごとに収集・保存・銘柄紐付け
  - SSRF 対策 / XML パースの安全化 / レスポンスサイズ制限 等の保護機構を実装
- 監査（Audit）
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)
  - 監査用テーブル（signal_events / order_requests / executions 等）を提供
- データ品質チェック
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - check_missing_data, check_spike, check_duplicates, check_date_consistency

セットアップ手順
前提
- Python 3.10 以上（typing の | 演算子や型注釈の利用に対応）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
（実際の requirements.txt はプロジェクトに応じて用意してください）

例: 仮想環境を作成して依存をインストール
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

プロジェクトの初期化（DuckDB スキーマ作成）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # data/ ディレクトリがなければ自動作成
```

監査ログ用 DB 初期化（分離して使う場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

環境変数のロード
- パッケージはプロジェクトルート（.git または pyproject.toml を起点）から .env を自動で読み込みます。
- 自動読み込みを無効化する場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主要設定は kabusys.config.settings から参照できます（例: settings.jquants_refresh_token）。

使い方（基本例）
1) 設定を用意する（.env をルートに置く。例は下記参照）
2) DB を初期化して ETL を実行
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # デフォルトで今日の ETL を実行
print(result.to_dict())
```

3) ニュース収集を実行（known_codes を与えて銘柄紐付けを行う例）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 有効な銘柄コードリストを事前に用意（例: set(["7203","6758", ...]))
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

4) 監査テーブルを初期化（既存の conn に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

環境変数（.env）
自動ロードされる主な環境変数（kabusys.config.Settings で参照される）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン（通知等に利用する場合）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL (任意) — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）

簡易 .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動 .env ロードの挙動
- 自動読み込み順: OS 環境変数 > .env.local > .env
- .env.local は .env の上書きに使用されます
- プロジェクトルートが特定できない場合は自動ロードをスキップします

セキュリティ・設計上の注意点
- J-Quants クライアントはレート制限（120 req/min）とリトライ（最大3回）を組み込んでいます。429/408/5xx などは指数バックオフや Retry-After を尊重します。401 を受けた場合はトークンを自動リフレッシュして 1 回リトライします。
- ニュース収集は以下の安全対策を実装:
  - defusedxml を使用して XML Bomb 等を防止
  - レスポンスの最大バイト数制限（デフォルト 10 MB）
  - リダイレクト先のスキーム検証・プライベートホスト（SSRF）ブロック
  - URL 正規化時にトラッキングパラメータを削除
- DuckDB への保存は多くが ON CONFLICT DO UPDATE / DO NOTHING を利用して冪等性を担保しています。
- 監査ログは削除しない前提（FK は ON DELETE RESTRICT）、タイムスタンプは UTC 保存を推奨しています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得＋保存ロジック）
    - news_collector.py       — RSS ニュース収集 / 正規化 / 保存
    - schema.py               — DuckDB スキーマ定義 & init_schema
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  — 市場カレンダー管理（営業日判定等）
    - audit.py                — 監査ログスキーマ初期化
    - quality.py              — データ品質チェック
    - (その他 ETL/ユーティリティ)
  - strategy/                 — 戦略層（パッケージ用意、実装はここに追加）
  - execution/                — 発注/実行層（パッケージ用意、実装はここに追加）
  - monitoring/               — モニタリング（用意のみ）

補足
- パッケージは src レイアウト（src/kabusys）で配置されています。ローカルでインストールする場合は setuptools/pyproject を使い `pip install -e .` などで開発インストールしてください。
- ETL の実行は Cron / Airflow / 任意のジョブスケジューラから定期起動する想定です。run_daily_etl は各ステップで例外を拾って処理を続行するため、部分的な障害があっても可能な範囲でデータを収集します。重大な品質問題は QualityIssue として返却されます。
- DuckDB の初期化は init_schema を推奨します。既存 DB に対しては get_connection を使い、必要に応じて audit スキーマを追加してください。

ライセンス・貢献
- 本リポジトリのライセンス情報や貢献ルール（CONTRIBUTING.md）がある場合はプロジェクトルートを参照してください。

---

必要であれば README にサンプル .env.example、CI 実行方法、実運用での監視・アラート例、Slack 通知（settings での Slack 設定利用法）などの追記を行います。どの情報を優先して追加しますか？