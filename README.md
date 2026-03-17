# KabuSys

日本株向け自動売買システムの基盤ライブラリ。データ取得（J‑Quants）、ETL、データ品質チェック、ニュース収集、監査ログ（発注→約定のトレース）など、量的取引システムの基礎機能を提供します。

バージョン: 0.1.0

---

## 主要機能（概要）

- J‑Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーをページネーション対応で取得
  - API レート制御（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録、Look‑ahead バイアス対策を考慮

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit レイヤーのテーブルDDLを定義
  - init_schema, init_audit_schema などで冪等に初期化可能

- ETL パイプライン
  - 差分更新（最終取得日参照）、バックフィル（後出し修正吸収）、品質チェックを一連で実行
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実装し、問題は一覧で返却

- ニュース収集
  - RSS フィードから記事取得、前処理、記事ID（正規化URL→SHA‑256先頭32文字）で冪等保存
  - SSRF / XML Bomb / Gzip Bomb 等の攻撃対策を実装
  - 銘柄コード抽出と news_symbols への紐付け（既知コードセットを利用）

- 監査ログ（Audit）
  - signal → order_request → execution の階層でトレーサビリティを保持するテーブル群を提供
  - 発注の冪等キーやステータス管理を想定

- 設定管理
  - .env / .env.local / OS 環境変数を自動ロード（優先度: OS > .env.local > .env）
  - テスト用に自動ロードを無効にする環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## 前提（Prerequisites）

- Python 3.10 以上（型注釈に | を使用）
- インストール依存パッケージ（例）
  - duckdb
  - defusedxml
- その他標準ライブラリ（urllib, gzip, logging 等）

例: 必要最小パッケージはプロジェクトの packaging に依存しますが、開発環境では次を入れておくと良いです。

pip install duckdb defusedxml

---

## 環境変数（主な必須 / 任意）

必須（実行に必要なもの）
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルト値あり）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動 .env ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

簡易の .env 例（プロジェクトルートに置く）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. レポジトリをクローン／チェックアウト
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  # Windows は .venv\Scripts\activate
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合は pip install -e . など）
4. 環境変数を設定（.env または OS 環境変数）
5. DuckDB スキーマを初期化
   - 下記「使い方」を参照

---

## 使い方（主要 API の例）

Python REPL やスクリプトから簡単に使えます。

- 設定取得（settings）
  - from kabusys.config import settings
  - settings.jquants_refresh_token などで環境変数にアクセス（未設定時は例外）

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
  - :memory: を渡すとインメモリ DB
  - 監査テーブルは init_audit_schema で追加:
    - from kabusys.data.audit import init_audit_schema
    - init_audit_schema(conn)

- J‑Quants からのデータ取得（直接呼び出し）
  - from kabusys.data import jquants_client as jq
  - id_token = jq.get_id_token()  # トークン取得（自動リフレッシュやリトライを含む）
  - quotes = jq.fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
  - saved = jq.save_daily_quotes(conn, quotes)

  備考: fetch_* 系はページネーション対応、save_* は DuckDB へ冪等保存（ON CONFLICT）

- ETL の実行（日次パイプライン）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # デフォルトは本日を対象にカレンダー先読み・品質チェックする
  - result は ETLResult オブジェクト（fetched/saved 数、品質問題、エラー等を保持）

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes=set([...]))
  - 既定では DEFAULT_RSS_SOURCES から取得。known_codes を渡すと銘柄紐付けを実行。
  - また個別に fetch_rss / save_raw_news / save_news_symbols を使って制御可能

- 品質チェック個別呼び出し
  - from kabusys.data import quality
  - issues = quality.run_all_checks(conn, target_date=..., reference_date=..., spike_threshold=0.5)

- 監査テーブルの初期化（独立 DB）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

注意点:
- J‑Quants のレート制御（120 req/min）とリトライロジックはクライアント側で実装済みです。
- news_collector は外部からの不正 URL（非 http/https、プライベートIP、リダイレクト先など）を検査します。
- ETL は個々のステップを独立してエラーハンドリングするため、部分的に失敗しても他ステップは継続します。重大な問題は ETLResult.errors に集約されます。

---

## 主要モジュールとディレクトリ構成

（パッケージは src/kabusys 配下）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/設定読み込みと Settings
  - data/
    - __init__.py
    - jquants_client.py            — J‑Quants API クライアント（取得・保存）
    - news_collector.py           — RSS ニュース収集・保存・銘柄抽出
    - schema.py                   — DuckDB スキーマ定義・初期化
    - pipeline.py                 — ETL パイプライン（差分取得・品質チェック）
    - audit.py                    — 監査ログ（信号→発注→約定トレーサビリティ）
    - quality.py                  — データ品質チェック
  - strategy/
    - __init__.py                 — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                 — 発注/ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py                 — 監視/メトリクス（拡張ポイント）

DDL／テーブル群:
- Raw 層: raw_prices, raw_financials, raw_news, raw_executions
- Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature 層: features, ai_scores
- Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- Audit 層: signal_events, order_requests, executions（init_audit_schema で追加）

---

## 運用上の注意／設計メモ

- 環境ロード
  - プロジェクトルートは .git または pyproject.toml を基準に自動検出。テストなどで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - 読み込み優先度: OS env > .env.local > .env

- セキュリティ / 安全策
  - news_collector は SSRF、XML Bomb、Gzip Bomb を考慮して実装されています（スキーム検証、プライベートIPチェック、受信サイズ上限、defusedxml を使用）。
  - J‑Quants クライアントは 401 時のトークン更新を一度だけ試み、ネットワークエラーや率制御に対して指数バックオフを行います。

- DB の冪等性
  - raw データの保存関数は ON CONFLICT DO UPDATE / DO NOTHING を活用して冪等性を担保します（ETL の再実行やバックフィルに対応）。

---

## 参考（簡単な実行フロー例）

1. 初期化（対話的に）
```py
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)
print(result.to_dict())
```

2. ニュース収集（既知コードセットあり）
```py
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

---

必要であれば、README に「デバッグ方法」「テストの実行方法」「CI 用シークレットの設定例」などの追記も可能です。どの項目を詳細化したいか教えてください。