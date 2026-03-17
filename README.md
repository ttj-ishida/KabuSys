KabuSys — 日本株自動売買プラットフォーム
====================================

概要
----
KabuSys は日本株向けのデータ基盤と自動売買パイプラインのライブラリ群です。  
主に以下を提供します。

- J-Quants API からの市場データ取得（株価日足、財務情報、JPX カレンダー）
- RSS ニュースの収集と銘柄紐付け（ニュース収集器）
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）

主な機能一覧
--------------
- 環境変数管理（.env / .env.local 自動読み込み、必須キーチェック）
- J-Quants クライアント
  - レート制限（120 req/min）厳守
  - リトライ（指数バックオフ、401 時のトークン自動リフレッシュ）
  - ページネーション対応、取得時刻（fetched_at）を UTC で記録
  - DuckDB へ冪等的に保存（ON CONFLICT）
- ニュース収集（RSS）
  - URL 正規化・トラッキングパラメータ除去、SHA-256 ベースの記事 ID
  - SSRF 対策（スキーム検証、プライベートIP拒否、リダイレクト検査）
  - gzip/サイズ上限対策、defusedxml による XML 攻撃対策
  - DuckDB へ冪等保存（INSERT ... RETURNING）
  - 銘柄コード抽出と一括紐付け
- DuckDB スキーマ定義
  - Raw / Processed / Feature / Execution / Audit の各層テーブル定義
  - インデックス定義・初期化ユーティリティ（init_schema, init_audit_schema）
- ETL パイプライン
  - 差分取得、バックフィル（デフォルト 3 日）
  - カレンダー先読み（デフォルト 90 日）
  - 品質チェックの実行（fail-fast ではなく全問題収集）
- データ品質チェック
  - 欠損（OHLC）/ 重複 / スパイク（前日比）/ 日付不整合検査
  - QualityIssue 型で詳細とサンプル行を返す

セットアップ手順
----------------

前提
- Python 3.9+（コードは typing | zoneaware datetime を利用）
- pip
- 推奨ライブラリ（後述）をインストール

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. パッケージインストール
   - プロジェクトが PEP 517/pyproject を持つ場合:
     - pip install -e .
   - 直接必要な依存を個別にインストールする場合:
     - pip install duckdb defusedxml

   （標準ライブラリの urllib 等も使用します）

3. 環境変数設定
   - プロジェクトルートに .env（および .env.local）を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN=（J-Quants の refresh token）
     - KABU_API_PASSWORD=（kabuステーション API のパスワード）
     - SLACK_BOT_TOKEN=（Slack Bot トークン）
     - SLACK_CHANNEL_ID=（通知先チャネル ID）
   - 任意
     - KABUSYS_ENV=development|paper_trading|live（デフォルト development）
     - LOG_LEVEL=DEBUG|INFO|...（デフォルト INFO）
     - DUCKDB_PATH=data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH=data/monitoring.db

   例 .env（最小）
   - JQUANTS_REFRESH_TOKEN=your_refresh_token
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567

4. DuckDB スキーマ初期化
   - Python から初期化する例:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")

   - 監査ログ（audit）を別 DB で管理する場合:
     - from kabusys.data import audit
     - conn = audit.init_audit_db("data/audit.duckdb")
     - または既存 conn に audit.init_audit_schema(conn) を呼ぶ

使い方（主要な API 例）
---------------------

- J-Quants トークン取得
  - from kabusys.data.jquants_client import get_id_token
  - id_token = get_id_token()  # settings.jquants_refresh_token を使用

- 日次 ETL の実行（DuckDB 接続を渡す）
  - from datetime import date
    from kabusys.data import pipeline, schema
    conn = schema.init_schema("data/kabusys.duckdb")
    result = pipeline.run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

  run_daily_etl は以下を順に実行します:
  1. 市場カレンダー ETL（先読み）
  2. 株価日足 ETL（差分・バックフィル）
  3. 財務データ ETL（差分・バックフィル）
  4. 品質チェック（オプション）

- ニュース収集（RSS）
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    conn = schema.init_schema("data/kabusys.duckdb")
    known_codes = {"7203", "6758", ...}  # 事前に有効銘柄リストを準備
    results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
    print(results)

- データ品質チェック単体実行
  - from kabusys.data import quality, schema
    conn = schema.get_connection("data/kabusys.duckdb")
    issues = quality.run_all_checks(conn, target_date=date.today())
    for i in issues:
        print(i)

- DuckDB の接続取得（スキーマ初期化済みのファイルへ接続）
  - from kabusys.data.schema import get_connection
    conn = get_connection("data/kabusys.duckdb")

運用上の注意・設計ポイント
-------------------------
- J-Quants API のレート制限（120 req/min）を厳守するため内部で固定間隔スロットリングを実装しています。
- HTTP リトライは指数バックオフで最大 3 回（408/429/5xx）を対象に実施し、401 はトークン自動リフレッシュを行って1回リトライします。
- ニュース収集では SSRF、XML Bomb、gzip 解凍攻撃、巨大レスポンス等に対して複数の防御を実装しています。
- ETL は冪等性を意識しており、DuckDB への挿入は ON CONFLICT を利用しています。
- run_daily_etl は Fail-Fast ではなく、各ステップの問題を集めて ETLResult として返します。呼び出し側で重大度に応じた対応（停止・通知など）を行ってください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py      — RSS ニュース収集器（正規化・SSRF対策・保存）
  - schema.py              — DuckDB スキーマ定義・初期化
  - pipeline.py            — ETL パイプライン（差分取得・品質チェック）
  - quality.py             — データ品質チェックモジュール
  - audit.py               — 監査ログテーブル定義・初期化
- strategy/
  - __init__.py            — 戦略関連（拡張ポイント）
- execution/
  - __init__.py            — 発注実行やブローカー連携の拡張ポイント
- monitoring/
  - __init__.py            — 監視関連（拡張ポイント）

（実装済みの主要関数は README 本文に記載の通りです）

開発・拡張のヒント
------------------
- strategy/ と execution/ はエントリポイントを用意して戦略やブローカー実装を差し替えられるように設計されています。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして自動 .env ロードを無効化できます。
- news_collector._urlopen や jquants_client の HTTP レイヤーはモック可能に作られておりユニットテストがしやすい設計です。
- DuckDB は ":memory:" を指定してインメモリ DB でテストを実行できます。

ライセンス・注意
----------------
- この README に記載した環境変数や API 利用に関する機密情報は適切に管理してください。
- 実際の資金を使った運用（live 環境）を行う際は法令順守・注文ロジック/リスク管理を十分に検討してください。

お問い合わせ / 開発
-------------------
詳細実装や追加機能、運用に関する説明を追加したい場合は、具体的な要件（ブローカー連携先、戦略仕様、モニタリング要件等）を教えてください。README をもとに導入手順や運用手順をさらに整備します。