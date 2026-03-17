# KabuSys

日本株自動売買プラットフォームのコアライブラリ（KabuSys）です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ（発注→約定トレーサビリティ）などの機能を提供します。

## 概要
KabuSys は日本株アルゴリズム取引のための内部ライブラリ群です。  
主に以下の責務を持ちます。

- J-Quants API からの市場データ（株価日足・財務データ・マーケットカレンダー）取得と DuckDB への永続化（冪等）。
- RSS ベースのニュース収集と記事の正規化／銘柄紐付け。
- ETL パイプライン（差分取得、バックフィル、品質チェック）の実行。
- マーケットカレンダー（JPX）データ管理・営業日判定ユーティリティ。
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化。
- 設定管理（.env / 環境変数）の自動読み込み（配布後に安全に動作する探索ロジックあり）。

設計上の特徴：
- API レート制御（J-Quants の 120 req/min を順守する RateLimiter）
- リトライ・トークン自動リフレッシュ（401 時に一回リフレッシュ）
- Look-ahead バイアスを防ぐための fetched_at / UTC 記録
- DuckDB に対する冪等保存（ON CONFLICT）
- RSS の SSRF / XML 攻撃対策（URL スキーム検証、defusedxml、レスポンスサイズ制限 等）

## 機能一覧
- 環境設定: 自動で .env/.env.local をプロジェクトルートから読み込む（必要に応じて無効化可能）
- J-Quants クライアント:
  - 株価日足（fetch_daily_quotes / save_daily_quotes）
  - 財務データ（fetch_financial_statements / save_financial_statements）
  - マーケットカレンダー（fetch_market_calendar / save_market_calendar）
- News Collector:
  - RSS フィード取得（gzip 対応、サイズ制限、SSRF 回避）
  - 記事正規化（URL トラッキング除去、SHA-256 ベースの冪等ID）
  - DuckDB への保存（save_raw_news, save_news_symbols）
  - 銘柄コード抽出（4桁の既知銘柄コードから抽出）
- ETL パイプライン:
  - 差分更新、バックフィル、品質チェック（run_daily_etl など）
- マーケットカレンダー管理:
  - 営業日判定・前後営業日取得・期間の営業日取得、夜間バッチ更新（calendar_update_job）
- データ品質チェック:
  - 欠損・スパイク（急騰/急落）・重複・日付不整合チェック（run_all_checks）
- スキーマ初期化:
  - DuckDB 用の全テーブル初期化（init_schema）
  - 監査ログ用スキーマ（init_audit_schema / init_audit_db）

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 環境（推奨: 仮想環境）を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要な依存パッケージをインストール
   - 最低限必要なライブラリ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   ※ プロジェクトに requirements.txt / pyproject.toml がある場合はそちらでインストールしてください（pip install -e . 等）。

4. 環境変数の設定
   - プロジェクトルートに .env や .env.local を置くと自動で読み込まれます（起動時に .git または pyproject.toml を起点に探索）。
   - 自動読み込みを無効化したいテスト等では、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから初期化します（後述の使い方参照）。

## 必須／推奨環境変数
KabuSys は複数の外部サービスを前提にしています。最低限以下を設定してください。

- J-Quants
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）

- kabuステーション API
  - KABU_API_PASSWORD: kabu API パスワード（必須）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

- Slack（通知等で使用）
  - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

- データベースパス（任意）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（monitoring 等）ファイルパス（デフォルト: data/monitoring.db）

- ログ / 実行モード
  - KABUSYS_ENV: 実行環境 (development | paper_trading | live) （デフォルト: development）
  - LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## 使い方（簡易サンプル）

以下は代表的な利用例です。詳細は各モジュールの API に準拠してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

2) 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS を読み、raw_news と news_symbols を保存）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

4) マーケットカレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} records")
```

5) J-Quants から生データを直接取得して保存（テスト用）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
records = jq.fetch_daily_quotes(id_token=id_token, date_from=None, date_to=None)
jq.save_daily_quotes(conn, records)
```

6) 環境設定参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.is_live)
```

## ディレクトリ構成
（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理および .env 自動読み込み
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py      — RSS ベースのニュース収集・保存機能
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - schema.py              — DuckDB スキーマ定義 / init_schema / get_connection
    - calendar_management.py — JPX カレンダー管理ユーティリティ
    - audit.py               — 監査ログ（シグナル／発注／約定）用スキーマ
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略モジュール用プレースホルダ
  - execution/
    - __init__.py            — 発注 / execution 層用プレースホルダ
  - monitoring/
    - __init__.py            — 監視モジュール（プレースホルダ）

（上記はリポジトリの主要ファイルを抜粋しています）

## 注意点・運用上のポイント
- J-Quants API のレート制限（120 req/min）をライブラリ内で順守します。大量に並列で叩かないでください。
- get_id_token() はリフレッシュトークンを用いて ID トークンを取得します。settings.jquants_refresh_token を設定しておいてください。
- DuckDB への保存はできるだけ同一接続で行い、init_schema() でテーブルを事前に作成してください。
- news_collector は外部 RSS を扱うため、SSRF・XML インジェクション・Gzip Bomb 等の対策を実装していますが、運用での入力先管理（信頼できる RSS のみ追加）を推奨します。
- ETL は Fail-Fast ではなく全件収集を重視します。品質チェックでエラーが出た場合は結果を確認してから対処してください。
- 環境変数の自動ロードは、プロジェクトルートの判定に .git または pyproject.toml を使います。配布後の実行環境でも意図した .env が読み込まれるよう設計されています。

## 開発メモ / テストヒント
- 自動 .env 読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してからモジュールをインポートしてください（テスト時に便利）。
- news_collector._urlopen をモックすることでネットワークアクセスを差し替えられます（ユニットテスト用フック）。
- DuckDB のインメモリ接続(":memory:") を使えば一時的なテスト DB を簡単に構築できます。

---

詳細な API 仕様やデータモデル（DataPlatform.md / DataSchema.md 参照）は別ドキュメントへまとめる想定です。README に載せきれない実装上の注意や設計ドキュメントがある場合はそれらも合わせて参照してください。必要であれば README を英語版にしたり、具体的な運用手順（cron / CI ジョブ）例を追加します。必要な情報を教えてください。