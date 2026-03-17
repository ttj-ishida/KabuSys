# KabuSys

日本株自動売買プラットフォームのコアライブラリ。  
データ取得（J-Quants）、ETLパイプライン、マーケットカレンダー管理、ニュース収集、データ品質チェック、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムの基盤ライブラリです。主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新）
- DuckDB を用いた 3 層（Raw / Processed / Feature）スキーマの初期化と永続化
- RSS からのニュース収集と銘柄紐付け（SSRF対策・サイズ制限・XMLサニタイズ）
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定・next/prev/trading days）
- 監査ログ（signal → order_request → executions のトレース用テーブル群）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上のポイント:
- API レート制限（120 req/min）を尊重する RateLimiter 実装
- 重要処理は冪等性を担保（DuckDB への INSERT は ON CONFLICT で更新）
- セキュリティ対策（XML の defusedxml、SSRF リダイレクト対策、応答サイズ上限など）
- トークン自動リフレッシュ（401 の際に refresh token で再取得）

---

## 機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ保存する save_* 関数（冪等）
  - レート制御・リトライ・トークンキャッシュ
- data.schema
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(db_path) で初期化
- data.pipeline
  - run_daily_etl: 市場カレンダー更新 → 株価ETL → 財務ETL → 品質チェック（オプション）
  - 差分更新・バックフィル機能
- data.news_collector
  - RSS 取得（gzip 対応・XML サニタイズ・SSRF対策）
  - raw_news への保存（チャンクINSERT、INSERT ... RETURNING）
  - 記事ID生成（URL正規化→SHA-256先頭32文字）、銘柄コード抽出・紐付け
- data.calendar_management
  - 営業日判定 / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による夜間差分更新
- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks でまとめて実行
- data.audit
  - 監査用テーブル群の初期化（init_audit_schema / init_audit_db）
- config
  - .env 自動読み込み（プロジェクトルートの .env / .env.local を読み込み）
  - Settings クラス経由で環境変数取得（必須キーは _require で検査）

---

## 前提条件

- Python 3.10+（型アノテーションに union | を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリで HTTP/URL 処理や logging を利用

（プロジェクトの pyproject.toml / requirements.txt に依存関係を追加してください）

---

## セットアップ手順

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - pip install duckdb defusedxml

   （プロジェクトに pyproject.toml があれば pip install -e . や pip install -r requirements.txt を利用）

3. 環境変数 (.env) を用意
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトで:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")

---

## 必要な環境変数

（Settings クラスで参照される主要キー）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL (省略可) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用（本ライブラリではトークンが期待される）
- SLACK_CHANNEL_ID (必須) — Slack チャンネルID
- DUCKDB_PATH (省略可) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (省略可) — デフォルト: data/monitoring.db
- KABUSYS_ENV (省略可) — development | paper_trading | live（デフォルト development）
- LOG_LEVEL (省略可) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

例 .env（最小）
- JQUANTS_REFRESH_TOKEN=xxxxx
- KABU_API_PASSWORD=xxxxx
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567

---

## 使い方（簡単なコード例）

以下は主要なユースケースの簡単な例です。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL の実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.data import pipeline
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- J-Quants から日足データを直接取得して保存
```python
from kabusys.data import jquants_client as jq
# id_token を明示的に渡すことも可能。省略時は設定された refresh token を使って自動取得
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

- RSS ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 銘柄抽出に使う有効な銘柄コードのセット（例: prices テーブルから読み取る）
results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(results)  # {source_name: 新規保存件数}
```

- 監査スキーマの初期化（既存の接続に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

- マーケットカレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
is_trade = is_trading_day(conn, date(2024,3,20))
next_day = next_trading_day(conn, date(2024,3,20))
```

---

## ディレクトリ構成

リポジトリ（src 配下）のおおまかな構成:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - data/
    - __init__.py
    - schema.py                — DuckDB スキーマ定義 / init_schema / get_connection
    - jquants_client.py        — J-Quants API クライアント、保存ロジック
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — カレンダー管理・判定ロジック・更新ジョブ
    - news_collector.py        — RSS 収集・正規化・DB保存・銘柄抽出
    - quality.py               — データ品質チェック
    - audit.py                 — 監査ログ定義と初期化
    - (その他データ関連モジュール)
  - strategy/
    - __init__.py              — 戦略層用エントリ（将来的な拡張）
  - execution/
    - __init__.py              — 発注・実行関連（将来的な拡張）
  - monitoring/
    - __init__.py              — 監視・メトリクス関連（将来的な拡張）

---

## 開発上の注意点 / 実装上の要点

- レート制御: J-Quants API は 120 req/min を想定。jquants_client は固定間隔（スロットリング）で待機します。
- 冪等性: save_* 関数は ON CONFLICT を使って重複を排除・更新するため、再実行が可能です。
- トークン管理: get_id_token は refresh token から id token を取得。401 受信時は自動リフレッシュを行い1回のみリトライします。
- ニュース収集のセキュリティ:
  - defusedxml による XML パース
  - リダイレクト時のスキーム検査とプライベートIP拒否（SSRF対策）
  - レスポンスサイズ上限（10MB）・gzip 解凍後サイズ再チェック（Gzip bomb 対策）
- テストしやすさ:
  - news_collector._urlopen などはテスト時にモック差し替え可能
  - pipeline の関数は id_token を注入できるため外部依存を切り離せます

---

## トラブルシューティング

- .env が自動ロードされない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていると自動ロードは無効化されます
- J-Quants トークンエラー:
  - Settings.jquants_refresh_token が設定されているか確認
  - get_id_token でリフレッシュできることを確認
- DuckDB 接続/権限エラー:
  - 指定した DB パスの親ディレクトリが存在しない場合、init_schema は自動作成しますが、書き込み権限を確認してください

---

## 今後の拡張案（参考）

- strategy / execution 層の具象実装（注文作成・証券会社 API 連携）
- Slack 通知・モニタリング統合（settings の Slack 設定を活用）
- CI / テストスイート（外部 API はモック化）
- パッケージ配布（pyproject.toml を整備して pip install -e . を容易に）

---

必要なら README を .env.example のテンプレートや具体的なコマンド例（cron での夜間ジョブ登録、systemd の unit 例など）で追記します。どの部分をより詳しくしたいか教えてください。