# KabuSys — 日本株自動売買システム (README)

概要
----
KabuSys は日本株の自動売買やデータプラットフォームを構築するためのライブラリ群です。J-Quants API からの市場データ取得、DuckDB を用いたスキーマ定義・永続化、ETL パイプライン、データ品質チェック、監査ログ（トレーサビリティ）といった機能を提供します。設計は冪等性・トレーサビリティ・レート制御・リトライなど実運用を意識しています。

主な特徴
--------
- J-Quants API クライアント
  - OHLCV（日足）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制限（120 req/min）を守る固定間隔スロットリング
  - リトライ（指数バックオフ、最大 3 回）および 401 発生時の自動トークンリフレッシュ
  - ページネーション対応、取得時刻（fetched_at）を UTC で記録
- DuckDB スキーマ設計
  - Raw / Processed / Feature / Execution の多層スキーマ
  - 各種テーブル（raw_prices, raw_financials, market_calendar, features, signals, orders, trades, positions, など）とインデックス定義
  - 監査用スキーマ（signal_events, order_requests, executions）
- ETL パイプライン
  - 差分更新（最終取得日からの差分のみ取得）、バックフィルによる後出し修正吸収
  - 市場カレンダーの先読み（デフォルト 90 日）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 各ステップは独立してエラーハンドリング（1 ステップ失敗でも他は継続）
- データ品質チェック
  - 欠損値検出、前日比スパイク判定、主キー重複、将来日付/非営業日データ検出
  - 問題は QualityIssue オブジェクトとして収集（エラー／警告の分類）
- 監査ログ（トレーサビリティ）
  - シグナルから約定に至る UUID 連鎖を保持
  - 発注要求は冪等キー（order_request_id）で管理

セットアップ手順
----------------
前提
- Python 3.10 以上（型注釈に | 演算子、Literal 等を使用）
- pip が利用可能

1. リポジトリをクローン（開発環境での例）
   - git clone <リポジトリURL>

2. 開発インストール（プロジェクトルートに setup がある場合）
   - pip install -e . もしくは必要な依存パッケージをインストールしてください。
   - 必要な主な依存例:
     - duckdb
     - （その他、運用で Slack 等に通知する場合は slack_sdk 等）

   例:
   - pip install duckdb

3. 環境変数の設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと、自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env に設定が必要な主なキー（例）
- JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
- KABU_API_PASSWORD=your_kabu_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトあり）
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C0123456789
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # development | paper_trading | live
- LOG_LEVEL=INFO

使い方（簡単な例）
-----------------

1) DuckDB スキーマの初期化
- データ用 DB を初期化して接続を取得する例:

```python
from kabusys.data.schema import init_schema

# data/kabusys.duckdb を作成して全テーブルを初期化
conn = init_schema("data/kabusys.duckdb")
```

- 監査ログテーブルを既存接続に追加する例:

```python
from kabusys.data.audit import init_audit_schema

# 既に init_schema で得た conn に監査テーブルを追加
init_audit_schema(conn)
```

2) 日次 ETL を実行する（デフォルトは本日）
- シンプルな実行例:

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # デフォルトで本日をターゲットに実行
print(result.to_dict())
```

- ETL 実行時のオプション
  - id_token を外部で取得・注入してテスト可能（get_id_token を参照）
  - run_quality_checks=False で品質チェックをスキップ可能
  - backfill_days や calendar_lookahead_days を引数で調整可能

3) J-Quants API を直接使う（必要に応じて）
- トークン取得・データ取得:

```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

token = get_id_token()  # settings.jquants_refresh_token を使う
quotes = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
```

注意点・運用メモ
- レート制限: J-Quants は 120 req/min。クライアントは内部で固定間隔レートリミッタを実装しています（モジュール内で制御）。
- 冪等性: データ保存は ON CONFLICT DO UPDATE を用いているため、再実行で重複を発生させません。
- 品質チェック: 重大な品質問題は QualityIssue に severity="error" として返りますが、ETL は可能な限り継続して実行します（呼び出し元が判定）。
- 時刻: 監査ログや fetched_at は UTC で記録する方針です。
- 自動 .env 読み込み: パッケージはプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

ディレクトリ構成
--------------
主要なファイル構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py            # パッケージ定義、バージョン
  - config.py              # 環境変数・設定管理（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py    # J-Quants API クライアント（取得・保存ロジック）
    - schema.py            # DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py          # ETL パイプライン（差分取得、品質チェック等）
    - quality.py           # データ品質チェック
    - audit.py             # 監査ログ（トレーサビリティ）テーブル定義・初期化
    - pipeline.py
  - strategy/
    - __init__.py          # 戦略関連（未実装箇所のエントリ）
  - execution/
    - __init__.py          # 発注/実行関連（未実装箇所のエントリ）
  - monitoring/
    - __init__.py          # 監視・モニタリング（未実装箇所のエントリ）

各モジュールの概要
- config.py: 環境変数のパース（.env のクォートやエスケープ対応）、settings オブジェクトでアプリケーション設定を取得。
- data/jquants_client.py: HTTP リクエストラッパー、トークン管理、fetch_* / save_* 関数群。
- data/schema.py: 全テーブルの CREATE DDL と init_schema 関数。
- data/pipeline.py: 差分 ETL のコア（run_daily_etl 等）。
- data/quality.py: 欠損・重複・スパイク・日付不整合チェック。
- data/audit.py: 監査ログ用テーブルと初期化関数。

拡張・開発のヒント
------------------
- 戦略や実行ロジック（strategy, execution パッケージ）は拡張用のエントリポイントです。Signal 生成やリスク管理、発注の実装はここに追加してください。
- DuckDB スキーマは _ALL_DDL / _INDEXES を編集して拡張できます。init_schema は冪等なので既存 DB に対して追加テーブルを作成できます。
- 品質チェック（quality.py）は SQL による効率的な実装になっているため、新しいチェックは同様のパターンで追加可能です。

サポート / 貢献
---------------
- バグ報告や機能要望はリポジトリの issue を利用してください。
- コントリビュートは歓迎します。ローカルでユニットテストや linter を実行してから PR を送ってください。

ライセンス
----------
- リポジトリの LICENSE に従ってください（ここでは指定なし）。

以上。質問や README の追加情報（例: CI、デプロイ手順、より詳しい使用例など）を希望される場合は教えてください。