# KabuSys

日本株自動売買プラットフォーム用のライブラリ（データ取得・ETL・監査・カレンダー管理・ニュース収集 等）

このリポジトリは、J-Quants や kabuステーション 等からデータを取得し、DuckDB に保存して戦略・実行層へ供給するための基盤モジュール群を提供します。設計は冪等性（ON CONFLICT）、レート制御、リトライ、SSRF 対策、データ品質チェックなどを重視しています。

バージョン: 0.1.0

---

## 主な機能

- J-Quants API クライアント
  - 株価（日足 OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レートリミット（120 req/min）制御、指数バックオフによるリトライ
  - 401 応答時の自動トークンリフレッシュ（1回）
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT を使用）

- ETL パイプライン
  - 差分更新（最終取得日に基づく再取得 + バックフィル）
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- ニュース収集
  - RSS フィードの収集・正規化・前処理
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等保存
  - SSRF 対策（スキーム検証・プライベートアドレス排除・リダイレクト検査）
  - defusedxml を使った安全な XML パース
  - 銘柄コード抽出（本文・見出しから 4 桁コード検出）

- マーケットカレンダー管理
  - JPX の祝日・半日・SQ を DB に差分更新
  - 営業日判定、前後営業日取得、期間の営業日一覧取得

- 監査（Audit）
  - シグナル → 発注 → 約定までを UUID で追跡する監査テーブル群の初期化
  - order_request_id を冪等キーとして二重発注防止

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のスキーマ定義と初期化ユーティリティ

---

## 動作環境・依存

- Python 3.10 以上（PEP 604 の型注記（|）を使用）
- 必要な Python パッケージ（一部）:
  - duckdb
  - defusedxml

プロジェクトルートに setup/pyproject がある想定でパッケージ化してください。開発・実行に必要なパッケージは適宜 requirements.txt / pyproject.toml に追加してください。

例（簡易インストール）:
pip install duckdb defusedxml

---

## 環境変数（必須/推奨）

このライブラリは .env を自動読み込みします（プロジェクトルートに .git または pyproject.toml がある場合）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（実行する機能により必要）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード
- SLACK_BOT_TOKEN       : Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
- LOG_LEVEL   : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH : DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）

簡単な .env.example:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順

1. Python 3.10+ をインストール
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - その他プロジェクト固有の依存を pyproject.toml / requirements.txt に応じて追加
4. プロジェクトルートに .env を作成（.env.example を参考に）
5. DB 初期化（後述の例を参照）

---

## 使い方（主な API と例）

以下は主要な利用例（Python スクリプト内での利用）です。

1) DuckDB スキーマを作成・接続する
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ DB 可

2) 日次 ETL を実行する（J-Quants から差分取得して保存・品質チェック）
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())  # ETL の実行結果サマリ

3) 個別 ETL ジョブ（株価のみ等）
from datetime import date
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date.today())

4) ニュース収集ジョブを実行する
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出で使用する有効コードセット（なければ None）
results = run_news_collection(conn, known_codes={"7203", "6758"})
# results は {source_name: 新規保存数} を返す

5) 監査スキーマを初期化（監査専用 DB または既存接続へ）
from kabusys.data.audit import init_audit_schema, init_audit_db
# 既存接続に追加する場合:
init_audit_schema(conn, transactional=True)
# 監査専用 DB の初期化:
audit_conn = init_audit_db("data/kabusys_audit.duckdb")

6) カレンダー関連ユーティリティ
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date
is_open = is_trading_day(conn, date(2026, 1, 1))
next_day = next_trading_day(conn, date.today())

----

注意点 / 設計の要約:
- J-Quants クライアントはモジュールレベルの id_token キャッシュと RateLimiter を持ちます。
- API リクエストは最大 3 回のリトライ（条件付き）を行い、401 の場合はトークンリフレッシュを1回試みます。
- DuckDB への保存は基本的に ON CONFLICT を使った冪等処理です。
- NewsCollector は SSRF / XML Bomb / 大きなレスポンス等に注意した堅牢な取得ロジックを実装しています。
- 品質チェックモジュールはエラー/警告を収集して呼び出し元が判断できるようにします（Fail-Fast ではない）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      -- 環境変数 / 設定管理（.env 自動読み込み）
- data/
  - __init__.py
  - jquants_client.py            -- J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py            -- RSS ニュース収集・保存
  - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
  - calendar_management.py       -- マーケットカレンダー管理
  - schema.py                    -- DuckDB スキーマ定義・初期化
  - audit.py                     -- 監査ログスキーマ初期化
  - quality.py                   -- データ品質チェック
- strategy/
  - __init__.py                  -- 戦略用パッケージ（拡張ポイント）
- execution/
  - __init__.py                  -- 発注 / 実行層（拡張ポイント）
- monitoring/
  - __init__.py                  -- 監視・メトリクス（拡張ポイント）

（上記は主要ファイルの一覧。将来的に strategy / execution / monitoring を拡張して戦略実装や発注コネクタを統合できます）

---

## 開発・運用メモ

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を探索）から行われます。テスト時に自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB ファイルのデフォルトは data/kabusys.duckdb です。運用では永続ボリュームへ配置してください。
- ETL は部分失敗しても他処理を継続する設計です。品質チェック結果（errors / quality_issues）を監査・アラートに活用してください。
- Slack や証券会社 API などと連携する場合はそれらのクライアント実装（例: slack_sdk 等）を追加してください。本パッケージはトークン取得のための設定のみ提供します。

---

## ライセンス / 貢献

この README はコードベースの概要を示すためのもので、実際のプロジェクトで配布する場合は LICENSE ファイルを追加してください。貢献する場合は、Issue / Pull Request を通じてお願いします。

---

必要であれば README にサンプルワークフロー（cron ジョブ、Dockerfile、CI 設定例など）も追加できます。追加希望があれば教えてください。