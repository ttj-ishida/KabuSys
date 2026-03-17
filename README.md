# KabuSys

日本株自動売買プラットフォームのライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）を中心に提供します。

--- 

## 概要

KabuSys は日本株の自動売買システムを支えるコアライブラリ群です。主に次の機能を提供します。

- J-Quants API を利用した株価（日足）・財務データ・JPX マーケットカレンダーの取得
- RSS（ニュース）収集と前処理、記事と銘柄コードの紐付け
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定・前後営業日検索等）
- 監査用スキーマ（signal → order_request → executions のトレース）
- 設定は環境変数 / .env ファイルで管理（自動ロード機能あり）

設計上、API レート制御・リトライ・冪等性（ON CONFLICT）・SSRF対策・XML解釈の安全化（defusedxml）等を考慮しています。

---

## 主な機能一覧

- data/jquants_client.py
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュ・自動更新）
  - save_* 関数で DuckDB へ冪等保存（ON CONFLICT）
  - レートリミット（120 req/min）とリトライ

- data/news_collector.py
  - RSS フィード取得（gzip 対応、SSRF/プライベートアドレス検査、受信サイズ制限）
  - URL 正規化・トラッキングパラメータ除去・記事ID は SHA-256（先頭32文字）
  - DuckDB への一括挿入（INSERT ... RETURNING、トランザクション）

- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path) で初期化（冪等）

- data/pipeline.py
  - run_daily_etl(...) : カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 部分的な ETL（run_prices_etl, run_financials_etl, run_calendar_etl）も提供

- data/calendar_management.py
  - 営業日判定 / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチでカレンダー差分更新）

- data/audit.py
  - 監査ログ用スキーマ（signal_events, order_requests, executions）
  - init_audit_db(db_path) で監査用 DB 初期化（UTC タイムゾーン固定）

- data/quality.py
  - 欠損/重複/スパイク/日付不整合のチェック（QualityIssue オブジェクトで返却）
  - run_all_checks(conn, ...) で一括実行

- config.py
  - 環境変数の自動読み込み（プロジェクトルートの .env / .env.local）
  - Settings クラス（必須トークンの取得とバリデーション）
  - 環境変数の必須項目をチェックし、未設定時は ValueError を発生させる

---

## セットアップ手順

前提: Python 3.10 以上（型注釈に | 演算子を使用しています）

1. リポジトリをクローン / コピー

2. 仮想環境を作成・有効化（任意だが推奨）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 必要パッケージをインストール
   - 最低限の依存:
     - duckdb
     - defusedxml
   - インストール例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt があればそれを使用してください）

4. 環境変数 / .env を設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（Settings で _require_ されるもの）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabuステーション API のパスワード
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID : Slack 送信先チャンネル ID

   任意/デフォルト:
   - KABUSYS_ENV : development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL : DEBUG / INFO / ... （デフォルト: INFO）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : SQLite パス（デフォルト: data/monitoring.db）

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単なコード例）

以下は代表的な操作例です。適宜スクリプトや cron / Airflow / Prefect 等に組み込んでください。

1. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイル作成・ディレクトリ自動生成
```

2. 日次 ETL 実行（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
# conn は上で作成した DuckDB 接続
result = run_daily_etl(conn)  # デフォルト: 今日を対象に実行
print(result.to_dict())
```

3. ニュース収集（RSS）を実行して記事・紐付けを保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄抽出で参照する有効銘柄コードの集合（例: {"7203","6758",...}）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)  # {source_name: 新規保存件数}
```

4. マーケットカレンダー更新ジョブ（夜間バッチ想定）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved calendar records:", saved)
```

5. 監査用 DB の初期化（監査ログ専用 DB にしたい場合）
```python
from kabusys.data.audit import init_audit_db
aud_conn = init_audit_db("data/kabusys_audit.duckdb")
```

6. 品質チェック（ETL 後に呼ぶ）
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

7. 直接 J-Quants データを取得する（テストやバッチで）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()               # settings から自動取得
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,3,31))
```

---

## 推奨運用例

- 日次 ETL を夜間（または営業日朝）にスケジュールして run_daily_etl を実行
- calendar_update_job を併せて定期実行し market_calendar を最新化
- 監査ログ（order_requests / executions）は別 DB に分離して管理すると運用上扱いやすい
- ニュース収集は頻度を分けて（例: 15分毎）実行し、銘柄抽出で known_codes を最新に保つ
- ログレベルや環境（paper_trading / live）は KABUSYS_ENV / LOG_LEVEL で切り替え

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要モジュール構成は次の通りです（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py  — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント・保存
    - news_collector.py  — RSS ニュース収集・保存・銘柄抽出
    - schema.py          — DuckDB スキーマ定義 / init_schema
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理
    - audit.py           — 監査ログ（signal / order_request / executions）
    - quality.py         — データ品質チェック
  - strategy/           — 戦略関連（空のパッケージ、戦略実装用）
  - execution/          — 発注実装（空のパッケージ、実ブローカー連携用）
  - monitoring/         — 監視 / メトリクス（空のパッケージ）

各モジュールは設計ドキュメント（コメント）に沿って実装されており、再利用しやすい関数単位でエクスポートされています。

---

## 開発上の注意点 / 実装上のポイント

- Python 3.10 以降を想定（型ヒントに | を使用）
- J-Quants API レート制限（120 req/min）を内部で守る実装があるため、ユーザ側で追加のレート制御は通常不要
- jquants_client の get_id_token は自動リフレッシュロジックを持つ（401 発生時に1回リフレッシュしてリトライ）
- ニュース収集は SSRF・XML Bomb・gzip 爆発対策（受信上限）を実施
- DuckDB への挿入は可能な限り冪等に作られている（ON CONFLICT 句）
- data.audit.init_audit_db は接続の TimeZone を UTC に固定する（TIMESTAMP は UTC 想定）
- .env の自動ロードはプロジェクトルート検出に依存（.git または pyproject.toml が基準）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能

---

## 追加依存／拡張

- Slack 通知や kabuステーション API 統合、戦略ロジック、実ブローカー接続は各自実装する想定（strategy/、execution/ ディレクトリ）
- 運用環境では監視（Prometheus / Alert）やジョブ管理（cron / Airflow）を組み合わせて運用してください

---

以上です。必要であれば、README に含めるサンプル .env.example、CI / テストの実行方法、あるいは具体的なデプロイ/運用手順（systemd / container 化例 など）を追記できます。どの情報を追加しますか？