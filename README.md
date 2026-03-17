# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、ETLパイプライン、データ品質チェック、マーケットカレンダー管理、監査ログテーブルなど、戦略実行に必要な基盤機能を提供します。

---

## 主な機能
- J-Quants API クライアント
  - 日次株価（OHLCV）・四半期財務データ・JPX マーケットカレンダーの取得
  - レート制限（120 req/min）対応、リトライ（指数バックオフ）、401時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS フィードから記事収集、URL 正規化、トラッキングパラメータ除去、記事IDは正規化URLのSHA-256先頭32文字
  - SSRF対策（スキームチェック・プライベートIPチェック・リダイレクト検査）
  - サイズ上限（デフォルト 10MB）・defusedxml による XML 攻撃対策
  - DuckDB へ冪等保存（INSERT ... RETURNING で挿入済み判定）および銘柄コード紐付け

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義とインデックス
  - スキーマ初期化（init_schema）および監査ログ専用初期化（init_audit_schema）

- ETL パイプライン
  - 差分更新（DB 最終取得日からの差分取得）と backfill による後出し修正吸収
  - 市場カレンダー先読み、株価・財務データの取得・保存・品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL 実行結果を ETLResult オブジェクトで返却

- マーケットカレンダー管理
  - 営業日判定 / 前後営業日の取得 / 期間の営業日取得 / SQ 判定
  - DB 未取得時は曜日ベースのフォールバック

- 監査（Audit）機能
  - シグナル → 発注要求 → 約定 のトレーサビリティを確保するテーブル群
  - order_request_id を冪等キーとして二重発注を防止

- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付整合性チェックを SQL ベースで実行

---

## 必要要件
- Python 3.10+
- 主要依存パッケージ
  - duckdb
  - defusedxml

（標準ライブラリの urllib, json, datetime, logging 等も使用）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb>=0.7" "defusedxml>=0.7"
# またはパッケージ化されていれば:
# pip install -e .
```

---

## 環境変数（設定）
このライブラリは環境変数から設定を読み込みます。プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env`、`.env.local` を自動で読み込みます（OS 環境変数は上書きされない、.env.local は .env を上書き）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO

自動 .env ロードを無効化するには:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

エラー時は Settings オブジェクトが未設定の必須環境変数で ValueError を送出します。

利用例（コード内）:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
```

---

## セットアップ手順（簡易）
1. リポジトリをクローン
2. 仮想環境作成、依存パッケージをインストール（上記参照）
3. プロジェクトルートに `.env`（および必要なら `.env.local`）を作成し、必須環境変数を設定
4. DuckDB スキーマを初期化

例:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

監査ログ用テーブルを追加する場合:
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

---

## 使い方（代表的な操作例）

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルを自動作成
```

- 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を省略すると今日を対象に実行
print(result.to_dict())
```

- 株価・財務の個別 ETL
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl, run_financials_etl

fetched_prices, saved_prices = run_prices_etl(conn, target_date=date(2025,1,15))
fetched_fin, saved_fin = run_financials_etl(conn, target_date=date(2025,1,15))
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203","6758","9984"}  # 有効な銘柄コードのセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- J-Quants から直接データ取得（テストや限定取得時）
```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes

quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 品質チェック単体実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

補足:
- jquants_client は内部で RateLimiter（120 req/min）、リトライ、401 自動リフレッシュを実装
- news_collector は SSRF・Gzip Bomb 等の安全対策を実装しているため、安全に RSS を収集可能
- テスト用に id_token 注入や _urlopen のモック差替えが可能（テスト容易性を考慮）

---

## ディレクトリ構成（主要ファイル）
以下はこの README に含まれるコードベースに対応する主要モジュール構成です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

各モジュールの役割:
- config.py: 環境変数・設定の読み込みと Settings オブジェクト
- data/jquants_client.py: J-Quants API クライアントおよび DuckDB への保存関数
- data/news_collector.py: RSS からニュースを収集して保存するモジュール
- data/schema.py: DuckDB スキーマ定義と初期化
- data/pipeline.py: ETL の高レベル制御（差分取得・品質チェック）
- data/calendar_management.py: マーケットカレンダー関連のユーティリティと夜間ジョブ
- data/audit.py: 監査ログ（signal / order_request / executions）テーブル定義と初期化
- data/quality.py: データ品質チェック（欠損・重複・スパイク・日付不整合）

---

## 実装上の注意点 / 設計上の特徴
- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込む（OS 環境変数は保護される）。テスト等で無効化可能。
- データ取得は冪等（ON CONFLICT）を前提にしているため、再実行可能。
- ETL は Fail-Fast ではなく、各ステップごとにエラーハンドリングして可能な限り処理を継続する設計。
- ニュース収集はセキュリティ（SSRF、XML攻撃、サイズ制限）を考慮して実装。
- DuckDB を用いることでローカルで高速な列指向分析を実現（ファイル DB で運用可能）。

---

## 貢献 / 開発メモ
- テストを書く際は、外部 API 呼び出し（_urlopen, get_id_token など）をモックすることを推奨します。
- DB 初期化や ETL 実行は副作用が伴うため、単体テストでは ":memory:" の DuckDB を用いると便利です。
- KABUSYS_ENV を切り替えて paper_trading/live の振る舞いを分離してください。

---

必要に応じて README にサンプル .env.example や CI 実行例（ETL を Cron/Cloud Scheduler で実行する方法）を追加できます。追記してほしいセクションがあれば教えてください。