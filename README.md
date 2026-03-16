# KabuSys

軽量な日本株向け自動売買プラットフォーム用ライブラリ（プロトタイプ）

バージョン: 0.1.0

概要:
- J-Quants や kabuステーション などからデータを取得して DuckDB に蓄積し、
  戦略・発注・監査・モニタリングの基盤となる機能を提供します。
- 設計上のポイント：API レート制御、リトライ、トークン自動リフレッシュ、データの冪等保存、
  監査ログのトレーサビリティ、データ品質チェックなどを備えます。

主な機能一覧
- 環境変数・設定管理（kabusys.config）
  - .env/.env.local 自動読み込み（プロジェクトルートを .git または pyproject.toml で判定）
  - 必須環境変数取得・検証、環境種別（development / paper_trading / live）やログレベル設定
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レートリミット（120 req/min）、リトライ（指数バックオフ・401時のトークン自動更新）対応
  - DuckDB へ冪等に保存するユーティリティ（raw_prices / raw_financials / market_calendar）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス定義、初期化用 API（init_schema / get_connection）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions など監査用テーブル群の初期化
  - 発注の冪等キー（order_request_id）などトレーサビリティを担保
- データ品質チェック（kabusys.data.quality）
  - 欠損、主キー重複、前日比スパイク、将来日付・非営業日データ検出
  - QualityIssue 型リストで結果を返却（エラー／警告の分類）
- （将来）戦略・実行・モニタリング用の名前空間（kabusys.strategy, kabusys.execution, kabusys.monitoring）

動作要件
- Python 3.10 以上（型注釈に | 演算子を利用）
- 依存（例）
  - duckdb
  - （標準ライブラリ以外の追加ライブラリが必要な場合は requirements.txt / pyproject.toml を参照してください）

セットアップ手順（開発環境向け）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb
   - （プロジェクト配布に pyproject.toml や requirements.txt があればそれを使用）
   - 例: pip install -e .   （プロジェクトがパッケージ化されている場合）

3. 環境変数を用意
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` または `.env.local` を配置すると自動で読み込まれます。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主要な環境変数例（.env に記述する）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 省略可（デフォルト）
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb  # 省略可（デフォルト）
     - SQLITE_PATH=data/monitoring.db   # 省略可（デフォルト）
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

使い方（基本例）
- DuckDB スキーマを初期化して J-Quants から日足を取得し保存する例:

```python
from kabusys.config import settings
from kabusys.data import jquants_client
from kabusys.data.schema import init_schema
from datetime import date

# DB 初期化（ファイルまたは ":memory:"）
conn = init_schema(settings.duckdb_path)

# 日付指定でデータを取得
records = jquants_client.fetch_daily_quotes(
    date_from=date(2023, 1, 1),
    date_to=date(2023, 12, 31),
    # code="7203"  # 特定銘柄を指定する場合
)

# DuckDB に保存（冪等）
inserted = jquants_client.save_daily_quotes(conn, records)
print(f"保存件数: {inserted}")
```

- 監査ログテーブルを初期化（既存接続に追加）:

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # conn は init_schema の戻り値など
```

- データ品質チェックの実行:

```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)  # target_date を設定するとその日だけチェック
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
    for row in issue.rows:
        print(row)
```

- J-Quants の ID トークンを直接取得する例（通常は内部で自動更新される）:

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

設定の読み込みと挙動
- .env のパースは POSIX ライクな書式に対応（export プレフィックス、引用符、コメント処理など）。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に実施します。見つからない場合はスキップします。
- 必須の環境変数が未設定の場合は Settings のプロパティアクセス時に ValueError が発生します。

注意点 / 設計メモ
- J-Quants クライアントはレート制限（120 req/min）を守るため固定間隔スロットリングを行います。大量取得時は時間がかかります。
- HTTP エラーやネットワーク障害に対してリトライ（最大 3 回）を行い、401 は自動的にトークン更新して 1 回リトライします。
- DuckDB への保存は ON CONFLICT DO UPDATE により冪等に実装されています（重複挿入が発生しても更新されます）。
- 監査ログは削除を想定しておらず、発注トレーサビリティを重視しています。
- すべてのタイムスタンプは原則 UTC で扱います（監査ログ初期化時に SET TimeZone='UTC' を設定します）。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py                 : パッケージ初期化（__version__ など）
  - config.py                   : 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py         : J-Quants API クライアント（取得・保存ロジック）
    - schema.py                 : DuckDB スキーマ定義と初期化（Raw/Processed/Feature/Execution）
    - audit.py                  : 監査ログテーブル定義・初期化
    - quality.py                : データ品質チェック
  - strategy/
    - __init__.py               : 戦略関連名前空間（将来の拡張用）
  - execution/
    - __init__.py               : 発注／ブローカー連携名前空間（将来の拡張用）
  - monitoring/
    - __init__.py               : モニタリング関連名前空間（将来の拡張用）

開発・運用上のヒント
- テストなどで自動 .env 読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は init_schema() を最初に一度だけ呼び、以降は get_connection() で接続を得る運用が想定されます。
- データ取得処理をバッチ化する際は、J-Quants のページネーションとレート制御仕様に留意してください。
- 監査テーブルと実行テーブルを分離しておくことで、監査記録を削除せずに運用できます。

この README はコードベースの現状（v0.1.0）に基づく概要ドキュメントです。詳細な使用方法や運用手順は将来的にドキュメント（DataPlatform.md / DataSchema.md など）を整備して補完してください。