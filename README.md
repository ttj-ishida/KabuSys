# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。J-Quants や kabu ステーションと連携して市場データ・財務データ・ニュースを収集し、DuckDB に格納、ETL・品質チェック・監査（発注トレーサビリティ）を行うためのモジュール群を提供します。

---

## 概要

KabuSys は以下を目的とした内部向けライブラリです：

- J-Quants API から株価（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーを取得
- RSS フィードからニュースを収集して記事と銘柄紐付けを行う
- DuckDB スキーマの初期化・管理（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- カレンダー管理（営業日判定、次・前営業日算出）
- 監査用テーブル（信号→発注→約定のトレーサビリティ）
- 品質チェック（欠損、スパイク、重複、日付不整合など）

設計上のポイント：
- API レート制限・リトライ・トークン自動リフレッシュを実装（J-Quants）
- DuckDB への保存は冪等（ON CONFLICT）で上書き／重複排除
- ニュース収集で SSRF・XML Bomb・サイズ攻撃対策を実施
- ETL はバックフィル、品質チェックを備えエラー時もできる限り継続する

---

## 主な機能一覧

- data.jquants_client
  - 株価（fetch_daily_quotes）、財務（fetch_financial_statements）、カレンダー（fetch_market_calendar）取得
  - ID トークン取得 / キャッシュ、レートリミット、リトライロジック、DuckDB への保存関数（save_*）
- data.news_collector
  - RSS 取得（fetch_rss）、記事正規化、ID 生成、DuckDB への保存（save_raw_news）、銘柄抽出と紐付け
- data.schema
  - DuckDB スキーマ定義 / 初期化（init_schema）
- data.pipeline
  - 日次 ETL（run_daily_etl）、個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
- data.calendar_management
  - 営業日判定、next/prev_trading_day、calendar_update_job
- data.audit
  - 監査ログ（signal_events / order_requests / executions）初期化（init_audit_schema / init_audit_db）
- data.quality
  - 欠損・スパイク・重複・日付不整合チェック（run_all_checks）
- 設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート検出）、Settings クラスによる環境変数アクセス
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

その他: strategy、execution、monitoring モジュールの名前空間を準備（実装は別途）。

---

## 前提・依存

- Python 3.10 以上（型ヒントの `X | None` などを利用）
- パッケージ依存（最低限）:
  - duckdb
  - defusedxml
- ネットワークアクセス: J-Quants API / RSS ソース / kabu API（運用時）
- 推奨: 仮想環境（venv / virtualenv / conda）

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージ自体を editable インストールする場合
pip install -e .
```
（プロジェクトに requirements.txt / pyproject.toml があればそれを利用してください）

---

## 環境変数（主なキー）

kabusys.config.Settings で参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — SQLite パス（監視用）デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — 値: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env ファイルの自動読み込みを無効化

※ プロジェクトルートにある `.env` / `.env.local` が自動で読み込まれます（ただし、OS 環境変数が優先）。パース挙動はシェル風の export/quoted/comment に対応しています。

---

## セットアップ手順（簡易）

1. リポジトリを取得
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストール
   ```bash
   pip install -U pip
   pip install duckdb defusedxml
   # 開発インストール
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（.env.example があれば参照）
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマ初期化（例）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリも作成されます
   ```

6. 監査ログ用スキーマ初期化（必要な場合）
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主要ユースケースの例）

- 日次 ETL の実行（基本）
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # 引数で target_date, id_token などを指定可能
  print(result.to_dict())
  ```

- 個別 ETL（株価のみ差分取得）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  # conn は init_schema で取得済みを前提
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- JPX カレンダーの夜間更新ジョブ（バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # known_codes は銘柄コードのセット（例: {"7203","6758", ...}）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- J-Quants から直接取得して保存
  ```python
  from kabusys.data import jquants_client as jq
  # id_token は自動取得キャッシュを使うため通常は省略可能
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)
  ```

- 品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

---

## 設定・動作上の注意

- .env 自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）を行い、.env / .env.local を順に読み込みます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。
- J-Quants API のレート制限（120 req/min）およびリトライ方針（指数バックオフ、429 の Retry-After 対応、401 時のトークン自動リフレッシュ）を実装済みです。
- ニュース収集は外部 URL 取得を伴うため、SSRF 対策および受信サイズ制限が組み込まれています。
- DuckDB のスキーマは冪等（IF NOT EXISTS / ON CONFLICT）で定義されていますので、何度でも初期化できますが、監査スキーマの初期化をトランザクション内で行う場合は transactional=True を推奨します。
- KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれかで、運用モードに応じて挙動分岐（将来的な利用）を想定しています。

---

## ディレクトリ構成

ソースの主なファイル構成（抜粋）:

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
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

主要モジュールの役割:
- kabusys.config: 環境変数・設定読み込みロジック
- kabusys.data: データ取得・ETL・スキーマ・品質チェック・監査関連
- kabusys.strategy: 戦略定義（名前空間）
- kabusys.execution: 発注ロジック（名前空間）
- kabusys.monitoring: モニタリング用コード（名前空間）

---

## 開発・テスト時のヒント

- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うと .env の自動ロードを抑止できます。
- network / HTTP の振る舞いをテストする場合、jquants_client の内部の HTTP 呼び出しや news_collector._urlopen をモックすることで外部依存を切り替えられます。
- DuckDB の `:memory:` を使えばテスト時にファイルを作らずに動かせます（init_schema(":memory:")）。

---

## 今後の拡張案（参考）

- strategy / execution の具体的な実装（ポートフォリオ最適化・リスク管理・証券会社 API の adapter）
- Slack 通知・監視（monitoring モジュールの実装）
- CI での ETL 結果の自動アラート（品質チェック結果に基づくアクション）

---

README に記載されていない細かい API や引数の説明はコード内の docstring を参照してください。必要であれば、各モジュールごとの詳細ドキュメントや使用例を追加で作成します。