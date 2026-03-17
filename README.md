# KabuSys

日本株自動売買プラットフォームのライブラリ群（データ収集・ETL・監査・ニュース収集など）。

このリポジトリは、J‑Quants API や RSS フィードからデータを収集して DuckDB に蓄積し、
品質チェック・カレンダ管理・監査ログなど自動売買システム運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 特徴（概要・機能一覧）

- J‑Quants API クライアント
  - 株価日足（OHLCV）・財務（四半期 BS/PL）・JPX マーケットカレンダー取得
  - API レート制御（120 req/min）、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look‑ahead Bias を防止

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のDDLを定義
  - 初期化関数（init_schema / init_audit_db）

- ETL パイプライン
  - 差分更新・バックフィル対応（デフォルト backfill_days=3）
  - 市場カレンダー先読み（デフォルト 90 日）
  - 品質チェック組込み（欠損・スパイク・重複・日付不整合）

- ニュース収集（RSS）
  - RSS フィード取得・前処理（URL除去・空白正規化）
  - 記事IDは URL 正規化 + SHA‑256（先頭32文字）で冪等性を保証
  - SSRF 対策、受信サイズ上限、gzip 対応
  - raw_news / news_symbols へ冪等保存（INSERT ... RETURNING）

- マーケットカレンダー管理
  - JPX カレンダー差分更新ジョブ
  - 営業日／SQ判定、前後営業日取得、期間内営業日リスト

- 監査（Audit）
  - signal_events / order_requests / executions 等の監査テーブルと索引
  - 発注→約定までのトレーサビリティ（UUIDベースの階層）

- データ品質チェック
  - 欠損データ・スパイク（前日比）・重複・日付不整合検出
  - QualityIssue オブジェクトで問題を集約

---

## 動作要件

- Python 3.10 以上（PEP 604 の型記法（|）などを使用）
- 必須ライブラリ（最低限）
  - duckdb
  - defusedxml
- （実行環境に応じ）ネットワーク接続（J‑Quants API、RSS）

インストール例（仮の requirements がない場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# このパッケージを開発モードで使う場合
pip install -e .
```

---

## 環境変数（設定）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動ロードされます。
自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN  (必須) — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD      (必須) — kabu API パスワード
- KABU_API_BASE_URL      — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       (必須) — Slack チャンネル ID
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            — 環境（development, paper_trading, live）デフォルト: development
- LOG_LEVEL              — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

設定アクセス例（コード内）:
```python
from kabusys.config import settings
settings.jquants_refresh_token
settings.duckdb_path
```

※ `.env.example` を参考に `.env` を作成してください（リポジトリに例ファイルがある想定）。

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.10+）
2. 仮想環境を作成して依存をインストール
   - duckdb, defusedxml など（上記参照）
3. 環境変数を設定（またはプロジェクトルートに `.env` を配置）
4. DuckDB スキーマ初期化
   - 例: data/kabusys.duckdb を作成してスキーマを作る
     ```bash
     python -c "from kabusys.data import schema; schema.init_schema('data/kabusys.duckdb')"
     ```
5. （監査用 DB を別で用意する場合）
   ```bash
   python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/kabusys_audit.duckdb')"
   ```

---

## 使い方（主要 API と実例）

以下はライブラリを直接 Python から呼び出す基本例です。

- DuckDB 接続取得（初回は init_schema を使う）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # 初回でディレクトリを作成しテーブルを作成
# 既存 DB に接続するだけなら:
# from kabusys.data.schema import get_connection
# conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL 実行（株価・財務・カレンダーの差分取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 市場カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)  # conn は DuckDB 接続
print("saved:", saved)
```

- ニュース収集（RSS）と保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄コードの集合（例: 全上場銘柄リスト）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
print(res)  # {source_name: 新規保存数}
```

- 個別 API の利用例
  - J‑Quants トークン取得:
    ```python
    from kabusys.data.jquants_client import get_id_token
    token = get_id_token()
    ```
  - 株価取得（生データ）
    ```python
    from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
    saved = save_daily_quotes(conn, records)
    ```

- 監査スキーマ初期化（既存接続へ追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=False)
```

---

## 注意事項 / 実運用上のポイント

- J‑Quants API のレート制限（120 req/min）やエラーコード（408, 429, 5xx）に対するリトライ実装が含まれます。ユーザ側での追加制御は不要ですが、バッチの並列化には注意してください。
- 自動環境変数ロードは .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から読み込みます。テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定してください。
- DuckDB のファイルは OS ファイルパーミッションやバックアップポリシーを考慮してください。大規模データ運用ではストレージ容量に注意。
- NewsCollector は外部 RSS を取得するため SSRF 対策や受信サイズ制限などを実装していますが、外部依存の運用リスクは排除できません。信頼できるソースのみを使うことを推奨します。
- コード内で ON CONFLICT / INSERT ... RETURNING を多用して冪等性を担保しています。外部から直接 DB を操作する場合は整合性を保てるようにしてください。

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイルとモジュール構成:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py      — J‑Quants API クライアント（取得・保存）
      - news_collector.py      — RSS ニュース収集と保存ロジック
      - schema.py              — DuckDB スキーマ定義・初期化
      - pipeline.py            — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py — マーケットカレンダー管理・ジョブ
      - audit.py               — 監査テーブル定義・初期化
      - quality.py             — データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（上記はコードベースの主要箇所を表します。strategy / execution / monitoring モジュールは将来的な戦略／発注／監視機能の土台です）

---

## 貢献 / 開発メモ

- 型ヒントとユニットを重視した設計になっています。ユニットテストを追加する際は KABUSYS_DISABLE_AUTO_ENV_LOAD を使い環境依存を切り離してください。
- DuckDB の操作は SQL を直接実行します。新しいクエリを追加する場合は SQL インジェクションを避けるためパラメータバインド（?）を使ってください。
- ニュース収集や外部 API の呼び出しはネットワークの不安定さに左右されるため、ログと再試行戦略を考慮した運用をしてください。

---

必要に応じて README にサンプル .env.example、CI 実行手順、より詳細な API 使用例（Scheduler 連携、Slack 通知の例）等を追加できます。どの情報がほしいか教えてください。