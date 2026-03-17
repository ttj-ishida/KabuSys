# KabuSys

日本株自動売買のためのデータ基盤・ETL・監査モジュール群

---

## プロジェクト概要

KabuSys は、日本株の自動売買システム向けに設計された内部ライブラリ群です。主な目的は以下です。

- J-Quants API からのマーケットデータ収集（株価日足、財務データ、JPX カレンダー）
- RSS からのニュース収集と銘柄紐付け
- DuckDB を用いたデータスキーマ定義・初期化
- ETL（差分取得・バックフィル・品質チェック）パイプライン
- 発注／監査用のスキーマ（監査ログ、order_requests、executions 等）
- SSRF・XML Bomb 等の攻撃対策を考慮した堅牢な実装

設計方針として、API レート制限・リトライ・冪等性・トレーサビリティ・品質チェックに重きを置いています。

---

## 主な機能一覧

- J-Quants クライアント（rate limit、自動リフレッシュ、リトライ、ページネーション対応）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_* 系で DuckDB に冪等保存（ON CONFLICT）
- DuckDB スキーマ管理・初期化
  - init_schema(db_path) で全テーブルとインデックスを作成
  - audit 用スキーマ（init_audit_schema / init_audit_db）
- ETL パイプライン
  - run_daily_etl: カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分更新・backfill・calendar lookahead をサポート
- ニュース収集（RSS）
  - fetch_rss, save_raw_news, extract_stock_codes, run_news_collection
  - URL 正規化（tracking パラメータ除去）、記事ID は SHA-256 ハッシュ（先頭32文字）
  - SSRF 対策、gzip サイズ上限、defusedxml による XML 攻撃対策
- データ品質チェック
  - 欠損、重複、スパイク（前日比閾値）、日付不整合チェック
  - QualityIssue オブジェクトで結果を返す
- マーケットカレンダー管理
  - 営業日判定、前後営業日探索、期間内営業日取得、夜間バッチ更新 job

---

## セットアップ手順

前提: Python 3.10 以上を推奨（型注釈に `|` を使用）

1. リポジトリをクローンし、ソースルートに移動
   - プロジェクトは src/ 配下にパッケージがあるレイアウトです。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトで setup.cfg / pyproject.toml があれば pip install -e . を推奨）

4. 環境変数設定
   - プロジェクトルートの `.env` / `.env.local` を利用できます（config.py が自動で読み込みます）
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

必須の環境変数（コード内で _require() による確認あり）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")。デフォルト "development"
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)。デフォルト "INFO"
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト "data/kabusys.duckdb"
- SQLITE_PATH — 監視 DB（SQLite）パス。デフォルト "data/monitoring.db"

例 .env（最小例）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトからの利用イメージです。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 監査ログ用 DB 初期化（別 DB にしたい場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL 実行（J-Quants 認証は設定済みの環境変数を参照）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

4) ニュース収集ジョブを実行して保存（既知の銘柄コードセットを渡すと自動で紐付け）
```python
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: inserted_count, ...}
```

5) 品質チェック実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

6) J-Quants API を直接使う例
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
id_token = get_id_token()
records = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,3,1))
```

注意点:
- jquants_client は API レート制限（120 req/min）を内部で尊重します。
- 401 受信時はトークンを自動リフレッシュして一度リトライします。
- save_* 関数は冪等（ON CONFLICT）です。複数回実行しても重複登録を回避します。

---

## よく使う API（概要）

- kabusys.config.settings — 環境設定アクセス（settings.jquants_refresh_token 等）
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL ワークフロー
- kabusys.data.jquants_client.fetch_daily_quotes(...) — 株価取得
- kabusys.data.jquants_client.fetch_financial_statements(...) — 財務取得
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection — ニュース収集
- kabusys.data.quality.run_all_checks — 品質チェック
- kabusys.data.calendar_management.* — 営業日判定・カレンダー更新ジョブ
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ初期化

---

## ディレクトリ構成

パッケージは src/kabusys 配下に配置されています。主要ファイル:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - news_collector.py             — RSS ニュース収集・DB 保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義・初期化
    - pipeline.py                   — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py        — カレンダー更新・営業日判定
    - audit.py                      — 監査ログ（signal/order_request/executions）定義
    - quality.py                    — データ品質チェック
    - pipeline.py
  - strategy/
    - __init__.py                   — 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py                   — 発注実行関連（拡張ポイント）
  - monitoring/
    - __init__.py                   — 監視/アラート等（拡張ポイント）

注: strategy, execution, monitoring は拡張のための空パッケージになっています（将来的な戦略/発注実装を想定）。

---

## 運用上の注意・設計上のポイント

- .env 自動読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml の場所）から .env/.env.local を読み込みます。
  - 自動読み込みが不要な場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- API 制限とリトライ
  - J-Quants は 120 req/min を想定。jquants_client は固定間隔スロットリングと指数バックオフを実装しています。
- 冪等性
  - save_* 系は ON CONFLICT DO UPDATE / DO NOTHING を使用しているため、再実行に安全です。
- セキュリティ
  - news_collector は SSRF 対策（リダイレクト検査、プライベート IP 拒否）と defusedxml による XML 攻撃対策を行います。
  - 外部 URL のスキームは http/https のみ許可されます。
- DB トランザクション
  - 大量挿入はチャンク化してトランザクションで処理。失敗時はロールバックします。
- 日次バッチ
  - run_daily_etl は各ステップを個別にエラーハンドリングするため、あるステップの失敗が他ステップを止めにくい実装です（ただしエラーは記録されます）。

---

## 開発・拡張

- 戦略（strategy）や発注実装（execution）は空のパッケージとして用意されています。戦略を実装して signals を生成し、signal_queue → order_requests → executions と連携することで実運用に接続できます。
- テスト時には config の自動 .env 読み込みを無効化して環境をコントロールしてください（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## ライセンス・コントリビューション

（この README にはライセンスやコントリビューション手順は含まれていません。必要に応じてプロジェクトに LICENSE / CONTRIBUTING.md を追加してください。）

---

README は以上です。必要であれば、インストール用 pyproject.toml / requirements.txt のテンプレート、.env.example、具体的な ETL スケジューリング例（cron/systemd/tash）、または運用手順書を追加で作成します。どれを優先しますか？