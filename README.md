# KabuSys

日本株向けの自動売買データ基盤／ETLライブラリ。J-QuantsやRSSを用いたデータ収集、DuckDBベースのスキーマ管理、データ品質チェック、監査ログ（発注→約定のトレース）などを提供します。

主な用途：データ収集パイプラインの実装、戦略向け特徴量作成の前段処理、ニュース収集・銘柄紐付け、監査（order/exec）ログ管理。

---

## 主な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPXマーケットカレンダー取得
  - レート制限（120 req/min）とリトライ（指数バックオフ、401時のトークン自動更新）対応
  - 取得時刻（fetched_at）をUTCで記録、DuckDBへ冪等保存（ON CONFLICT）
- ETL パイプライン
  - 差分更新（最終取得日を元に未取得分のみ取得）
  - backfill 機能（直近N日を再取得してAPIの後出し修正を吸収）
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（RSS）
  - RSS取得・XMLパース（defusedxml使用）、テキスト前処理、URL正規化
  - 記事IDは正規化URLのSHA-256先頭32文字で冪等保証
  - SSRF対策（スキーム検証、プライベートIP拒否、リダイレクト検査）、レスポンスサイズ制限
  - DuckDBへバルク保存と銘柄（4桁コード）抽出・紐付け
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
  - インデックス、外部キー、監査ログテーブル、UTCタイムゾーン設定
- 監査ログ（audit）
  - signal_events, order_requests, executions の初期化・インデックス
  - 発注要求の冪等キー（order_request_id）や broker_execution_id を利用したトレーサビリティ

---

## 必要条件 / 依存ライブラリ

- Python 3.9+
- 必須パッケージ（主に）:
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはパッケージ化されていれば: pip install -e .
```

（プロジェクト配布時に requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン／取得する。
2. 仮想環境を作成して依存パッケージをインストールする（上記参照）。
3. 環境変数を設定する（.env をプロジェクトルートに置くと自動で読み込まれます）。
   - 自動読み込みは、プロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。
4. DuckDB スキーマを初期化する。

例: DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")  # data/ 配下を自動作成します
```

監査ログ（audit）テーブルを追加する場合:
```python
from kabusys.data.schema import get_connection
from kabusys.data.audit import init_audit_schema

conn = get_connection("data/kabusys.duckdb")
init_audit_schema(conn)
```

---

## 環境変数（設定項目）

このプロジェクトは環境変数／.env による設定を利用します。主なキー:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (オプション、デフォルト: http://localhost:18080/kabusapi)
- Slack（通知などに使用）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- システム設定
  - KABUSYS_ENV (development/paper_trading/live) — デフォルト development
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト INFO

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env ファイルの読み込み順:
- OS 環境変数 > .env.local > .env
- .env.local は .env を上書き可能（override=True）
- OS 環境変数は保護され上書きされません

---

## 使い方（主な操作例）

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL（株価・財務・カレンダー取得＋品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # デフォルトは今日を対象
  print(result.to_dict())
  ```

  - 引数に id_token を注入可能（テスト用）。
  - run_daily_etl は個別の ETL（calendar/prices/financials）を独立して実行し、品質チェックも実行します。

- カレンダー更新ジョブ（夜間バッチとして）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- RSS ニュース収集（raw_news 保存 + 銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は銘柄コード集合（例: {'7203', '6758', ...}）
  res = run_news_collection(conn, known_codes={'7203','6758'})
  print(res)  # ソースごとの新規保存数
  ```

- J-Quants からの取得（個別呼び出し）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 品質チェックの個別実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

---

## 実装上の注意点 / 設計ハイライト

- API 呼び出しはレート制限（120 req/min）に従うため内部でスロットリングされます。
- J-Quants API 呼び出しは 401 を検知すると自動でリフレッシュトークンから id_token を再取得して1回リトライします。
- データは DuckDB に対して冪等に保存されます（INSERT ... ON CONFLICT DO UPDATE / DO NOTHING）。
- RSS 取得は SSRF・XML 攻撃・Gzip Bomb などに対して複数の防御（スキーム検証、プライベートIP拒否、受信サイズ制限、defusedxml）を実装。
- ETL は Fail-Fast ではなく各処理を独立して実行し、検出された品質問題は集約して呼び出し元が判断できるようにしています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得／保存ロジック）
    - news_collector.py      — RSS ニュース収集／前処理／保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（差分取得 / 品質チェック）
    - calendar_management.py — マーケットカレンダー管理（営業日ロジック / バッチ）
    - audit.py               — 監査ログ（signal/order/execution）初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — （戦略モジュール置き場）
  - execution/
    - __init__.py            — （発注・ブローカー連携置き場）
  - monitoring/
    - __init__.py            — （監視・メトリクス置き場）

---

## テスト・開発メモ

- .env の自動ロードはプロジェクトルートを基準に行うため、テスト実行時に CWD に依存しない挙動になります。
- 自動ロードを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して下さい。
- ニュース収集の HTTP 呼び出しは、テストで `kabusys.data.news_collector._urlopen` をモックして差し替え可能です。
- jquants_client の id_token はモジュールレベルでキャッシュされます。テストで強制リフレッシュする場合は get_id_token() を直接使うか _get_cached_token(force_refresh=True) を用いて下さい（内部API）。

---

## ライセンス / 貢献

（ここにライセンスやコントリビュート手順を追記してください）

---

READMEは以上です。必要に応じてサンプルスクリプト、CI 設定、requirements ファイル、より詳細な運用手順（バッチスケジューリング、ログ収集、Slack 通知の呼び出し実装など）を追加できます。どの項目を拡張するか指定してください。