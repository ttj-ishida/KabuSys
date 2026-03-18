# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリセット（KabuSys）。  
データ取得・ETL、データ品質チェック、ニュース収集、DuckDBスキーマ定義、監査ログなどの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を通じて戦略実行基盤の土台を提供します。

- J-Quants API を用いた市場データ（株価、財務、JPXカレンダー）の取得と保存（DuckDB）
- RSS ベースのニュース収集と記事→銘柄紐付け
- DuckDB 上のレイヤ化されたデータスキーマ（Raw / Processed / Feature / Execution）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日検索など）
- 監査ログ（signal → order → execution のトレースを担保するテーブル群）
- 環境変数ベースの設定管理と自動 .env ロード

設計上の要点:
- API レート制限やリトライ、トークン自動リフレッシュ等の堅牢性
- データ取得時の fetched_at によるトレーサビリティ（Look-ahead bias 対策）
- DuckDB における冪等保存（ON CONFLICT）やトランザクション管理
- ニュース収集における SSRF / XML Bomb 対策、トラッキングパラメータ除去

---

## 主な機能一覧

- 設定管理: kabusys.config.Settings（.env の自動読み込み・必須環境変数検査）
- J-Quants クライアント: kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - トークン取得・自動リフレッシュ、固定間隔レートリミッタ、再試行（指数バックオフ）
- ニュース収集: kabusys.data.news_collector
  - RSS 取得・前処理・ID生成（URL正規化＋SHA-256）・DuckDB 保存・銘柄抽出
  - SSRF/圧縮サイズ制限/XML 安全パーサ使用（defusedxml）
- スキーマ管理: kabusys.data.schema
  - init_schema / get_connection（DuckDB スキーマ初期化）
  - Raw / Processed / Feature / Execution レイヤのDDL を定義
- ETL パイプライン: kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - 差分取得・backfill・品質チェックの統合
- カレンダー管理: kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチでJPXカレンダーを更新）
- 監査ログ: kabusys.data.audit
  - init_audit_schema / init_audit_db（signal / order_request / executions の監査テーブル）
- 品質チェック: kabusys.data.quality
  - 欠損・重複・スパイク・日付不整合の検出（QualityIssue を返す）

---

## 要件

- Python 3.10 以降（「X | None」などの構文を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging, hashlib, ipaddress, socket, re など

（パッケージ化時は requirements.txt / pyproject.toml を追加してください）

---

## セットアップ手順（ローカル）

1. リポジトリをクローン／配置
   - 例: git clone <repo> && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml

   ※ 実プロジェクトでは pyproject.toml / requirements.txt に依存関係を明記してください。

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます（kabusys.config が起動時に探して読み込みます）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用等）。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN (必須) — Slack ボットトークン
   - SLACK_CHANNEL_ID (必須) — Slack チャネルID
   - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (任意) — デフォルト: data/monitoring.db
   - KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
   - LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

   例 .env（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 初期化（DB スキーマ作成）

DuckDB スキーマを初期化するには kabusys.data.schema.init_schema を使用します。

Python 例:
```
from kabusys.config import settings
from kabusys.data import schema

conn = schema.init_schema(settings.duckdb_path)
# conn は duckdb の接続オブジェクト (duckdb.DuckDBPyConnection)
```

監査ログ（audit）用 DB を別途作る場合:
```
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要な例）

基本的な日次 ETL を実行する（市場カレンダー取得 → 株価/財務取得 → 品質チェック）:

```
from kabusys.config import settings
from kabusys.data import schema, pipeline

conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn)  # target_date を明示することも可能
print(result.to_dict())
```

特定期間の株価を差分 ETL で取得:
```
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")  # init_schema で既に作成済みの想定
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
```

ニュース収集ジョブを実行して DuckDB に保存:
```
from kabusys.data import news_collector, schema
conn = schema.get_connection("data/kabusys.duckdb")
# sources をカスタム指定可、known_codes は銘柄コード集合（抽出に使用）
results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)
```

JPX カレンダー更新（夜間バッチ）:
```
from kabusys.data import calendar_management, schema
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
```

J-Quants の id_token を明示的に取得する:
```
from kabusys.data import jquants_client
id_token = jquants_client.get_id_token()  # settings.jquants_refresh_token を使用
```

監査ログテーブルの初期化（既存 conn に追加）:
```
from kabusys.data import audit, schema
conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)
```

---

## 目次（ディレクトリ構成）

以下は本リポジトリの主要ファイルとディレクトリ構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - quality.py

各モジュールの役割:
- config.py: 環境変数・設定の読み込みと検証（.env 自動ロード、Settings クラス）
- data/jquants_client.py: J-Quants API 呼び出しと DuckDB への保存ユーティリティ
- data/news_collector.py: RSS 取得・前処理・DB保存・銘柄抽出
- data/schema.py: DuckDB スキーマ定義と初期化
- data/pipeline.py: ETL パイプライン（差分処理／品質チェック統合）
- data/calendar_management.py: 市場カレンダー更新と営業日関連ユーティリティ
- data/audit.py: 監査ログ（signal/order/execution）テーブルの定義と初期化
- data/quality.py: データ品質チェック群
- execution/, strategy/, monitoring/: 将来の注文実行・戦略・監視機能の拡張ポイント（現状はパッケージプレースホルダ）

---

## ログ・環境モード

- KABUSYS_ENV: development / paper_trading / live を指定（settings.env で検証）。  
  - is_live / is_paper / is_dev のプロパティを利用できます。
- LOG_LEVEL でログレベルを制御（デフォルト INFO）。

---

## 注意点 / 運用メモ

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。CI／テスト等で自動読み込みを抑止する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants の API レート制限（120 req/min）やエラー時のリトライ処理は内部で扱っていますが、長時間の大量リクエスト時には運用上の配慮が必要です。
- ニュース収集は外部 RSS をパースするため、XML 攻撃や SSRF を想定した安全対策（defusedxml、SSRF チェック、受信サイズ制限）を実装していますが、実運用時の追加検証を推奨します。
- DuckDB のファイルを共有ストレージで運用する場合は排他制御やバックアップポリシーを検討してください。

---

## 今後の拡張

- execution / strategy / monitoring パッケージに戦略の実装、注文送信（証券会社 API 統合）、リアルタイム監視・アラートを追加予定
- CI 用のテスト・依存関係定義（pyproject.toml / requirements.txt）の整備
- ドキュメント、サンプルワークフロー（Docker / k8s バッチジョブ例）

---

ご不明点や README に追記したい情報（例: 実行スクリプト、CI 設定、Docker イメージなど）があれば教えてください。README をご要望に合わせて拡張します。