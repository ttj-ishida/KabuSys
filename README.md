# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（KabuSys）。  
J-Quants からの市場データ取得、DuckDB での永続化、ニュース収集、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レート制限（120 req/min）準拠、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）の記録による Look-ahead Bias 防止
  - DuckDB への冪等保存（ON CONFLICT による更新）
- ETL パイプライン
  - 差分更新（最終取得日を参照して未取得分のみ取得）
  - backfill による後出し修正吸収
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）
- ニュース収集モジュール
  - RSS フィード取得、テキスト前処理、記事ID の生成（URL 正規化 + SHA-256）
  - SSRF 対策、XML 攻撃対策（defusedxml）、レスポンスサイズ制限
  - DuckDB へ冪等保存（INSERT ... RETURNING、トランザクション）
  - 銘柄コード抽出（テキスト中の 4 桁コード）
- マーケットカレンダー管理
  - 営業日判定、前後営業日検索、範囲内営業日取得、JPX カレンダーの夜間差分更新ジョブ
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティを確保するテーブル群
  - order_request_id を冪等キーとして二重発注を防止
- DuckDB スキーマ定義
  - Raw / Processed / Feature / Execution / Audit レイヤーのテーブル定義と初期化ユーティリティ

---

## 動作要件

- Python 3.10 以上（型注釈に PEP 604（|）を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - defusedxml

実際の環境では Slack 通知や証券 API 連携のために追加パッケージ（slack-sdk 等）を導入する場合があります。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン / ダウンロード
2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （もしパッケージ化された setup/pyproject がある場合）pip install -e .
4. DuckDB の初期化（例）:
   - Python REPL / スクリプトで:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
   - デフォルトの DuckDB ファイルパスは `data/kabusys.duckdb`（settings.duckdb_path）

---

## 環境変数 / .env

kabusys は起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` / `.env.local` を自動読み込みします。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（Settings クラスを参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack Bot のトークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先のチャンネル ID（必須）

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)。デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)。デフォルト: INFO

例 (.env):
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（代表的な API と実行例）

以下はモジュールをプログラムから利用する基本例です。実行はスクリプトやスケジューラ（cron・Airflow 等）から行います。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルがなければ生成し、全テーブルを作成
```

2) 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)  # すでに init_schema してある DB に接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS から記事を取得して保存、銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 有効な銘柄コードのセット（抽出フィルタ）
known_codes = {"7203", "6758", "9984", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: new_records_count}
```

4) カレンダー差分更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved={saved}")
```

5) 監査ログスキーマの初期化（audit 用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
```

6) J-Quants の生データ取得（個別呼び出し）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用して idToken を取得
records = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,12,31))
```

---

## 主要関数 / モジュールの説明

- kabusys.config
  - Settings クラス経由で環境変数を参照。自動で .env / .env.local をプロジェクトルートから読み込み。
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB への保存）
  - get_id_token（リフレッシュトークンから idToken を取得）
- kabusys.data.schema
  - init_schema(db_path): DuckDB の全テーブルを作成して接続を返す
  - get_connection(db_path): 既存 DB へ接続
- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl: 日次フローの総合エントリポイント（オプションで品質チェック有効）
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
  - extract_stock_codes（記事テキストから銘柄コード抽出）
- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job
- kabusys.data.quality
  - 各種品質チェック（欠損、重複、スパイク、日付不整合）
  - run_all_checks
- kabusys.data.audit
  - 監査用テーブルの初期化（init_audit_schema, init_audit_db）

---

## ディレクトリ構成

(主要ファイル / モジュールを抜粋)

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + DuckDB 保存
    - news_collector.py      # RSS ニュース収集・保存・銘柄抽出
    - schema.py              # DuckDB スキーマ定義・初期化
    - pipeline.py            # ETL パイプライン（差分更新・日次統合）
    - calendar_management.py # マーケットカレンダー関連ユーティリティ
    - audit.py               # 監査ログ（シグナル→発注→約定）スキーマ
    - quality.py             # データ品質チェック
  - strategy/                 # 戦略関連（未実装箇所のプレースホルダ）
    - __init__.py
  - execution/                # 発注実行関連（プレースホルダ）
    - __init__.py
  - monitoring/               # 監視・メトリクス（プレースホルダ）
    - __init__.py

---

## 開発メモ / 注意点

- 自動 .env 読み込み:
  - プロジェクトルートの `.env` → `.env.local` の順で読み込みます。OS 環境変数は上書きされないよう保護されます（.env.local は override=True だが OS 環境変数は protected）。
  - テストや特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化してください。
- DuckDB:
  - init_schema() は冪等的にテーブルを作成します。既に存在するテーブルはそのまま残ります。
  - INSERT ... RETURNING を使う箇所があるため、DuckDB の該当バージョンを利用してください（一般的な最新 DuckDB を推奨）。
- ネットワーク / セキュリティ:
  - news_collector は SSRF 対策（スキーム検査、プライベートホスト検査）や XML 攻撃対策（defusedxml）を実装しています。
  - J-Quants API はレートリミットに注意（既にコード内でレート制御あり）。
- テストの容易性:
  - jquants_client の id_token キャッシュや news_collector の _urlopen はテスト用にモック可能です（コード内で注記あり）。
- ログレベルと環境:
  - KABUSYS_ENV と LOG_LEVEL を設定して実行環境やログ出力を制御してください。

---

## 今後の拡張案（参考）

- strategy / execution 層の実装（ポートフォリオ最適化、リスク管理、注文送信・再送制御）
- Slack 通知やモニタリング用 Prometheus / Grafana 連携
- CI テストスイート（ETL ローカルテスト用のモック J-Quants サーバ等）
- Docker コンテナ化・運用用 compose / systemd ユニット

---

ご不明点や README へ追加してほしい内容（例: 具体的な .env.example、requirements.txt、実運用のデプロイ手順等）があれば教えてください。README を拡張してドキュメント化します。