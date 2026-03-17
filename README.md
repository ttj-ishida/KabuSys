# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。J-Quants や kabuステーション 等の外部サービスからデータを取得し、DuckDB に蓄積・品質チェック・ETL を行い、戦略・発注・監査の基盤を提供します。

主な設計方針:
- データ取得はレート制限・リトライ・トークンリフレッシュを備えた堅牢な実装
- DuckDB を用いた冪等（idempotent）な保存（ON CONFLICT）
- ニュース収集は SSRF・XML Bomb 等の対策を実装
- ETL は差分/バックフィル対応・品質チェック（欠損/重複/スパイク/日付不整合）
- 監査（audit）テーブルによるシグナル→発注→約定のトレーサビリティ

---

## 機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env/.env.local 自動ロード（オプトアウト可）
  - 必須環境変数のバリデーション、実行環境フラグ（development/paper_trading/live）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期BS/PL）、JPX カレンダー取得
  - レートリミッタ、リトライ、401 時のトークン自動リフレッシュ、fetched_at 登録
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・XML パース（defusedxml）、URL 正規化、ID は SHA-256 トップ32文字で生成
  - SSRF / プライベートIP / gzip サイズ上限対策、DuckDB への冪等保存 + 銘柄紐付け
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス作成、init_schema() / get_connection()
- ETL パイプライン（kabusys.data.pipeline）
  - 市場カレンダー、株価、財務の差分取得・保存・品質チェック
  - run_daily_etl() により日次 ETL を一括実行
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、カレンダー夜間更新ジョブ
- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク、主キー重複、日付不整合を検出し QualityIssue を返す
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル、init_audit_schema

その他:
- strategy / execution / monitoring 用のパッケージ雛形（将来的に戦略や発注実装を追加）

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の | 記法等を使用）
- Git

1. リポジトリをクローン
```bash
git clone <repository-url>
cd <repository-root>
```

2. 仮想環境を作成して有効化
```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

3. 必要パッケージをインストール
- このコードベースで明示的に使用している外部パッケージ:
  - duckdb
  - defusedxml
- 他にプロジェクトで必要なパッケージ（例: Slack クライアント等）がある場合は追加してください。

例:
```bash
pip install duckdb defusedxml
# 開発用に (推奨)
pip install -e .
```

4. 環境変数の準備
- プロジェクトルートに `.env` または `.env.local` を作成すると、自動で読み込まれます（ただし自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主な環境変数（例）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL (任意) — 既定: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack Bot Token
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — 既定: data/kabusys.duckdb
- SQLITE_PATH (任意) — 既定: data/monitoring.db
- KABUSYS_ENV (任意) — development / paper_trading / live （既定: development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxx
KABU_API_PASSWORD=yyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主な API と実行例）

Python REPL やスクリプトから直接呼び出して利用できます。

1. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
```

2. 日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3. 個別の ETL ジョブ
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
# conn を用意して target_date 指定
```

4. ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードセット（例: {"7203","6758"}）
res = run_news_collection(conn, sources=None, known_codes=known_codes)
# returns {source_name: 新規保存件数}
```

5. カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved_count = calendar_update_job(conn)
```

6. 品質チェックを単独で実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

7. J-Quants の低レベル API 呼び出し（例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()
quotes = fetch_daily_quotes(id_token=token, code="7203", date_from=..., date_to=...)
```

注意点:
- 実運用（live）では env 設定やログレベル、DB のバックアップ・排他制御に十分注意してください。
- ETL やジョブは間隔やレート制限（J-Quants: 120 req/min）に配慮して運用してください。

---

## 主要ディレクトリ構成

（src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py                         - 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py               - J-Quants API クライアント（取得＆保存）
    - news_collector.py               - RSS ニュース収集・保存・銘柄抽出
    - schema.py                       - DuckDB スキーマ定義と初期化
    - pipeline.py                     - ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py          - マーケットカレンダー管理
    - audit.py                        - 監査ログ（signal/order/execution）初期化
    - quality.py                      - データ品質チェック
  - strategy/                          - 戦略層（雛形）
    - __init__.py
  - execution/                         - 発注・約定管理（雛形）
    - __init__.py
  - monitoring/                        - 監視関連（雛形）
    - __init__.py

その他:
- .env / .env.local  - ローカル設定（プロジェクトルートに配置）

---

## 開発・運用上の注意

- Python バージョン: 3.10 以上を推奨
- DB: DuckDB を採用（軽量で高速）。パスの既定は data/kabusys.duckdb
- 環境変数自動ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に .env/.env.local を自動読み込み
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- セキュリティ:
  - news_collector は SSRF/プライベートIP/Gzip bomb/XML Bomb 等の防御を実装
  - J-Quants トークンは環境変数で管理し、get_id_token() が自動でリフレッシュ
- 冪等性:
  - データ挿入は ON CONFLICT または INSERT ... DO NOTHING を用い再実行に耐える設計
- ロギング:
  - settings.log_level でログレベルを制御
- テスト:
  - ネットワークアクセスや時間依存部分はモック可能な設計（例: _urlopen を差し替え）

---

## よくある質問・トラブルシュート

- .env が読み込まれない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - パッケージの __file__ を起点にプロジェクトルート（.git または pyproject.toml）を探索するため、プロジェクト配置場所を確認
- DuckDB にテーブルが作成されない:
  - init_schema() を呼んでいるか確認。get_connection() はスキーマ初期化を行わない点に注意
- J-Quants の 401 が頻発する:
  - JQUANTS_REFRESH_TOKEN が正しいか、get_id_token() 呼び出しに失敗していないか確認。jquants_client は 401 で一度だけリフレッシュを試みます

---

README はここまでです。追加で以下を用意できます:
- サンプル .env.example
- 簡易 CLI スクリプト（ETL / calendar update / news collect）
- CI 用のテストケース雛形

必要があれば、どれを優先して作成するか教えてください。