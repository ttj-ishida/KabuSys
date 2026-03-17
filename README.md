# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）です。本リポジトリはデータ収集・ETL・品質チェック・監査ログ・マーケットカレンダー管理など、戦略や注文実行層に必要な基盤機能を提供します。

主な設計方針：
- データ層は DuckDB を用いた3層構造（Raw / Processed / Feature）で整備
- J-Quants API からの取得はレート制限・リトライ・トークン自動リフレッシュを考慮
- ニュース収集は RSS の安全処理（SSRF対策・XML脆弱性対策・サイズ制限）を実装
- DB 書き込みは冪等に（ON CONFLICT / トランザクション）対応
- 品質チェックで欠損・スパイク・重複・日付不整合を検出

---

## 機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーの取得
  - レートリミット（120 req/min）、指数バックオフリトライ、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）や Look-ahead Bias に配慮した設計
- ニュース収集（RSS）
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、SHA-256 による記事 ID 生成
  - SSRF 対策（リダイレクト検査・プライベートホスト拒否）、gzip サイズ制限、defusedxml による安全な XML パース
  - raw_news / news_symbols への冪等保存
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit のテーブル DDL を提供
  - インデックス定義、監査ログ用スキーマ（order/exec のトレース）も含む
- ETL パイプライン
  - 差分更新（最終取得日からの差分／バックフィル）、カレンダー先読み、品質チェックを一括実行
  - 品質チェック（欠損、スパイク、重複、日付整合性）
- マーケットカレンダー管理
  - 営業日判定・前後営業日の取得・期間内営業日列挙、夜間カレンダー差分更新ジョブ
- 監査ログ（Audit）
  - signal → order_request → executions までの UUID 連鎖でのトレーサビリティ
  - UTC タイムゾーン固定、冪等キー、ステータス管理

---

## 要求環境 / 依存

- Python 3.10+
  - 型注釈（|）、match などの記法に依存していないが、Union の `|` を利用しているため 3.10 以上を推奨
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

インストール例（仮に pyproject / setup が用意されている場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 開発インストール（プロジェクトに setup/pyproject がある場合）
# pip install -e .
```

（もし requirements.txt / pyproject.toml がある場合はそれに従ってください）

---

## 環境変数

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に必要となる環境変数（Settings により参照されます）:

- J-Quants
  - JQUANTS_REFRESH_TOKEN=<your_refresh_token>
- kabuステーション API
  - KABU_API_PASSWORD=<password>
  - KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- Slack（通知などに使用する想定）
  - SLACK_BOT_TOKEN=<xoxb-...>
  - SLACK_CHANNEL_ID=<channel_id>
- データベースパス（省略可）
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用 SQLite、デフォルト: data/monitoring.db)
- システム設定
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   # もしローカルインストール可能なら:
   # pip install -e .
   ```

2. 環境変数を設定（`.env` をプロジェクトルートに作成）
   - 上記の環境変数を `.env` に記述

3. DuckDB スキーマ初期化
   - Python REPL やスクリプトから次を実行：
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリは自動作成されます
   ```
   - 監査ログ専用 DB を作る場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

4. ロギングレベルは環境変数 `LOG_LEVEL` で制御

---

## 使い方（代表的な例）

- 日次 ETL を実行する（株価 / 財務 / カレンダー取得 + 品質チェック）:
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # デフォルトでは target_date=today, 品質チェック有効
print(result.to_dict())
```

- 個別ジョブ（カレンダー更新）:
```python
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- ニュース収集の実行例:
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（例: {"7203","6758", ...}）。None の場合は紐付けをスキップ。
results = run_news_collection(conn, known_codes=None)
print(results)
```

- J-Quants のトークン取得（手動）:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を参照
print(token)
```

- 品質チェック単体実行:
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=None, reference_date=date.today())
for i in issues:
    print(i)
```

注意:
- ETL やニュース収集は外部 API にアクセスするため、適切な認証情報とネットワーク環境が必要です。
- J-Quants API はレート制限（120 req/min）があるため、コードは内部で待機処理を行います。

---

## ディレクトリ構成（主要ファイル）

（パスは `src/kabusys/` をルートとした一覧）

- __init__.py
  - パッケージのルート。公開モジュール名を __all__ に定義。
- config.py
  - 環境変数読み込み・設定管理。`.env` / `.env.local` 自動ロード機能、Settings クラス。
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（fetch/save, レート制御、認証リフレッシュ、ページネーション、DuckDB への保存関数）
  - news_collector.py
    - RSS 取得・前処理・SSRF 対策・raw_news への冪等保存・銘柄抽出
  - schema.py
    - DuckDB の DDL 定義と init_schema / get_connection
  - pipeline.py
    - 日次 ETL パイプライン、個別 ETL（prices/financials/calendar）とヘルパー
  - calendar_management.py
    - マーケットカレンダー更新、営業日判定・next/prev/get_trading_days
  - audit.py
    - 監査ログ用スキーマ（signal_events, order_requests, executions）と初期化関数
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
- strategy/
  - __init__.py  （戦略関連機能を配置するためのパッケージ）
- execution/
  - __init__.py  （発注 / ブローカー連携などの実装場所）
- monitoring/
  - __init__.py  （監視・メトリクス関連を想定）

（上記以外の補助モジュールはプロジェクトに応じて追加されます）

---

## 運用上の注意 / トラブルシューティング

- 環境変数の自動ロード:
  - プロジェクトルートの判定は `.git` または `pyproject.toml` を基準にします。テストなどで自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- トークン管理:
  - J-Quants のリフレッシュトークンは長期保存されますが、ID トークンは有効期限が短いためライブラリ内で自動リフレッシュします。`get_id_token` 呼出しは `allow_refresh=False` で内部再帰を防ぐ実装になっています。
- DuckDB:
  - デフォルトパスは `data/kabusys.duckdb`。ディレクトリがなければ自動作成されます。
  - 監査ログ用 DB を分離したい場合は `init_audit_db` を使用してください。監査スキーマは UTC タイムゾーンに固定されます。
- セキュリティ:
  - RSS 収集では SSRF・XML Bomb 対策を実装していますが、外部 URL の扱いには注意してください。
- ロギング:
  - `LOG_LEVEL` 環境変数で詳細度を制御してください（例: DEBUG でトラブルシュートに有用なログを出力）。

---

この README は現在のコードベース（src/kabusys 内のモジュール）に基づき作成しています。実際の導入時はプロジェクトの pyproject.toml / setup.py / CI 定義、運用手順書（DataPlatform.md 等）が存在する場合はそちらも参照してください。必要であれば README に使い方のスクリプト例や systemd / cron ジョブ設定例、より詳細な運用手順を追加できます。