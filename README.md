# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）のコードベース用 README（日本語）。

概要・機能・セットアップ・使い方・ディレクトリ構成をまとめています。開発中のライブラリであり、一部モジュール（strategy / execution / monitoring）はプレースホルダです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを支えるデータ基盤とユーティリティ群を提供します。主に以下を目的としています。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する ETL
- RSS フィードを収集してニュース記事を DuckDB に保存するニュースコレクタ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 市場カレンダー管理（営業日判定、前後営業日検索）
- 監査ログ（シグナル→発注→約定 のトレーサビリティ）用スキーマ
- 環境変数による設定管理（.env/.env.local の自動読み込み）

設計上のポイント：
- API レート制御（J-Quants: 120 req/min の固定間隔スロットリング）
- リトライ（指数バックオフ、401 の自動トークン更新を含む）
- 冪等性（DuckDB への保存は ON CONFLICT で上書き/排除）
- SSRF / XML Bomb 等のセキュリティ対策（news_collector）

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須環境変数検証用の Settings

- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（refresh token → id token）
  - 日次株価（OHLCV）、財務（四半期）、マーケットカレンダーの取得
  - レートリミッタ・リトライ・ページネーション対応
  - DuckDB へ冪等保存する save_* 関数

- RSS ニュース収集（kabusys.data.news_collector）
  - RSS 取得・XML パース（defusedxml 使用）
  - URL 正規化・tracking params 除去・記事 ID に SHA-256 ハッシュ
  - SSRF チェック・サイズ制限（最大 10MB）
  - DuckDB へ冪等保存（INSERT ... RETURNING を利用）
  - 記事から銘柄コード抽出（4 桁数値）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス作成、init_schema() / get_connection()

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL 実行（市場カレンダー→株価→財務→品質チェック）
  - 差分取得（最終取得日ベース）、backfill による後出し訂正吸収
  - run_daily_etl により ETL 結果を ETLResult で取得

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、get_trading_days、calendar_update_job

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの初期化関数
  - すべて UTC 保存ポリシー、トレーサビリティのための制約とインデックス

- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合チェック
  - run_all_checks で総合実行、QualityIssue オブジェクトで結果返却

---

## 要件

- Python 3.10 以上（PEP 604 のユニオン型記法などを使用）
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml

（他は標準ライブラリで賄える設計です。必要に応じて追加パッケージを requirements.txt にまとめてください）

---

## インストール（開発環境）

1. リポジトリをチェックアウト
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール

例:
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
# またはパッケージ化されている場合:
# python -m pip install -e .
```

---

## 環境変数（.env）

kabusys.config.Settings が参照する主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN  - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD       - kabuステーション API のパスワード
- SLACK_BOT_TOKEN         - Slack 通知用トークン
- SLACK_CHANNEL_ID        - Slack チャネル ID

オプション / デフォルトあり:
- KABUSYS_API_BASE_URL    - kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH             - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH             - SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV             - environment (development | paper_trading | live), デフォルト: development
- LOG_LEVEL               - ログレベル（DEBUG/INFO/...）, デフォルト: INFO

自動ロード:
- プロジェクトルート（.git または pyproject.toml の存在）を基に `.env` と `.env.local` を自動でロードします。
- OS 環境変数が優先され、.env.local は .env の上書きとなります。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## データベース初期化

DuckDB スキーマを初期化する例:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成してテーブルを作る
```

監査ログ用スキーマを追加するには：

```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema() の戻り値を流用可能
init_audit_schema(conn)
```

---

## 使い方（簡単な例）

1) 日次 ETL を実行する最小スクリプト:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 引数で target_date, id_token 等を指定可能
print(result.to_dict())
```

2) ニュース収集（RSS）を実行する例:

```python
import duckdb
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.config import settings

conn = duckdb.connect(settings.duckdb_path)
# 初回は schema.init_schema でテーブルを作成しておくこと
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(res)  # {source_name: 新規保存件数}
```

3) カレンダー夜間バッチ（calendar_update_job）:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print("saved:", saved)
```

4) 直接 J-Quants の日次株価を取得する:

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使用して idToken を取得
records = fetch_daily_quotes(id_token=token, code="7203", date_from=..., date_to=...)
```

---

## 設計上の注意点

- J-Quants API はレート制限（120 req/min）を守るために内部で固定間隔スロットリングと指数バックオフを利用しています。大量取得時は処理時間がかかります。
- fetch_* 系はページネーション対応です。get_id_token は 401 時の自動リフレッシュを行います。
- news_collector は受信サイズ上限・gzip 解凍後の検査・SSRF 対策・XML の安全パース（defusedxml）を行います。
- DuckDB への保存は冪等（ON CONFLICT 句）で設計されています。

---

## ディレクトリ構成

主要ファイル・フォルダ（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                - 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      - J-Quants API クライアント + DuckDB 保存関数
    - news_collector.py      - RSS ニュース収集と保存ロジック
    - schema.py              - DuckDB スキーマ定義・初期化
    - pipeline.py            - ETL パイプラインの実装（run_daily_etl 等）
    - calendar_management.py - マーケットカレンダー管理、営業日判定
    - audit.py               - 監査ログ（signal/order/execution）スキーマと初期化
    - quality.py             - データ品質チェック
  - strategy/
    - __init__.py            - 戦略層（プレースホルダ）
  - execution/
    - __init__.py            - 発注実行層（プレースホルダ）
  - monitoring/
    - __init__.py            - 監視関連（プレースホルダ）

---

## ロギング・デバッグ

- settings.log_level でログレベルを制御できます（LOG_LEVEL 環境変数）。
- モジュールごとに logger 名が設定されています（例: kabusys.data.jquants_client）。
- ETL は各ステップで例外を捕捉して続行する設計です。重大なエラーは ETLResult.errors に蓄積されます。

---

## 今後の拡張ポイント（参考）

- strategy / execution / monitoring の実装（発注ロジック・リスク管理・監視アラート）
- Slack 通知連携（settings の Slack 設定を利用）
- テストカバレッジの追加（news_collector のネットワーク周りのモック等）
- requirements.txt / packaging（pip install 対応）

---

README はここまでです。必要であれば README にサンプル .env.example を追加したり、より詳しい API 使用例（引数の説明や戻り値の型）を追記できます。どの部分を詳しく書くか指定してください。