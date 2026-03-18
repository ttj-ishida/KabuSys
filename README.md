# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買プラットフォームを構成するライブラリ群です。J-Quants API から市場データを取得して DuckDB に格納し、ニュース収集・品質チェック・マーケットカレンダー管理・監査ログ機能など、戦略／発注層へ渡すためのデータ基盤（ETL）を提供します。

主な設計方針:
- データ取得は冪等（ON CONFLICT / DO UPDATE / DO NOTHING）で安全に保存
- API 利用はレート制限とリトライ（指数バックオフ）で堅牢化
- Look-ahead bias を防ぐため fetched_at / UTC タイムスタンプを記録
- ニュース収集は SSRF 対策・XML 脆弱性対策・サイズ制限を導入

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 使い方（主要 API 例）
- 環境変数 (.env) 例
- ディレクトリ構成

---

プロジェクト概要
----------------
KabuSys はデータレイヤ（Raw / Processed / Feature / Execution）を DuckDB 上に構築し、以下の主要機能を実装します:

- J-Quants API クライアント（価格・財務・カレンダー取得、認証トークン管理）
- ETL パイプライン（日次差分取得 + バックフィル + 品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev/trading-days 等ユーティリティ）
- ニュース収集（RSS 取得、前処理、記事保存、銘柄抽出）
- 監査ログ（signal / order / execution のトレーサビリティ）
- データ品質チェックモジュール（欠損・スパイク・重複・日付不整合検査）
- 設定管理（.env 自動読み込み、環境別設定）

---

機能一覧
--------
- data.jquants_client
  - API 呼び出し（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - get_id_token（リフレッシュトークンから id_token を取得）
  - API レート制御（120 req/min）、リトライ、401 自動リフレッシュ
  - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）
- data.pipeline
  - run_daily_etl：日次 ETL（カレンダー → 価格 → 財務 → 品質チェック）
  - 差分取得、backfill、品質チェックの統合
- data.news_collector
  - RSS 取得・前処理（URL 除去・空白正規化）
  - 記事ID は URL 正規化の SHA-256（先頭32文字）で冪等性確保
  - SSRF 対策・defusedxml による XML 攻撃対策・受信サイズ制限
  - DuckDB への保存（save_raw_news / save_news_symbols）
  - run_news_collection：複数ソースの収集ジョブ
- data.schema
  - DuckDB スキーマ定義と init_schema(db_path)
  - Raw / Processed / Feature / Execution 層のDDLとインデックス
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチで JPX カレンダーを更新）
- data.audit
  - 監査用テーブル定義と init_audit_schema / init_audit_db（UTC タイムゾーン固定）
- data.quality
  - 欠損、スパイク、重複、日付不整合のチェック（QualityIssue を返す）
- config
  - Settings クラス（環境変数から各種設定を参照）
  - プロジェクトルートの .env / .env.local を自動読み込み（無効化可）

---

必要条件
--------
- Python 3.10 以上（| 型注釈などを使用）
- 依存ライブラリ:
  - duckdb
  - defusedxml
  - （標準ライブラリ: urllib, json, logging, datetime, pathlib 等）

インストール例（ローカル開発）:
```bash
# 仮想環境を作成して有効化
python -m venv .venv
source .venv/bin/activate

# パッケージをインストール（requirements.txt がある場合はそちらを使用）
pip install duckdb defusedxml
# またはパッケージ配布時は `pip install -e .` (setup/pyproject があること)
```

---

セットアップ手順
----------------

1. リポジトリのクローン／配置

2. 環境変数の設定
   - プロジェクトルートに .env または .env.local を作成する（サンプルは下部参照）
   - 自動ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

3. DuckDB スキーマ初期化
   - Python からスキーマを初期化して DB ファイルを作成します（デフォルトのパスは data/kabusys.duckdb）。
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # :memory: も可
```

4. （必要に応じて）監査DBの初期化
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

環境変数（必須 / 推奨）
---------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

オプション:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に .env と .env.local を自動読み込みします
- 読み込み優先度: OS 環境 > .env.local > .env
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例 (.env.example) — 下部に記載

---

使い方（主要 API 例）
--------------------

設定取得:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

スキーマ初期化:
```python
from kabusys.data import schema
conn = schema.init_schema(settings.duckdb_path)
```

日次 ETL 実行:
```python
from kabusys.data import pipeline
from datetime import date

result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

ニュース収集:
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄コードの集合（例: 全上場銘柄のコードセット）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count}
```

カレンダー更新ジョブ（夜間バッチ）:
```python
from kabusys.data import calendar_management
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
```

監査スキーマ初期化（既存 conn に追加したい場合）:
```python
from kabusys.data import audit
audit.init_audit_schema(conn, transactional=False)
```

品質チェック（単独実行）:
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

J-Quants トークン取得（直接）:
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を利用
```

注意点（運用上のポイント）
- jquants_client は内部で 120 req/min の固定間隔スロットリングと最大 3 回のリトライを行います
- 401 を受けた場合はリフレッシュトークンから自動で id_token を再取得して 1 回だけリトライします
- ニュース収集は外部 URL に対して SSRF 対策を行い、受信サイズを上限（10MB）に制限します
- DuckDB への保存は基本的に冪等操作（ON CONFLICT）で上書きまたはスキップされます
- data.pipeline.run_daily_etl はエラー発生時も可能な限り処理を継続し、結果オブジェクトにエラー・品質問題を蓄積します

---

.env.example（サンプル）
------------------------
以下をプロジェクトルートの .env または .env.local にコピーして必要な値を設定してください。

例:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

ディレクトリ構成
----------------
リポジトリ内の主要ファイル / モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - calendar_management.py
      - schema.py
      - audit.py
      - quality.py

各モジュール責務:
- config.py: 環境変数・設定の集中管理（自動 .env 読み込み含む）
- data/schema.py: DuckDB のスキーマ定義・初期化
- data/jquants_client.py: J-Quants API クライアント（取得・保存）
- data/pipeline.py: ETL のオーケストレーション（差分取得・品質チェック）
- data/news_collector.py: RSS 収集 → 前処理 → DuckDB 保存
- data/calendar_management.py: JPX カレンダー管理と営業日ロジック
- data/audit.py: 監査ログ用スキーマ
- data/quality.py: 品質チェック

---

補足
----
- バージョンは kabusys.__version__ で確認できます（現行: 0.1.0）。
- DuckDB を利用しているため軽量で高速にローカル処理が可能です。運用では適切なバックアップ・アクセス管理を行ってください。
- 本 README はコードベースに含まれる docstring を基に作成しています。各関数の詳細な挙動や引数については該当モジュールの docstring を参照してください。

---

問題・改善提案・貢献
-------------------
バグ報告や機能要望、プルリクエスト歓迎します。プロジェクトルートに CONTRIBUTING.md があればそちらに従ってください。