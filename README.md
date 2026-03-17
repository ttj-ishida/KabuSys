# KabuSys

日本株自動売買システムのコアライブラリ（データ取得・ETL・スキーマ・監査ログ・ニュース収集など）。  
このリポジトリは主にデータプラットフォーム（J‑Quants からのデータ取得、DuckDB スキーマ、ETL、品質チェック、ニュース収集、監査ログ）を提供します。

## 主な特徴
- J‑Quants API クライアント
  - 株価日足（OHLCV）・財務（四半期 BS/PL）・JPX マーケットカレンダー取得
  - レート制御（120 req/min）・リトライ（指数バックオフ）・トークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look‑ahead Bias を抑制
  - DuckDB への冪等保存（ON CONFLICT による更新）
- ETL パイプライン
  - 差分更新（最終取得日に基づく差分取得）とバックフィル対応
  - 市場カレンダーの先読み（lookahead）対応
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス定義・冪等なスキーマ初期化
- ニュース収集（RSS）
  - RSS から記事取得 → 正規化 → DuckDB へ冪等保存（raw_news）
  - 記事IDは正規化 URL の SHA‑256（先頭 32 文字）
  - SSRF 対策、サイズ制限、XML セキュリティ対策（defusedxml）
  - 銘柄コード抽出・news_symbols への紐付け
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定までを UUID 連鎖でトレース
  - order_request_id による冪等性・UTC タイムゾーン固定

---

## 機能一覧（ファイル／モジュールベース）
- kabusys.config
  - .env の自動ロード (.git または pyproject.toml を基準)
  - 環境変数ラッパ（settings）
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token（トークンリフレッシュ）
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
  - URL 正規化・SSRF 対策・gzip サイズ制限
- kabusys.data.schema
  - init_schema, get_connection（DuckDB スキーマ初期化）
- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
  - 差分取得・バックフィル・品質チェック統合
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.audit
  - init_audit_schema, init_audit_db（監査ログテーブルの初期化）
- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks

---

## 前提条件
- Python 3.10+
- 必要なライブラリ（一例）
  - duckdb
  - defusedxml

例:
pip install duckdb defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux / macOS) または .venv\Scripts\activate (Windows)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または最低限:
     - pip install duckdb defusedxml

3. 環境変数 / .env を準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` を置くと自動読み込みされます。
   - 読み込み順序: OS 環境変数 > .env > .env.local（.env.local は .env を上書き）
   - 自動ロードを無効にするには:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN (必須) — J‑Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知用（必要に応じて）
   - SLACK_CHANNEL_ID (必須) — Slack チャネル ID
   - 参考（任意／デフォルトあり）
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live; デフォルト development)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL; デフォルト INFO)

.env の例:
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## 使い方（よく使う API の例）

以下は Python REPL / スクリプトでの簡単な利用例です。

- DuckDB スキーマを初期化して接続を得る
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

- 監査用 DB を初期化する（監査専用 DB を別ファイルで管理したい場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL を実行する（デフォルト: 今日を対象）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())  # ETL 結果の概要
```

- 市場カレンダーの夜間更新ジョブを実行
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

- ニュース収集（RSS）を実行
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 銘柄抽出で使用する有効なコード集合（例: 既知銘柄リスト）
known_codes = {"7203", "6758", "9984"}  # 必要に応じて取得
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- J‑Quants から直接データを取得して保存
```python
from kabusys.data import jquants_client as jq

# トークンを settings から自動取得（内部でリフレッシュされる）
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

- 品質チェックを単独で実行
```python
from kabusys.data.quality import run_all_checks
from datetime import date

issues = run_all_checks(conn, target_date=date(2024,3,1))
for i in issues:
    print(i)
```

パラメータや戻り値の詳細は各モジュールの docstring を参照してください。

---

## 注意事項 / 実装上のポイント
- J‑Quants クライアント
  - レート制限は固定間隔スロットリング（120 req/min）で制御
  - 再試行: 最大 3 回、408/429/5xx を対象に指数バックオフ
  - 401 受信時はリフレッシュトークンで id_token を再取得し 1 回再試行
  - ページネーションを自動処理し、取得時刻 fetched_at を UTC Z 形式で保存
- ニュース収集
  - defusedxml を利用して XML 攻撃を防止
  - SSRF 対策: リダイレクト先や初期ホストに対してプライベート IP チェックを実施
  - 応答サイズ制限（10MB）と gzip 解凍後のチェック（Gzip Bomb 対策）
  - 記事 ID は URL 正規化後に SHA‑256 の先頭 32 文字を使用（冪等性）
- データベース
  - DuckDB を使用。init_schema() で必要な全テーブル／インデックスを作成（冪等）
  - audit 用スキーマは UTC タイムゾーンに固定
- 環境変数自動ロード
  - パッケージからプロジェクトルートを探索し .env / .env.local を読み込みます
  - テスト時などに自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定

---

## ディレクトリ構成（主要ファイル）
プロジェクトのルートに `src/kabusys` を想定した構成の抜粋です。

- src/kabusys/
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
    (戦略関連モジュールは将来的に追加)
  - execution/
    - __init__.py
    (注文送信・ブローカー連携用のモジュールを想定)
  - monitoring/
    - __init__.py

（実際のリポジトリには追加ファイル・テスト・ドキュメントが含まれる場合があります）

---

## よくある運用パターン
- 初期セットアップ
  1. init_schema() で DuckDB を作成
  2. run_daily_etl をスケジューラ（cron / Airflow / dagster 等）で毎朝実行
  3. calendar_update_job を夜間バッチで走らせてカレンダーを先読み
  4. run_news_collection をポーリング（頻度は媒体に依存）で実行
- ライブ運用
  - KABUSYS_ENV=live を設定し、戦略→signals→signal_queue→execution フローを組み合わせる
  - audit テーブルで完全なトレーサビリティを確保

---

## サポート / 拡張
- strategy / execution / monitoring パッケージはインターフェースを想定しており、ここに戦略ロジック・実行ロジック（ブローカー API）・監視（Slack 通知等）を実装していきます。
- テスト時には設定の自動ロードを無効にして明示的に環境変数を注入してください（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

README に記載の API 例や環境変数はソースコードの docstring / settings に基づいています。詳細は各モジュールの docstring を参照してください。必要であれば、README に CLI 例やデプロイ手順（systemd / Docker / Airflow）を追加できます。