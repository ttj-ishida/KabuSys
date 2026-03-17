# KabuSys

KabuSys は日本株向けの自動売買プラットフォームの基盤ライブラリです。データ取得（J-Quants）、RSS ニュース収集、ETL パイプライン、データ品質チェック、DuckDB スキーマ定義、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

主な設計方針としては、冪等性・トレーサビリティ・セキュリティ（SSRF 対策等）・API レート制御・リトライ処理・品質チェックの明確化を重視しています。

---

## 特徴（機能一覧）

- 環境変数 / .env 自動読み込み（プロジェクトルート検出）
- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レートリミット（120 req/min）遵守（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）記録で Look-ahead Bias を抑制
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集モジュール
  - RSS フィード取得、前処理（URL 除去・空白正規化）
  - URL 正規化→SHA-256（先頭 32 文字）で記事 ID を生成し冪等性を保証
  - defusedxml を使った安全な XML パース、SSRF 対策（スキーム検証・プライベートアドレス拒否）
  - レスポンスサイズ制限（メモリ DoS 防止）、gzip 解凍、DB にトランザクションで保存（INSERT ... RETURNING）
  - 記事と銘柄コードの紐付け（news_symbols）
- DuckDB スキーマ
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義、初期化ユーティリティ（init_schema）
- ETL パイプライン
  - 差分更新（バックフィル対応）、カレンダー先読み、品質チェック実行（run_daily_etl）
  - 各ステップは独立したエラーハンドリング（1 ステップ失敗でも他は継続）
- 品質チェック（quality モジュール）
  - 欠損データ検出、スパイク検出、重複チェック、日付不整合チェック
  - QualityIssue オブジェクトで検出結果を集約
- 監査ログ（audit モジュール）
  - シグナル→発注→約定までの UUID ベースのトレーサビリティテーブル
  - init_audit_schema / init_audit_db による初期化

---

## 前提条件 / 依存パッケージ

- Python 3.10 以上（型記法に `X | Y` を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください）

インストール例（仮）:
```bash
python -m pip install duckdb defusedxml
# またはプロジェクト配布パッケージがあれば
# pip install -e .
```

---

## 環境変数（.env）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます。
自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（config.py に定義）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python（3.10+）と依存パッケージをインストール
   - duckdb, defusedxml 等

2. リポジトリをクローン / 配布パッケージをインストール
   - pip install -e .（プロジェクトルートに setup/pyproject がある場合）

3. .env を作成して必要な環境変数を設定
   - 上記の主要環境変数を `.env` または環境に設定してください

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで初期化できます（例は次節）

---

## 使い方（主要 API と実行例）

以下は最小限の利用例です。実際はアプリケーション層でこれら関数を呼び出してパイプラインを定期実行（cron / Airflow 等）します。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH に基づく Path
conn = init_schema(settings.duckdb_path)
```

- J-Quants トークン取得（手動）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token が使用される
```

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト
print(result.to_dict())
```

- ニュース収集（RSS）を実行して保存
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# sources を渡さなければデフォルトの RSS ソースが使われる
results = run_news_collection(conn, known_codes={"6758", "7203", "9432"})
print(results)  # { source_name: 新規保存件数, ... }
```

- 監査ログテーブルの初期化（既存の DuckDB 接続に追加）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)
```

- jquants_client の個別利用
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar: API からデータ取得（ページネーション対応）
  - save_daily_quotes / save_financial_statements / save_market_calendar: DuckDB に冪等保存

注意: これらの関数は duckdb.DuckDBPyConnection を受け取るため、スクリプト内で conn を開いて渡してください。

---

## 主要モジュール説明（まとめ）

- kabusys.config
  - 環境変数読み込み、Settings クラスで型安全にアクセス
  - 自動 .env ロード（プロジェクトルート判定、.env → .env.local の順で読み込み）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

- kabusys.data.jquants_client
  - API 呼び出しの共通実装（_request）
  - RateLimiter、リトライ、401 リフレッシュ処理、ページネーション対応
  - fetch_* / save_* 関数

- kabusys.data.news_collector
  - RSS 取得（fetch_rss）、テキスト前処理、記事 ID 生成、DB 保存（save_raw_news）、銘柄紐付け
  - SSRF 対策、gzip 対応、XML 脆弱性対策

- kabusys.data.schema
  - DuckDB スキーマ定義（Raw/Processed/Feature/Execution）
  - init_schema / get_connection

- kabusys.data.pipeline
  - run_daily_etl: カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック
  - 差分更新、backfill、ETLResult による集約

- kabusys.data.audit
  - 監査ログテーブル定義・初期化（signal_events / order_requests / executions）
  - init_audit_schema / init_audit_db

- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks: まとめ実行

---

## ディレクトリ構成

（リポジトリ内の主要ファイル・モジュール構成）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py
    - strategy/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - audit.py
      - quality.py

各モジュールは役割ごとに分離されており、アプリケーション層（戦略、実行エンジン、監視）から必要な機能を呼び出して組み合わせる想定です。

---

## 運用上の注意・推奨

- API レート制限、リトライ設定、バックフィル日数やカレンダー先読み日数は運用に合わせて調整してください。
- DuckDB ファイルはバックアップを推奨します。開発時は ":memory:" を利用して軽量に動作確認が可能です。
- ニュース収集時は RSS ソースの信頼性と著作権に注意してください。
- 監査ログ（audit）は削除しない運用を想定しています。長期保存やアーカイブ方針を検討してください。
- テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って .env 自動読み込みを無効化すると環境の変化に影響されにくくなります。

---

## ライセンス / 貢献

（この README にはライセンス情報・貢献手順は含めていません。実プロジェクトでは LICENSE ファイル・CONTRIBUTING.md を追加してください）

---

この README はコードベース（src/kabusys/...）の主要機能と使い方を簡潔にまとめたものです。実運用ではログ設定・例外ハンドリング、監視・アラート、デプロイ（コンテナ化）や CI/CD を別途設計してください。