# KabuSys

日本株向け自動売買プラットフォームのライブラリ（KabuSys）。  
データ取得（J-Quants）、ETLパイプライン、ニュース収集、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）などの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。主な目的は次のとおりです。

- J-Quants API から株価・財務・カレンダーを取得して DuckDB に保存する（冪等性を重視）
- RSS からニュースを収集し記事と銘柄の紐付けを行う（SSRF や XML 攻撃対策あり）
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）を実行する
- マーケットカレンダー（JPX）を管理し営業日判定ロジックを提供する
- 発注〜約定に関する監査ログテーブル（トレーサビリティ）を初期化・管理する
- 設定は環境変数 / .env から管理（自動ロード機能あり）

設計上の特徴：API レート制限遵守、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ、DuckDB への idempotent な保存、RSS の SSRF/サイズ対策、品質チェックの集約報告。

---

## 機能一覧

- 設定管理
  - 環境変数/.env 自動ロード（.env, .env.local、プロジェクトルート検出）
  - 必須項目の取得と検証（例: JQUANTS_REFRESH_TOKEN）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価（日足）、財務（四半期 BS/PL）、マーケットカレンダー取得
  - レートリミット（120 req/min）とリトライロジック
  - ID トークンの自動リフレッシュとキャッシュ
  - DuckDB へ冪等保存（ON CONFLICT）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理（URL除去・空白正規化）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証、プライベートホスト拒否）、受信サイズ上限、defusedxml による XML 安全化
  - DuckDB へのバルク挿入（トランザクション、INSERT ... RETURNING）
  - 銘柄コード抽出（4桁数字、既知コードセットに基づく）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの再取得、backfill）
  - 市場カレンダー先読み
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - run_daily_etl による一括実行
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日の取得、期間内営業日リスト取得
  - 夜間バッチでカレンダー更新（calendar_update_job）
- スキーマ / DB 初期化（kabusys.data.schema）
  - DuckDB に Raw / Processed / Feature / Execution 層のテーブルを作成
  - インデックス作成、init_schema/get_connection
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の監査テーブルを作成
  - init_audit_db / init_audit_schema（UTC タイムゾーン固定）
- データ品質チェック（kabusys.data.quality）
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks でまとめて実行、QualityIssue のリストを返す

---

## 前提条件

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - defusedxml

環境に合わせて requirements.txt を用意してください（例）:
```
duckdb>=0.7
defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / コピーしてプロジェクトディレクトリに移動。

2. 仮想環境作成・有効化（任意だが推奨）:
```
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows
```

3. 依存パッケージをインストール:
```
pip install duckdb defusedxml
# または requirements.txt があれば:
pip install -r requirements.txt
```

4. 環境変数の準備:
- プロジェクトルートに `.env` や `.env.local` を作成できます。自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 主な環境変数（例）:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
  - KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL, デフォルト: INFO)

例 .env:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB スキーマ初期化（Python REPL で）:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

監査DBを別途初期化する場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（代表的な例）

- J-Quants ID トークン取得:
```python
from kabusys.data.jquants_client import get_id_token
print(get_id_token())  # settings.jquants_refresh_token を使用して id_token を取得
```

- 日次 ETL を実行（市場カレンダー、株価、財務、品質チェック）:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 引数で target_date, id_token 等を与えられる
print(result.to_dict())
```

- ニュース収集ジョブを実行:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
# known_codes があれば銘柄抽出・紐付けを行う
known_codes = {"7203", "6758"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # ソースごとの新規保存件数
```

- 品質チェックのみ実行:
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

- マーケットカレンダー周りの利用例:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      -- J-Quants API クライアント（取得 + DuckDB 保存）
      - news_collector.py      -- RSS ニュース収集・前処理・保存
      - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py -- マーケットカレンダー管理（営業日判定等）
      - schema.py              -- DuckDB スキーマ定義・初期化
      - audit.py               -- 監査ログ（発注/約定トレーサビリティ）
      - quality.py             -- データ品質チェック
    - strategy/
      - __init__.py            -- 戦略モジュール（将来的な拡張ポイント）
    - execution/
      - __init__.py            -- 発注実行モジュール（将来的な拡張ポイント）
    - monitoring/
      - __init__.py            -- 監視・アラート（将来的な拡張ポイント）

---

## 設計上の注意 / 運用メモ

- .env 自動ロード
  - プロジェクトルートは __file__ を基準に .git または pyproject.toml を辿って探索します。CWD に依存しないためパッケージ化後も動作します。
  - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API
  - レート制限 120 req/min をモジュール側で遵守します（固定間隔スロットリング）。
  - ネットワーク/HTTP エラー時は指数バックオフで最大 3 回リトライします。401 受信時はリフレッシュトークンで自動リフレッシュを試みます（1 回）。
- DuckDB 保存
  - 生データ保存は ON CONFLICT（DO UPDATE / DO NOTHING）を使い冪等性を保ちます。
  - スキーマ初期化は idempotent です（存在するテーブルはスキップ）。
- News Collector
  - RSS の XML は defusedxml で安全にパースします。レスポンスサイズや gzip 解凍後のサイズを制限します。
  - リダイレクト先のスキーム・ホストを検証して SSRF を防止します。
- 品質チェック
  - run_all_checks は Fail-Fast ではなく、すべてのチェックを実行して問題リストを返します。呼び出し側がエラーの重大度に応じた対応を決定してください。
- UTC タイムゾーン
  - 監査ログ関連の DB 初期化時に TimeZone を UTC に固定します。タイムスタンプは UTC 前提で扱ってください。

---

## 今後の拡張ポイント

- strategy / execution / monitoring の具体的な実装（戦略エンジン、発注ブローカーアダプタ、Prometheus/Sentry 連携等）
- CLI や定期実行（systemd / cron / Airflow など）用のエントリポイント
- 単体テスト、統合テスト、CI/CD 設定
- Slack 通知やメトリクス出力の強化

---

ご不明点や README に追加したい使用例・運用フローがあれば教えてください。README をプロジェクト運用チーム向けにさらに詳しく整備できます。