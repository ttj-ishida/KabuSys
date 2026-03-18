# KabuSys

日本株向けの自動売買システム用ライブラリ（モジュール群）。  
データ取得・ETL・データ品質チェック・監査ログ・ニュース収集など、アルゴリズム取引基盤に必要な機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python パッケージです。主な機能は以下のとおりです。

- J-Quants API からのデータ取得（株価日足、財務データ、マーケットカレンダー）
- DuckDB を利用したデータスキーマ定義と永続化（Raw / Processed / Feature / Execution 層）
- ETL（差分取得・バックフィル・保存）パイプライン
- データ品質チェック（欠損、重複、スパイク、日付不整合など）
- ニュース（RSS）収集と記事保存、銘柄抽出
- マーケットカレンダー管理（営業日判定・前後営業日検索）
- 監査ログ（シグナル〜発注〜約定までのトレーサビリティ）
- 各種設計方針（レート制限順守、リトライ、冪等性、SSRF 対策など）を組み込み

設計上のポイント:
- API レート制限（J-Quants: 120 req/min）を守るための RateLimiter
- リトライ（指数バックオフ）、401 受信時のトークン自動リフレッシュ
- DuckDB への保存は ON CONFLICT を使った冪等性
- RSS パーシングに defusedxml を利用した安全な処理、SSRF や大容量レスポンス対策

---

## 機能一覧（モジュール単位）

- kabusys.config
  - 環境変数読み込み（プロジェクトルートの `.env` / `.env.local` 自動ロード）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN 等）
- kabusys.data
  - jquants_client.py: J-Quants API クライアント（fetch / save 関数）
  - schema.py: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution）
  - pipeline.py: 日次 ETL（差分取得・保存・品質チェック）
  - news_collector.py: RSS 取得・前処理・保存・銘柄抽出
  - calendar_management.py: カレンダー更新・営業日判定機能
  - quality.py: データ品質チェック群
  - audit.py: 監査ログ（signal / order_request / execution）スキーマ初期化
- kabusys.strategy
  - 戦略モジュール用の名前空間（将来的に戦略ロジックを配置）
- kabusys.execution
  - 発注／実行管理用の名前空間（接続やラッパーを配置）
- kabusys.monitoring
  - 監視・アラート関連（名前空間）

---

## 必要条件

- Python 3.10 以上（型ヒントの union 演算子 `|` を使用）
- 主要依存ライブラリ（実行に必要な最低限）
  - duckdb
  - defusedxml
  - （標準ライブラリに依存する多数のモジュール: urllib, logging, datetime 等）
- J-Quants API のリフレッシュトークン（JQUANTS_REFRESH_TOKEN）
- （kabuステーション連携や Slack 連携を使う場合）各種認証情報

※パッケージ化・配布時には requirements.txt / setup.cfg 等で依存を明記してください。

---

## 環境変数 / 設定

自動読み込み
- パッケージは、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` と `.env.local` を自動で読み込みます。
- 優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主な環境変数（settings で参照されるもの）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABUS_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視 DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境名: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

設定取得例（コード）
```
from kabusys.config import settings

token = settings.jquants_refresh_token
db_path = settings.duckdb_path
is_live = settings.is_live
```

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml
   - （開発用）pip install -e .
4. `.env` をプロジェクトルートに作成（.env.example を参考にする）
   - 必須変数を設定: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     ```
5. DuckDB スキーマ初期化（次の「使い方」を参照）

---

## 使い方（主要ワークフロー）

以下は代表的な利用例（Python スクリプト内での呼び出し）です。

1) DuckDB スキーマの初期化
```
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# これで必要なテーブルとインデックスが作成されます
```

2) 日次 ETL 実行（市場カレンダー取得 → 株価/財務データ差分取得 → 品質チェック）
```
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブの実行（RSS 収集 → raw_news 保存 → 銘柄紐付け）
```
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に保持している有効銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

4) 監査ログスキーマの初期化（audit テーブル群）
```
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

5) J-Quants API を直接呼んでページネーション付きにデータを取得する例
```
from kabusys.data.jquants_client import fetch_daily_quotes
quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,2,1))
```

重要な設計挙動:
- jquants_client はレート制限とリトライ処理を組み込んでいます。ID トークンが期限切れで 401 が返ると自動でリフレッシュして一度だけ再試行します。
- news_collector は SSRF 対策・受信サイズ制限・defusedxml を使った安全な XML パース・トラッキングパラメータ除去等の保護を行います。
- データ保存関数は基本的に ON CONFLICT (UPSERT) を使って冪等に動作します。

---

## 実運用上の注意

- K-Quants / 証券会社 API のキーやパスワードは安全に管理し、リポジトリにコミットしないでください。
- 本パッケージは本番発注ロジック（実際の注文送信）を含む場合、十分なテストとガード（ポジション制限、最大損失、ドライランなど）を実装してください。
- DuckDB はシングルファイル DB ですが、複数プロセスでの同時書き込みや運用スキームに注意してください。
- ETL のスケジュール（cron / Airflow 等）やログ集約、監視を別途用意してください。

---

## ディレクトリ構成

大まかなソースツリー（主要ファイル）
```
src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      schema.py
      pipeline.py
      calendar_management.py
      audit.py
      quality.py
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py
```

主要ファイルの概要
- config.py: 環境変数の読み込みと Settings クラス
- data/jquants_client.py: J-Quants API クライアント（fetch_*, save_*）
- data/news_collector.py: RSS 取得・記事前処理・DB 保存・銘柄抽出
- data/schema.py: DuckDB テーブル定義・初期化（init_schema, get_connection）
- data/pipeline.py: ETL パイプライン（run_daily_etl 他）
- data/calendar_management.py: 市場カレンダー関連のユーティリティとバッチジョブ
- data/audit.py: 監査ログスキーマ（signal_events, order_requests, executions）
- data/quality.py: データ品質チェック群

---

## 開発 / テスト

- 自動環境変数読み込みをテストから無効化するには、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ネットワーク依存部分（jquants_client や news_collector._urlopen 等）はユニットテストでモック差し替えしやすいように設計されています（モジュールレベル関数を差し替え）。

---

以上がこのコードベースの README（概要・セットアップ・使い方・構成）です。README を具体的にプロジェクト配布用に整備する際は、requirements.txt／setup.cfg／LICENSE／CONTRIBUTING ガイド等を追加すると良いでしょう。必要であれば README.md の英訳や具体的な env.example ファイルの雛形も作成します。どれが必要か教えてください。