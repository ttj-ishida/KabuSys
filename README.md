# KabuSys

日本株自動売買プラットフォーム（ライブラリ）  
このリポジトリは、J-Quants / JPX カレンダー 等から市場データを収集・整備し、戦略・発注・監視に必要なデータレイヤ（Raw / Processed / Feature / Execution）と監査ログ基盤を提供します。DuckDB を中心に冪等性・トレーサビリティ・データ品質チェックを重視した設計です。

---

## 概要（Project Overview）

KabuSys は以下を主な目的とするモジュール群を含みます。

- J-Quants API クライアント（時系列、財務、マーケットカレンダー）  
  - レート制限・リトライ・トークン自動更新を内蔵
- RSS ベースのニュース収集（収集 → 前処理 → DuckDB 保存 → 銘柄抽出）
- DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution 層および監査テーブル）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定・次/前営業日検索）
- データ品質チェックモジュール（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

戦略層（strategy）、実行層（execution）、監視（monitoring）用のパッケージ枠組みも用意されています。

---

## 主な機能（Features）

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務、マーケットカレンダーの取得
  - レート制限（120 req/min）に従ったスロットリング
  - 冪等的な DuckDB への保存（ON CONFLICT 句）
  - 自動トークンリフレッシュ（401 時に1回リトライ）
- ニュース収集
  - RSS 取得、XML の安全パース（defusedxml）
  - URL 正規化とトラッキングパラメータ除去、記事IDは SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証・ホストプライベート判定・リダイレクト検査）
  - DuckDB へトランザクション単位での冪等保存（INSERT ... RETURNING）
  - テキストから銘柄コード抽出（既知コードフィルタリング）
- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution / Audit のテーブル定義
  - 適切なインデックス定義と外部キー制約
- ETL パイプライン
  - 差分更新（最終取得日を参照）、バックフィル（後出し修正取り込み）
  - 日次 ETL エントリ（calendar → prices → financials → 品質チェック）
  - 品質チェックで検出した問題を集約して返却
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - DB 優先、未登録日は曜日フォールバック
- 監査ログ（audit）
  - signal_events / order_requests / executions を用いたトレーサビリティ
  - UUID ベースの冪等キー、ステータス遷移、UTC タイムスタンプ

---

## セットアップ手順（Setup）

前提:
- Python 3.9+（typing | future 機能を利用）
- ネットワークアクセス（J-Quants API、RSS 等）
- 必要なパッケージ（下記をインストール）

1. 仮想環境の作成（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最小例）:
   - pip install duckdb defusedxml

   （プロジェクト化されている場合は pyproject.toml / requirements.txt を利用してください。開発時は pip install -e . を使えます。）

3. 環境変数の設定:
   - .env ファイルをプロジェクトルートに配置すると自動的に読み込まれます（.env.local で上書き可能）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須の環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- KABUSYS_ENV: 環境 ("development" / "paper_trading" / "live") （省略時 "development"）
- LOG_LEVEL: ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")（省略時 "INFO"）

デフォルトの DB パス（環境変数で変更可）:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)

例 .env（簡易）:
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（Usage）

以下は代表的な操作例です。実行前に必要な環境変数を設定してください。

1) DuckDB スキーマ初期化
- インメモリまたはファイル DB を作成し全テーブルを生成します。

例:
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

2) 日次 ETL を実行する（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
- init_schema で作成した接続を渡して run_daily_etl を呼び出します。

例:
python - <<'PY'
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
conn = init_schema('data/kabusys.duckdb')
res = run_daily_etl(conn)  # 引数で target_date 等を指定可能
print(res.to_dict())
PY

3) ニュース収集ジョブを手動実行
- RSS を取得して raw_news に保存します。known_codes を渡すと銘柄紐付けも実施します。

例:
python - <<'PY'
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection
conn = init_schema('data/kabusys.duckdb')
known_codes = {'7203','6758'}  # 例: 有効な銘柄コードセット
result = run_news_collection(conn, known_codes=known_codes)
print(result)
PY

4) J-Quants API から直接データを取得して保存
- jquants_client の fetch_* / save_* を利用します。

例:
python - <<'PY'
from kabusys.data.schema import init_schema
from kabusys.data import jquants_client as jq
conn = init_schema('data/kabusys.duckdb')
token = jq.get_id_token()  # settings を使って自動的にリフレッシュトークンから取得
records = jq.fetch_daily_quotes(id_token=token, date_from=None, date_to=None)
jq.save_daily_quotes(conn, records)
PY

5) 品質チェックを単独で実行
例:
python - <<'PY'
from kabusys.data.schema import init_schema
from kabusys.data.quality import run_all_checks
from datetime import date
conn = init_schema('data/kabusys.duckdb')
issues = run_all_checks(conn, target_date=None, reference_date=date.today())
for i in issues:
    print(i)
PY

注意:
- J-Quants のレート制限や API エラー、RSS の SSRF 制約に注意して実行してください。
- 多くの関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。init_schema で返る接続を再利用してください。

---

## ディレクトリ構成（Directory structure）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・設定（.env 自動ロード、必須項目チェック）
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（fetch_* / save_*）
  - news_collector.py
    - RSS 取得・前処理・保存・銘柄抽出
  - pipeline.py
    - ETL パイプライン（run_daily_etl, run_prices_etl, ...）
  - schema.py
    - DuckDB スキーマ定義と init_schema / get_connection
  - calendar_management.py
    - market_calendar 管理、営業日判定（is_trading_day, next_trading_day, ...）
  - audit.py
    - 監査ログ（signal_events, order_requests, executions）初期化
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
- strategy/
  - __init__.py
  -（戦略実装用モジュール群を配置する場所）
- execution/
  - __init__.py
  -（発注・ブローカー連携ロジックを配置する場所）
- monitoring/
  - __init__.py
  -（監視・アラート周りの実装を配置する場所）

ルート:
- pyproject.toml（プロジェクト設定: 想定）
- .env / .env.local（任意、自動ロードされる）
- data/（デフォルトの DB 保存先）

---

## 設計上の注意点・運用メモ

- 自動環境変数ロードはプロジェクトルートの .git または pyproject.toml を探索して行います。テスト中や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- J-Quants API はページネーション対応。fetch 関数は pagination_key を用いて全件取得します。トークンはモジュールキャッシュされページ間で共有されます。
- DuckDB へは冪等保存（ON CONFLICT ... DO UPDATE / DO NOTHING）を実装しているため、ETL の再実行が安全に行えます。
- RSS パーサは defusedxml を使用して XML Bomb 等を防ぎ、受信サイズ上限（10MB）でメモリ DoS を防止します。
- カレンダー・ETL はバックフィルを行い、API の後出し修正に対応します。
- 監査ログは UTC タイムスタンプを前提としています（init_audit_schema で SET TimeZone='UTC' を実行）。

---

## 追加情報 / 開発

- 戦略や実行ロジックは strategy/ と execution/ に実装してください。これらは ETL で整形された features / ai_scores / signals などを入力として使用します。
- テストを書く際は、jquants_client の HTTP 呼び出しや news_collector._urlopen 等をモックすることを推奨します。
- ログレベルは環境変数 LOG_LEVEL で制御できます。

---

必要なら README にサンプル .env.example やコマンドラインユーティリティ（ CLI ）の使い方、より詳しい API ドキュメント（関数引数の説明や戻り値の例）を追加します。どの部分を拡張しますか？