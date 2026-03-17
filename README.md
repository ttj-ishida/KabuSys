# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリです。J-Quants など外部データソースから市場データ・財務データ・ニュースを収集して DuckDB に蓄積し、ETL・品質チェック・監査ログを通じて戦略・発注レイヤへ供給することを目的としています。

---

## 概要

KabuSys は以下を主に提供します。

- J-Quants API クライアント（株価日足・財務・マーケットカレンダー取得、レート制御・リトライ・トークン自動更新）
- RSS ベースのニュース収集モジュール（SSRF 対策・gzip/サイズ制限・トラッキングパラメータ除去・銘柄抽出）
- DuckDB スキーマ定義と初期化機能（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- マーケットカレンダー管理ユーティリティ（営業日判定・前後営業日検索）
- 監査ログ（シグナル→発注→約定のトレース用スキーマ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計方針として、再現性（fetched_at の記録など）、冪等性（ON CONFLICT を使った保存）、外部攻撃対策（XML/SSRF）、および運用性（ログ・エラー集約）を重視しています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants との対話（認証、ページネーション対応、レート制御、リトライ、データ保存用ヘルパ）
  - save_* 関数は DuckDB へ冪等に保存（ON CONFLICT）
- data.news_collector
  - RSS フィード取得、記事正規化、SHA-256 ベース ID 発行、DuckDB へのバルク保存
  - URL 正規化、トラッキングパラメータ除去、SSRF 排除、gzip/サイズ上限
  - 銘柄コード抽出（4桁数字を known_codes と照合）
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema / get_connection を提供
- data.pipeline
  - 日次 ETL（calendar → prices → financials → 品質チェック）
  - 差分更新、バックフィル、結果オブジェクト（ETLResult）
- data.calendar_management
  - 営業日判定、前後営業日取得、カレンダー夜間更新ジョブ
- data.audit
  - 監査用テーブル（signal_events, order_requests, executions）と初期化
- data.quality
  - 欠損、スパイク、重複、日付不整合などのチェック群
- config
  - .env 自動ロード（.env → .env.local の優先順、OS 環境変数優先）
  - settings オブジェクトで環境設定を取得（トークン／DB パス／Slack 設定等）

strategy／execution／monitoring はパッケージプレースホルダとなっており、戦略実装／発注処理／監視処理を追加できます。

---

## 前提・依存関係

- Python 3.10 以上（typing の新しい構文を使用）
- 必要なライブラリ（最低限）:
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
```

プロジェクトをパッケージとして配布している場合は README に沿って requirements を追加しているはずです。開発用に追加パッケージ（テスト/ロギング等）を導入してください。

---

## 環境変数と設定

自動でプロジェクトルート（.git または pyproject.toml を探索）を検出し、以下の順で .env ファイルを読み込みます:

1. OS 環境変数（最優先）
2. .env.local（存在すれば上書き）
3. .env（存在すれば読み込み）

自動ロードを無効化したい場合:
- 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

必須環境変数（settings を使用する機能で参照される）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API のパスワード（発注周りで使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意・デフォルト:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 .env（参考）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo_url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```

2. 環境変数の用意
   - プロジェクトルートに `.env` または `.env.local` を置くか、OS 環境変数として設定します（上記必須値を参照）。

3. DuckDB スキーマ初期化
   - Python REPL やスクリプトで schema.init_schema を呼び出します。
   例:
   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)
   # これで必要なテーブル・インデックスが作成されます
   ```

4. 監査ログテーブル初期化（任意）
   ```python
   from kabusys.data import audit
   conn = schema.get_connection(settings.duckdb_path)  # 既存接続を取得
   audit.init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（簡単な例）

- 日次 ETL の実行（株価・財務・カレンダー取得＋品質チェック）:

```python
from kabusys.data import schema, pipeline
from kabusys.config import settings
from datetime import date

conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）:

```python
from kabusys.data import schema, news_collector
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
# known_codes は既知の銘柄コード集合（例えば prices_daily のコード一覧等）
known_codes = {"7203", "6758", "9984"}
res = news_collector.run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

- J-Quants からの日足データを直接取得して保存:

```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from kabusys.config import settings
from datetime import date

conn = schema.get_connection(settings.duckdb_path)
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,2,1))
saved = jq.save_daily_quotes(conn, records)
print(f"saved {saved}")
```

- 設定値の参照:

```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_dev)
```

---

## 運用上の注意点 / 実装の要点

- jquants_client
  - API レート制限（120 req/min）を _RateLimiter で制御
  - 指数バックオフで最大 3 回リトライ（408/429/5xx 等）
  - 401 を受信した場合は refresh token で id token を自動更新して 1 回リトライ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - 保存処理は冪等（ON CONFLICT DO UPDATE）

- news_collector
  - XML のパースは defusedxml を使用（XML Bomb 対策）
  - 受信サイズを MAX_RESPONSE_BYTES（デフォルト 10MB）で制限
  - リダイレクト先のスキームチェック・プライベート IP チェックで SSRF を防ぐ
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を採用して冪等性を確保

- schema / audit
  - テーブルは Raw → Processed → Feature → Execution → Audit の順に定義
  - audit.init_audit_schema は UTC タイムゾーンを固定（運用一貫性確保）

- pipeline / quality
  - 差分更新（最終取得日ベース）＋ backfill（デフォルト 3 日）
  - 品質チェックは Fail-Fast ではなく全件収集し、呼び出し側が判断できるよう結果を返す

---

## ディレクトリ構成

リポジトリの主要ファイル構成（抜粋）:

```
src/
└── kabusys/
    ├── __init__.py
    ├── config.py
    ├── data/
    │   ├── __init__.py
    │   ├── jquants_client.py
    │   ├── news_collector.py
    │   ├── schema.py
    │   ├── pipeline.py
    │   ├── calendar_management.py
    │   ├── audit.py
    │   └── quality.py
    ├── strategy/
    │   └── __init__.py
    ├── execution/
    │   └── __init__.py
    └── monitoring/
        └── __init__.py
```

各モジュールの役割は「主な機能一覧」を参照してください。strategy／execution／monitoring は拡張点として用意されています。

---

## 開発・拡張のポイント

- 新しいデータソースや戦略を追加する際は、raw 層にデータを冪等に保存するインターフェースを守ると運用が安定します。
- 発注ロジックは audit / order_requests テーブルを使って冪等（order_request_id）で実装すると二重発注の防止に有効です。
- DuckDB はスキーマ変更や大規模データに対して慎重に運用してください。インデックスやチャンクサイズは調整可能です。
- 設定は settings オブジェクトを通じて一箇所で管理してください（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って明示的に設定を注入できます）。

---

必要に応じて README に含めたい追加項目（例: CI / テスト実行方法、詳しい .env.example、運用 runbook、docker-compose など）があれば指示してください。