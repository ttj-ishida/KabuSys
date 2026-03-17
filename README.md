# KabuSys

日本株向けの自動売買プラットフォーム向けユーティリティ群です。  
データ取得・ETL・データ品質チェック・ニュース収集・マーケットカレンダー管理・監査ログなど、戦略や実行層の基盤となるモジュールを含みます。

主な設計方針：
- データの冪等性（DuckDBへの保存は ON CONFLICT で更新）を重視
- APIレート制限やリトライ、トークン自動リフレッシュを備えた外部APIクライアント
- SSRF／XML Bomb 等のセキュリティ対策を意識したニュース収集
- ETL は差分更新・バックフィル・品質チェックを組み合わせて運用を想定

---

## 機能一覧

- 設定管理
  - 環境変数 / .env ／ .env.local から設定の自動読み込み（無効化可）
  - 必須値未設定時は明示的な例外で通知

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）・四半期財務データ・JPXマーケットカレンダーを取得
  - レート制限（120 req/min）対応（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大3回）、401受信時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）をUTCで記録
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）

- ニュース収集（kabusys.data.news_collector）
  - RSSフィード取得、テキスト前処理（URL除去・空白正規化）
  - 記事IDは正規化URLのSHA-256（先頭32文字）で冪等性確保
  - defusedxml を使った安全なXMLパース、SSRF対策、受信上限バイト数制御
  - DuckDBへの一括挿入（トランザクション・チャンク挿入）・銘柄コード抽出・紐付け

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - スキーマ初期化（init_schema）と接続取得

- ETLパイプライン（kabusys.data.pipeline）
  - 日次ETL（カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）
  - 差分更新とバックフィル（デフォルト3日）対応
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- カレンダー管理（kabusys.data.calendar_management）
  - market_calendar の夜間更新ジョブ、営業日判定・前後営業日・期間内営業日取得等

- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定のトレース用テーブル群（UUIDによる階層的トレース）
  - 監査スキーマ初期化ユーティリティ

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合を検出
  - QualityIssue オブジェクトで結果を返す（severity: error | warning）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `X | None` などを使用）
- Git（リポジトリからセットアップする場合）

1. リポジトリをクローン（または package を入手）
   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. 仮想環境を作成して有効化（任意）
   - Linux/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール（例）
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - pip でインストール例:
     ```
     pip install duckdb defusedxml
     ```
   - 開発用に pyproject.toml / requirements.txt がある場合:
     ```
     pip install -e .
     # または
     pip install -r requirements.txt
     ```

4. 環境変数（.env）を設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を配置すると自動で読み込まれます。
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネルID（必須）
- （任意）KABUSYS_API_BASE_URL — kabu API のベースURL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

例 .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下は Python から直接呼ぶ簡易的な操作例です。実運用では適切なジョブスケジューラやログ出力を併用してください。

- DuckDB スキーマを初期化する
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を自動作成してテーブル作成
```

- 日次 ETL を実行する
```python
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.data.pipeline import run_daily_etl

conn = get_connection(settings.duckdb_path)  # 既存DBへ接続（init_schemaは一度だけでOK）
result = run_daily_etl(conn)
print(result.to_dict())
```
run_daily_etl は以下を順に実行します:
1. 市場カレンダーの差分取得（lookahead デフォルト: 90日）
2. 株価日足の差分取得（backfill デフォルト: 3日）
3. 財務データの差分取得（backfill デフォルト: 3日）
4. 品質チェック（デフォルト有効）

- ニュース収集ジョブを実行する
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄コード集合（任意）。与えると記事に対する銘柄紐付けを行う。
res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(res)  # {source_name: new_inserted_count}
```

- カレンダー夜間更新ジョブ（market_calendarの更新）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} records")
```

- 監査スキーマを追加する
```python
from kabusys.data.audit import init_audit_schema, init_audit_db
from kabusys.data.schema import get_connection

# 既存の conn に監査テーブルを追加
conn = get_connection("data/kabusys.duckdb")
init_audit_schema(conn)

# 監査専用DBとして初期化（別ファイル）
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- J-Quants の id_token を明示的に取得する
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token が使われる
```

ログレベルは環境変数 `LOG_LEVEL` で制御できます。

---

## 主要な API / 関数一覧（抜粋）

- kabusys.config
  - settings: 設定オブジェクト（プロパティ経由で環境変数にアクセス）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - 個別チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency

---

## ディレクトリ構成（主要ファイル）

リポジトリは src パッケージ形式になっています。代表的なファイルは以下の通りです。

- src/
  - kabusys/
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
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

各モジュールにドキュメンテーション文字列（docstring）があり、実装の設計意図や挙動が記載されています。詳細は該当ファイルを参照してください。

---

## 運用上の注意点

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml の親ディレクトリ）を基準に `.env` / `.env.local` を自動読み込みします。
  - 読み込みの優先順位：OS環境変数 > .env.local > .env
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で便利）。

- API レート制限とリトライ
  - J-Quants クライアントは 120 req/min を守るようスロットリングしています。大量取得時は時間がかかる点に注意してください。

- DuckDB スキーマの冪等性
  - DDL は CREATE IF NOT EXISTS を使用しているため、init_schema は何度呼んでも安全です。

- 品質チェックは「収集継続」を基本とする
  - 品質チェックでエラーが検出されても、ETLは可能な限り継続実行し、呼び出し元が結果に基づいて停止/アラート等を行う設計です。

---

READMEは以上です。必要があれば、README に含めるサンプル .env.example、より詳細な運用手順、cron/スケジューラ例、Dockerfile / systemd ユニット例、または strategy/execution 層の使い方ドキュメントを作成します。どれを追加しますか？