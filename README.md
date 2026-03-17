# KabuSys

日本株のデータ収集・ETL・監査・ニュース収集を行う自動売買基盤のライブラリ（KabuSys）です。本リポジトリはデータ層（DuckDB）、J-Quants からのデータ取得、ニュース収集、ETL パイプライン、品質チェック、マーケットカレンダー管理、監査ログ初期化のためのモジュールを含みます。

## 特徴（機能一覧）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）とリトライ（指数バックオフ）、401 時の自動トークンリフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアス回避を意識した設計
- DuckDB ベースのスキーマ（冪等なテーブル作成）
  - Raw / Processed / Feature / Execution / Audit レイヤーのテーブル定義
  - 適切なインデックスを作成
- ETL パイプライン（差分取得・バックフィル・品質チェック）
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新と backfill による後出し修正吸収
- ニュース収集（RSS）
  - RSS フィードから記事を取得して raw_news に保存
  - URL 正規化・トラッキングパラメータ除去・SSRF 対策・サイズ制限等の安全対策
  - 銘柄コード抽出と news_symbols への紐付け
- マーケットカレンダー管理
  - 営業日判定、前後営業日探索、カレンダーの夜間差分更新
  - DB 登録優先で、未登録日は曜日ベースでフォールバック
- 監査ログ（Audit）
  - signal → order_request → execution までトレース可能な監査テーブルの初期化
  - order_request_id による冪等性、UTC タイムスタンプ運用
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合検出
  - QualityIssue を返し、呼び出し側で重大度に応じた対応が可能

---

## 必要な環境変数（主な設定）
アプリケーション設定は環境変数（またはプロジェクトルートの `.env`, `.env.local`）から読み込みます。必須の主要キー：

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意／デフォルトあり：
- KABUSYS_ENV — `development | paper_trading | live`（デフォルト: `development`）
- LOG_LEVEL — `DEBUG | INFO | WARNING | ERROR | CRITICAL`（デフォルト: `INFO`）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: `http://localhost:18080/kabusapi`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視等で使う SQLite パス（デフォルト: `data/monitoring.db`）

自動 `.env` ロードを無効化する場合：
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

環境変数が足りない場合は Settings が例外を投げます（ValueError）。

---

## セットアップ手順（ローカル開発向け）

1. Python（推奨 3.9+）を用意します。

2. 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要な依存パッケージをインストール（最低限）
   - duckdb
   - defusedxml
   - 例:
     pip install duckdb defusedxml

   （プロジェクトに requirements.txt があればそちらを使ってください）

4. プロジェクトルートに `.env` を作成して必要な環境変数を設定する
   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

5. （任意）パッケージを editable/install:
   pip install -e .

---

## 使い方（主要な API と実行例）

以下は Python REPL やスクリプト内で使う例です。

- DuckDB スキーマの初期化と接続取得
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリを自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# もしくはインメモリ
# conn = schema.init_schema(":memory:")
```

- 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

run_daily_etl は内部で J-Quants クライアントを使い、レート制限・リトライ・トークンリフレッシュを扱います。戻り値は ETLResult オブジェクトで、取得件数や品質問題、エラー概要を含みます。

- ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")  # 既存 DB に接続
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
# results: {source_name: 新規保存数}
```

- カレンダー更新ジョブ（夜間更新）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved", saved)
```

- 監査ログスキーマの初期化（audit）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```
または既存接続に追加:
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- J-Quants API の直接呼び出し（必要であれば）
```python
from kabusys.data import jquants_client as jq

# トークンは settings から自動取得されるため通常は省略可能
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# DuckDB に保存
saved = jq.save_daily_quotes(conn, quotes)
```

注意: API の呼び出しはレート制限・リトライ・401 リフレッシュロジックを内包しています。

---

## ディレクトリ構成（主要ファイル）
リポジトリの主要なモジュール構造は以下の通りです（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（自動 .env ロード）
  - data/
    - __init__.py
    - schema.py               — DuckDB スキーマ定義と init_schema / get_connection
    - jquants_client.py       — J-Quants API クライアント（取得/保存ユーティリティ）
    - pipeline.py             — ETL パイプライン（run_daily_etl など）
    - news_collector.py       — RSS ニュース収集と保存
    - quality.py              — データ品質チェック（欠損/重複/スパイク/日付整合）
    - calendar_management.py  — マーケットカレンダー管理（is_trading_day 等）
    - audit.py                — 監査ログテーブル初期化
    - pipeline.py
  - strategy/
    - __init__.py             — 戦略層（未実装の拡張ポイント）
  - execution/
    - __init__.py             — 発注/実行層（未実装の拡張ポイント）
  - monitoring/
    - __init__.py             — モニタリング関連（拡張ポイント）

---

## 開発上のヒント / 注意事項
- 環境変数が足りないと Settings のプロパティが ValueError を投げます。必須キーを .env に設定してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- NewsCollector は外部 RSS に対する SSRF や XML 攻撃対策（defusedxml, ホストチェック, リダイレクト検査, サイズ制限）を行っています。RSS の取得処理はネットワーク例外を投げる可能性があるため、呼び出し側でハンドリングしてください。
- DuckDB の接続は軽量ですが、DDL 実行時のトランザクション（特に audit.init_audit_schema の transactional=True）に注意してください。DuckDB のトランザクション性に関する制約により、既にトランザクション中の接続で BEGIN を呼ぶと不整合が発生することがあります。
- jquants_client のリクエストは内部でレート制御（120 req/min）を行います。大量取得やバッチ実行の設計では待ち時間に注意してください。
- run_daily_etl は品質チェックをデフォルトで行い、QualityIssue のリストを返します。品質問題は即停止せず集約して返す設計です。呼び出し側で処理方針を決めてください。

---

必要に応じて README に含める追加情報（CI の実行方法、テストの実行、デプロイ手順、`.env.example` の内容など）を指定してください。README を参照する利用者向けにサンプル .env.example を作成することをおすすめします。