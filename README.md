# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）のリポジトリ用 README。  
この文書はパッケージ内の実装（データ取得・ETL・スキーマ・ニュース収集・監査ログなど）に基づき作成しています。

目次
- プロジェクト概要
- 主な機能
- 前提条件 / 必要ライブラリ
- セットアップ手順
- 簡単な使い方（例）
- 環境変数（.env）
- 自動 .env ロード動作
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買インフラ向けに設計された Python ライブラリ群です。  
主に以下を提供します。

- J-Quants API などからの市場データ取得（株価日足・財務・JPX カレンダー）
- DuckDB ベースのデータスキーマ定義と初期化
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- RSS ニュースの収集・前処理・銘柄紐付け
- マーケットカレンダー管理（営業日判定、next/prev 等）
- 監査ログ用スキーマ（シグナル → 発注 → 約定のトレース）
- 各種ユーティリティ（リトライ／レートリミット／SSRF対策等）

設計上の重視点：
- 冪等性（ON CONFLICT を使った安全な DB 更新）
- Look-ahead bias 回避（fetched_at を UTC で記録）
- API レート制御とリトライ（指数バックオフ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 主な機能一覧

- data.jquants_client
  - J-Quants から日足（OHLCV）、財務、取引カレンダーを取得
  - レートリミット（120 req/min）に基づくスロットリング
  - リトライ & トークン自動リフレッシュ
  - DuckDB へ冪等保存（save_daily_quotes 等）

- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(db_path) で全テーブル・インデックスを作成

- data.pipeline
  - run_daily_etl: 市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分更新（DB最終日＋backfill）を自動計算

- data.news_collector
  - RSS 取得、XML安全パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去・記事ID は正規化URLの SHA-256 (先頭32文字)
  - SSRF 対策（スキーム検証・プライベートアドレスブロック）
  - Gzip / レスポンスサイズ制限（メモリDoS対策）
  - raw_news / news_symbols への冪等保存

- data.calendar_management
  - market_calendar に基づく営業日判定、next/prev_trading_day、get_trading_days
  - 夜間の calendar_update_job（差分取得＆保存）

- data.quality
  - 欠損・スパイク・重複・日付不整合のチェック。QualityIssue オブジェクトで返却。

- data.audit
  - 監査ログ用テーブル（signal_events, order_requests, executions）と初期化ヘルパー

---

## 前提条件 / 必要ライブラリ

- Python 3.10 以上（型アノテーションの構文に依存）
- 依存パッケージ（一部）
  - duckdb
  - defusedxml

（実際の配布パッケージでは setup.py / pyproject.toml に依存関係を明記してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール（例）
   - pip install duckdb defusedxml
   - またはパッケージ化されていれば: pip install -e .
4. .env を作成（下の「環境変数」セクション参照）
5. DuckDB スキーマを初期化（例を下に示します）

---

## 簡単な使い方（コード例）

- DuckDB スキーマ初期化（ファイルを作成してテーブルを準備）:

```python
from kabusys.data.schema import init_schema

# ファイルpathには settings.duckdb_path の値を使ってください
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）:

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を渡すことも可能
print(result.to_dict())
```

- ニュース収集（RSS を取得して raw_news に保存）:

```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# sources を省略すると DEFAULT_RSS_SOURCES を使用
stats = run_news_collection(conn, known_codes={"7203", "6758"})
print(stats)  # source_name: 新規保存件数
```

- カレンダー夜間更新ジョブ:

```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved={saved}")
```

- 監査ログ DB 初期化（監査専用DBを作る場合）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- J-Quants のトークンを直接取得（必要に応じて）:

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使う
```

---

## 環境変数（.env）

settings（kabusys.config.Settings）で参照される主な環境変数は以下です。必須項目は必ず設定してください。

必須:
- JQUANTS_REFRESH_TOKEN  … J-Quants のリフレッシュトークン
- KABU_API_PASSWORD       … kabuステーション等の API パスワード
- SLACK_BOT_TOKEN         … Slack 通知用ボットトークン
- SLACK_CHANNEL_ID        … Slack 通知先チャンネルID

任意（デフォルト値あり）:
- KABUSYS_ENV             … 環境: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL               … ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL （デフォルト: INFO）
- KABU_API_BASE_URL       … kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH             … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH             … 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 (.env.example):

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

注意:
- settings は必須環境変数が不足していると ValueError を投げます（例: jquants_refresh_token）。
- DUCKDB_PATH に指定した親ディレクトリが存在しない場合、init_schema は自動作成します。

---

## 自動 .env ロード動作

kabusys.config モジュールは起動時に自動で環境変数のロードを試みます（.env / .env.local）:

- .env の検索はパッケージのファイル位置を基準に上位ディレクトリを探索し、.git または pyproject.toml が見つかったルートをプロジェクトルートと見なします。
- 読み込み順序: OS 環境変数 > .env.local > .env
- OS の環境変数は .env によって上書きされません（.env.local の override=True を使っても保護されます）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。

.env のパースはシェル風のキー=値、シングル/ダブルクォート、 export プレフィックス、インラインコメントなどに対応します。

---

## ディレクトリ構成

パッケージ内部の主要ファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py              — DuckDB スキーマ定義・初期化
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - news_collector.py      — RSS ニュース取得・保存
    - calendar_management.py — カレンダー管理 / 夜間ジョブ
    - audit.py               — 監査ログスキーマ初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記は実装済みモジュールの抜粋、戦略や実行・監視部分の実装はこのコードベースでは初期化のみ）

---

## 補足 / 運用上の注意

- J-Quants API 利用時はレート上限（120 req/min）を厳守する設計です。ライブラリは固定間隔スロットリングで制御しますが、複数プロセスから並列実行する場合は追加管理が必要です。
- DB 操作は多くが冪等に設計されています（ON CONFLICT DO UPDATE / DO NOTHING）。ただし外部からの直接操作やスキーマ変更時は注意してください。
- RSS 取得では SSRF 対策（スキーム検証、プライベートIPブロック、リダイレクト検査）やレスポンスサイズ制限を実装しています。
- audit スキーマは UTC タイムゾーンでの保存を前提としています（init_audit_schema は TimeZone を UTC に設定します）。
- 品質チェックは Fail-Fast ではなく、検出項目を全て収集して呼び出し側で判断できるように設計されています。

---

この README はソースコードの実装に基づく概要・導入手順をまとめたものです。詳細な運用ルール・設定値・実行スケジュール等はプロジェクト固有のドキュメント（DataPlatform.md など）に従ってください。