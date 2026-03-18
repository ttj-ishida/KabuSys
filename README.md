# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants API や RSS フィードからデータを取得し、DuckDB に保存・品質チェックを行う ETL、マーケットカレンダー管理、ニュース収集、監査ログ用スキーマなどを提供します。

主な設計方針：
- データの冪等性（ON CONFLICT / RETURNING 等）を重視
- API レート制限・リトライ・トークンリフレッシュに対応
- SSRF / XML Bomb 等のセキュリティ対策を実装
- 品質チェック（欠損・重複・スパイク・日付不整合）を提供
- 監査ログで戦略→シグナル→発注→約定までトレース可能

バージョン: 0.1.0

---

## 主な機能一覧

- 環境設定管理
  - .env ファイルの自動読み込み（プロジェクトルート検出、オーバーライド制御）
  - 必須環境変数のバリデーション（KABUSYS_ENV / LOG_LEVEL 等）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、財務データ、マーケットカレンダーの取得
  - レートリミット制御、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ（save_* 関数）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日からバックフィル）→ 保存 → 品質チェック
  - 日次ETL 実行エントリポイント run_daily_etl
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、記事ID生成（URL 正規化 + SHA-256）
  - SSRF 対策、受信サイズ上限、defusedxml による XML 保護
  - DuckDB への冪等保存（raw_news / news_symbols）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、期間内営業日の取得
  - 夜間バッチでカレンダー差分更新
- スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - init_schema / init_audit_db による初期化
- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク、重複、日付不整合の検出
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等、トレーサビリティ用スキーマ

---

## 動作要件

- Python 3.10 以上（型注釈の演算子 `|` を使用）
- 主要依存ライブラリ（代表例）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib 等を使用

必要に応じてプロジェクトの requirements.txt を用意してください。

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトをチェックアウト

2. 仮想環境を作成・有効化（推奨）
   - venv / pipenv / poetry 等を利用

3. 依存パッケージをインストール
   例（pip）:
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数を設定（.env をプロジェクトルートに配置することで自動読み込み）
   - 自動読み込みはデフォルトで有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. DuckDB スキーマ初期化（初回のみ）
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # ディレクトリが自動作成されます
     ```

   - 監査ログ専用 DB 初期化:
     ```python
     from kabusys.data import audit
     conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 環境変数（主要）

必須（実行する機能に応じて必須のものが異なります）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（使用する場合）
- SLACK_CHANNEL_ID: Slack 通知先チャネル ID（使用する場合）

任意 / デフォルトあり:
- KABU_API_BASE_URL: kabuapi の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: {development, paper_trading, live}（デフォルト: development）
- LOG_LEVEL: {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）

例: .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

注意:
- パッケージインポート時に自動で .env/.env.local がプロジェクトルートから読み込まれます（OS 環境変数が優先）。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主な例）

以下はライブラリを利用する際の簡単なコード例です。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）
```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema 済みの場合
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 単体で株価差分 ETL 実行
```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- ニュース収集ジョブを実行（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- J-Quants ID トークンを明示取得
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data import calendar_management
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved {saved} records")
```

---

## 注意点 / 実装に関するメモ

- J-Quants API は 120 req/min のレート制限を想定しています。jquants_client 内で固定間隔スロットリングを実装しています。
- HTTP 401 を受信した場合は自動でトークンをリフレッシュして 1 回だけ再試行します（無限ループ防止）。
- news_collector は RSS XML のパースに defusedxml を使い、SSRF の可能性を軽減するためリダイレクト先のスキーム/ホスト検査を行います。
- DuckDB への保存は可能な限り冪等に設計されています（ON CONFLICT DO UPDATE / DO NOTHING / INSERT ... RETURNING）。
- init_audit_db は UTC タイムゾーンでの監査テーブル初期化を行います（SET TimeZone='UTC'）。

---

## ディレクトリ構成

リポジトリ中の主要ファイル / モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - execution/                (発注・ブローカー連携用モジュール用フォルダ)
  - monitoring/               (監視・アラート用モジュール用フォルダ)
  - strategy/                 (戦略実装用フォルダ)
  - data/
    - __init__.py
    - jquants_client.py       (J-Quants API クライアント、保存ユーティリティ)
    - news_collector.py       (RSS ニュース収集・保存)
    - schema.py               (DuckDB スキーマ定義・初期化)
    - pipeline.py             (ETL パイプライン、run_daily_etl 等)
    - calendar_management.py  (マーケットカレンダー管理)
    - audit.py                (監査ログスキーマ初期化)
    - quality.py              (データ品質チェック)
- その他:
  - .env.example (プロジェクトルートに置く想定の例ファイル、手動作成)
  - data/ (デフォルトで DuckDB ファイル等が作成されるディレクトリ)

---

## 貢献 / 開発メモ

- 自動環境読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。パッケージ配布後も動作するよう CWD に依存しない実装です。
- テストや一時的な環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- 型アノテーションや明確なエラーメッセージを重視しています。拡張（ブローカー連携、戦略追加、モニタリング）を歓迎します。

---

必要であれば README に CI / テスト実行方法、requirements.txt の一覧、.env.example のテンプレートを追加で作成します。どの情報を補足したいか教えてください。