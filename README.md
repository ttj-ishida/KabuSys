# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants API を使った市場データ取得、DuckDB ベースのスキーマ定義・初期化、ETL（差分取得＋品質チェック）、監査ログ用スキーマなどを提供します。

主な用途：
- J-Quants から株価・財務・市場カレンダーを安全に取得して DuckDB に保存
- ETL パイプラインで差分更新・バックフィル・品質チェックを実行
- シグナル→発注→約定までの監査ログを保存してトレーサビリティを確保

対応 Python バージョン：
- Python 3.10+

注意：本 README はリポジトリ内のソースコード（src/kabusys 以下）を基に作成しています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易例）
- 環境変数一覧（.env）
- ディレクトリ構成

---

プロジェクト概要
- J-Quants API から株価日足（OHLCV）、四半期財務データ、JPX 市場カレンダーを取得するクライアントを提供
- DuckDB を用いたスキーマ（Raw / Processed / Feature / Execution / Audit）を定義・初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）を提供
- 品質チェックモジュールで欠損・スパイク・重複・日付不整合を検出
- 監査ログ（signal_events / order_requests / executions）を用いてトレーサビリティを確保

機能一覧
- 環境変数自動読み込み（プロジェクトルートの .env, .env.local を自動で読み込む）
- J-Quants API クライアント
  - レート制限（120 req/min）に従った固定間隔スロットリング
  - 408/429/5xx に対するリトライ（指数バックオフ、最大 3 回）
  - 401 を受けた場合のトークン自動リフレッシュ（1回）
  - ページネーション対応
  - 取得時刻（fetched_at）を UTC で記録する設計
- DuckDB スキーマ管理
  - init_schema(db_path) によるテーブル作成（冪等）
  - audit 用スキーマの追加 init_audit_schema(conn)
- ETL パイプライン
  - run_prices_etl, run_financials_etl, run_calendar_etl（差分 + バックフィル）
  - run_daily_etl：日次 ETL を一括実行（品質チェックオプション）
  - 差分取得の自動判定（DB の最終取得日からの再取得）
- データ品質チェック
  - 欠損（OHLC の NULL）
  - スパイク（前日比 > 閾値）
  - 主キー重複
  - 将来日付 / 非営業日データ
  - run_all_checks による一括実行
- 監査ログ（audit）
  - signal_events / order_requests / executions のテーブル定義と初期化
  - 発注フローのトレーサビリティを UUID 連鎖で追跡

---

セットアップ手順

1. リポジトリをクローンし、仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   - 本コードで最低必要なのは duckdb（その他は標準ライブラリで実装）
   ```bash
   pip install duckdb
   ```
   - （必要に応じて）本パッケージを開発モードでインストール
   ```bash
   pip install -e .
   ```

3. 環境変数（.env）を作成
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと、自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用途）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env の例:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

使い方（基本例）

1) DuckDB スキーマを初期化する
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照（デフォルト: data/kabusys.duckdb）
conn = schema.init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行する（品質チェックあり）
```python
from kabusys.data import pipeline
from kabusys.config import settings

# 既に init_schema で得た conn を再利用して実行するのが推奨
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

3) 監査スキーマ（order/event/executions）を初期化する
```python
from kabusys.data import audit, schema
conn = schema.init_schema(settings.duckdb_path)
audit.init_audit_schema(conn)
```

4) J-Quants API を直接利用する（トークン自動管理あり）
```python
from kabusys.data import jquants_client as jq

# id_token を省略すると内部キャッシュと自動リフレッシュが使われます
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# 保存は DuckDB 接続を渡す
jq.save_daily_quotes(conn, quotes)
```

備考（設計上のポイント）
- jquants_client は API レート制限（120 req/min）を内部で守る実装です。
- 401 を受けた場合はリフレッシュトークンから id_token を更新して 1 回だけリトライします。
- fetch 系関数はページネーションに対応しています。
- 保存関数は冪等（ON CONFLICT DO UPDATE）で重複を排除します。
- ETL は差分更新がデフォルト。バックフィル日数 (デフォルト 3 日) により後出し修正を吸収します。
- 品質チェックは Fail-Fast ではなく、検出結果を集めて呼び出し元に返します。

---

API（主要な関数・クラス）
- kabusys.config.settings — 環境設定プロパティ（settings.jquants_refresh_token 等）
- kabusys.data.schema.init_schema(db_path) -> duckdb connection
- kabusys.data.schema.get_connection(db_path)
- kabusys.data.jquants_client.get_id_token(refresh_token=None)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)
- kabusys.data.quality.run_all_checks(conn, target_date=None, ... )
- kabusys.data.audit.init_audit_schema(conn)
- kabusys.data.audit.init_audit_db(db_path)

---

開発者向けメモ
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に行われます。テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にしてください。
- DuckDB の初回作成時に親ディレクトリが自動作成されます。
- 時刻は UTC で保存する方針（監査ログ初期化時に SET TimeZone='UTC' を実行）。

---

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数と設定管理
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得・保存）
    - schema.py                   — DuckDB スキーマ定義と初期化
    - pipeline.py                 — ETL パイプライン（差分更新・品質チェック）
    - audit.py                    — 監査ログスキーマ初期化
    - quality.py                  — データ品質チェック
    - pipeline.py
  - execution/
    - __init__.py
  - strategy/
    - __init__.py
  - monitoring/
    - __init__.py

（上記は本リポジトリに含まれる主要なモジュール一覧です）

---

トラブルシューティング
- DuckDB に接続できない/ファイルが作成されない
  - DUCKDB_PATH の親ディレクトリに書き込み権限があるか確認してください。
- J-Quants API 呼び出しで 401 が返る
  - 環境変数 JQUANTS_REFRESH_TOKEN が正しいか確認してください。get_id_token はリフレッシュトークンから id_token を発行します。
- .env が読み込まれない
  - プロジェクトルートの判定は __file__ を起点に親ディレクトリを探索します。CWD ではなくパッケージ位置が基準です。自動ロードを無効化して手動で環境をセットすることもできます。

---

貢献・拡張案
- kabu ステーションや他のブローカーとの実際の発注実装（execution 層の実装）
- strategy パッケージに戦略実装とバックテスト機能
- モニタリング用メトリクス収集 / アラート（monitoring）
- Docker イメージ化や CI ワークフロー（ETL の定期実行）

---

ライセンス
- リポジトリの LICENSE を参照してください（本ドキュメントには含まれていません）。

---

以上。必要であれば README に追記したいサンプルスクリプト、CI / Docker の例、より詳しい環境変数説明やサンプル .env.example を作成します。どの情報を優先して追加しますか？