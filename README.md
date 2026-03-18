# KabuSys

日本株自動売買プラットフォームの軽量ライブラリ群。データ収集（J-Quants, RSS 等）、DuckDB ベースのスキーマ管理、ETL パイプライン、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（発注〜約定のトレーサビリティ）など、自動売買システムで必要となる基盤機能を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local から自動的に環境変数を読み込む（プロジェクトルート検出: `.git` または `pyproject.toml`）。
  - 必須設定は Settings クラス経由で取得（不足時は ValueError）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）対応、指数バックオフによるリトライ、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事収集、前処理、DuckDB の raw_news に冪等保存
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256 ベースの記事 ID 発行
  - SSRF / XML Bomb / 大容量レスポンス等の安全対策（defusedxml、リダイレクト検査、サイズ制限 等）
  - 記事と銘柄コードの紐付け（news_symbols）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス、外部キーを含む冪等な初期化関数（init_schema, get_connection）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック（最終取得日からの差分取得、backfill オプション）
  - 日次 ETL 実行エントリ（run_daily_etl）、品質チェック統合

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、期間内営業日の一覧取得
  - JPX カレンダーの夜間差分更新ジョブ

- データ品質チェック（kabusys.data.quality）
  - 欠損値、スパイク（急騰／急落）、主キー重複、日付不整合（未来日付／非営業日データ）を検出
  - QualityIssue 型で詳細を返す（severity により呼び出し元が対応を決定）

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定までのトレーサビリティテーブル群と初期化 API（init_audit_schema / init_audit_db）
  - order_request_id を冪等キーとして二重発注防止をサポート

---

## 必要要件

- Python 3.10 以上（型注釈で | None を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml

（プロジェクト管理に pyproject.toml や requirements.txt を使っている場合はそれに従ってください）

---

## セットアップ手順

1. Python 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - もし requirements.txt / pyproject.toml がある場合はそれを使用してください。
   - 最低限:
     - pip install duckdb defusedxml

3. リポジトリルートに .env を作成（自動読み込み）
   - 自動読み込みはデフォルトで有効。無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - .env.local があれば .env の上から上書きされます。

4. 必要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知に使う Bot Token
   - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
   - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
   - KABUSYS_ENV (任意, 値: development | paper_trading | live) — 運用モード
   - LOG_LEVEL (任意, 値: DEBUG | INFO | WARNING | ERROR | CRITICAL)

例: .env の最小例
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

以下は主な操作のサンプルです。実行前に環境変数を設定し、依存ライブラリをインストールしてください。

- DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は .env の DUCKDB_PATH から取得（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

- 監査ログ専用 DB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

- 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes: 銘柄コード（例: {'7203','6758'}）を渡すと記事と銘柄を紐付けます
results = run_news_collection(conn, known_codes=set(), timeout=30)
print(results)  # {source_name: 新規保存数, ...}
```

- J-Quants から日足を直接取得して保存（ユーティリティ）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

- データ品質チェック
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 設定（挙動のポイント）

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に `.env` を読みます。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - テスト等で自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- ロギングレベルは環境変数 LOG_LEVEL で制御（デフォルト INFO）。

- J-Quants API のレート制限（120 req/min）に合わせて internal RateLimiter が自動制御します。大量取得時は一定の間隔が挟まれます。

---

## ディレクトリ構成

リポジトリの主要ファイル・モジュール構成（コードベースから抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / Settings 管理
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント / 保存ユーティリティ
    - news_collector.py          -- RSS ニュース収集・前処理・保存
    - schema.py                  -- DuckDB スキーマ定義・初期化
    - pipeline.py                -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py     -- マーケットカレンダー管理 / 営業日ロジック
    - audit.py                   -- 監査ログ（シグナル/発注/約定）スキーマ初期化
    - quality.py                 -- データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

注: strategy/、execution/、monitoring/ は今回のコードベースではモジュールの骨組みが用意されており、アプリ固有の戦略やブローカー連携ロジックは各自で実装する想定です。

---

## 運用上の注意

- 機密情報（API トークン等）は .env.local や CI のシークレット機能を使って管理し、リポジトリに含めないでください。
- DuckDB ファイルは単一ファイルなのでバックアップやロックに注意してください（同時書き込みの扱いに関しては運用方針に従ってください）。
- 実際の発注ロジック（execution 層）を実装する際には二重発注防止・冪等性・監査ログの完全性に注意してください（audit モジュールを活用）。

---

## 拡張案 / TODO（参考）

- kabuステーション API 実装（execution 層）と発注リトライ／失敗ハンドリング
- Slack 通知やモニタリング（monitoring モジュール）実装
- CI 用のテストスイート、モックを使った外部 API の単体テスト整備
- 高度な特徴量計算やモデル評価パイプラインの追加（strategy/feature 層）

---

ご不明点や README に追加したい具体的な使用例（たとえば systemd/jupyter/airflow での運用例）があれば教えてください。README をそれに合わせて拡張します。