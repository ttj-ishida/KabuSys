# KabuSys

日本株向けの自動売買基盤（ライブラリ）の骨格実装です。  
データ取得（J-Quants）、DuckDBスキーマ、ETLパイプライン、データ品質チェック、監査ログ用スキーマなど、トレーディング・パイプラインに必要な主要要素を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。主な目的は以下の通りです。

- J-Quants API からの市場データ（株価日足、財務、取引カレンダー）の取得と保存
- DuckDB を用いた堅牢なスキーマ定義と初期化 (3層データモデル：Raw / Processed / Feature、Execution、Audit)
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質検査（欠損・スパイク・重複・日付不整合）
- 発注/約定の監査ログ用スキーマ（トレース可能なUUID連鎖）

設計上の特徴として、API レート制限・リトライ・トークン自動リフレッシュ・取得時刻（fetched_at）記録・冪等性（ON CONFLICT DO UPDATE）などを重視しています。

---

## 主な機能一覧

- J-Quants クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX 市場カレンダーの取得
  - レートリミッタ（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大3回）、401 時の自動トークンリフレッシュ
  - 取得時刻（UTC）を記録し Look-ahead Bias を防止
  - DuckDB へ冪等に保存する save_* 関数

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution レイヤーの DDL 定義
  - 初期化関数: init_schema(db_path)
  - 監査ログ用の初期化: init_audit_schema / init_audit_db

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL 実行: run_daily_etl()
  - 差分更新ロジック（最終取得日からの差分＋バックフィル）
  - カレンダーの先読み（デフォルト 90 日）
  - 品質チェック実行フロー統合

- データ品質チェック（kabusys.data.quality）
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比の閾値）
  - 主キー重複検出
  - 将来日付 / 非営業日データ検出
  - QualityIssue データモデルで問題を集約

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定 を追跡するためのテーブル群とインデックス
  - 冪等キー（order_request_id）、UTC タイムスタンプ運用設計

- 環境設定管理（kabusys.config）
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト経由）
  - KABUSYS_ENV / LOG_LEVEL などのシステム設定

---

## 要件

- Python 3.10 以上（PEP 604 のタイプ記法などを使用）
- 主要依存ライブラリ（例）:
  - duckdb
  - （標準ライブラリのみで動作する箇所も多いですが、実行するには duckdb をインストールしてください）

インストール例:
```
pip install duckdb
```

（プロジェクト全体の requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン / コードを入手

2. Python 環境を作成（推奨: venv / pyenv / conda）

3. 依存パッケージをインストール
   - 例: pip install duckdb

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に .env または .env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live; デフォルト: development)
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL; デフォルト: INFO)

例: .env（最低限の例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方

以下は代表的な利用例です。Python スクリプトや CLI ツールから呼び出して利用します。

- DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は .env で指定したパス（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

- 日次 ETL を実行（簡易）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を省略すると今日が対象
print(result.to_dict())
```

- 監査ログ用スキーマを追加
```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)  # 既存接続に監査テーブルを追加
```

- J-Quants クライアントを直接呼ぶ（トークンは settings.jquants_refresh_token を使用）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

# 例: 特定銘柄の株価取得
records = jq.fetch_daily_quotes(code="7203", date_from=None, date_to=None)
# DuckDB に接続して保存する場合は jq.save_daily_quotes(conn, records)
```

- 簡単なコマンドライン実行（ワンライナー）
```
python -c "from kabusys.data.schema import init_schema; from kabusys.data.pipeline import run_daily_etl; from kabusys.config import settings; conn=init_schema(settings.duckdb_path); print(run_daily_etl(conn).to_dict())"
```

注意:
- ETL の実行はネットワーク/API 呼び出しを伴います。API レート制限（デフォルト 120 req/min）やリトライ挙動に従います。
- run_daily_etl は内部で品質チェックを実行します（run_quality_checks を False にして無効化可能）。

---

## 主要 API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env, settings.is_live など

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続
  - get_connection(db_path)

- kabusys.data.jquants_client
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(...), save_market_calendar(...)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path)

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/                (発注実行関連の拡張ポイント)
      - __init__.py
    - strategy/                 (戦略実装用の拡張ポイント)
      - __init__.py
    - monitoring/               (監視用モジュール)
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py       (J-Quants API クライアント)
      - pipeline.py             (ETL パイプライン)
      - schema.py               (DuckDB スキーマ定義・初期化)
      - quality.py              (データ品質チェック)
      - audit.py                (監査ログスキーマ)
      - pipeline.py
    - その他（将来的に execution モジュールなど）

---

## 開発・運用上の注意

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を基に行われます。テストなどで自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants の API 呼び出しはレート制限・リトライ・トークンリフレッシュを考慮した実装になっていますが、運用時は実際の API 利用規約・レート制限に注意してください。
- DuckDB のファイルパスのディレクトリは自動作成されます（db_path が ":memory:" の場合はインメモリ）。
- 監査ログは基本的に削除しない運用を想定しています（FK は ON DELETE RESTRICT）。更新時は updated_at を必ず設定する設計です。
- 品質チェックは Fail-Fast ではなく全件収集する設計です。結果を見て運用側でどのように扱うか（停止 or 警告）を決定してください。

---

必要があれば、README に含める追加情報（例: サンプル .env.example、CI 実行手順、ユニットテスト実行方法、詳細なテーブル設計ドキュメントへのリンク等）を追記できます。どの情報を追加したいか教えてください。