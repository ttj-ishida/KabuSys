KabuSys
=======

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。  
データ取得・ETL・スキーマ定義・データ品質チェック・ニュース収集・監査ログ等を提供し、戦略（strategy）・発注（execution）・監視（monitoring）層と連携できるよう設計されています。

主な特徴
--------
- J-Quants API 経由で株価（日足 OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 受信時はトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアスを防止
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層を含む）
  - 各保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING 等）を前提
- ETL パイプライン（差分取得、バックフィル、品質チェックのワンストップ実行）
- ニュース収集（RSS）モジュール
  - URL 正規化→SHA-256 による記事 ID 生成（冪等）
  - SSRF / XML Bomb / Gzip Bomb 等の脅威緩和
  - 銘柄コード抽出と news_symbols への紐付け
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- strategy, execution, monitoring パッケージ用の基盤（拡張点）

動作要件（推奨）
----------------
- Python 3.10+
- ライブラリ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリの urllib, logging, datetime などを使用）

インストールとセットアップ
------------------------

1. リポジトリをクローンして仮想環境を作成・有効化
   - 例（Unix/macOS）
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - 実運用では他にログ周りや Slack 連携等の依存がある場合があります（適宜追加）。

3. 環境変数の準備
   - プロジェクトルートに .env または .env.local を置くことで自動読込されます（デフォルト）。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。
   - 必要な環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
     - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
     - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
     - KABUSYS_ENV (任意, デフォルト: development) — 有効値: development / paper_trading / live
     - LOG_LEVEL (任意, デフォルト: INFO) — DEBUG / INFO / WARNING / ERROR / CRITICAL

   - 例（.env）
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - KABU_API_PASSWORD=xxxxx
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

使い方（簡易サンプル）
---------------------

以下は Python REPL やスクリプト内での基本的な利用例です。

- スキーマ初期化（DuckDB ファイルの作成とテーブル作成）
  - from kabusys.data.schema import init_schema
  - from kabusys.config import settings
  - conn = init_schema(settings.duckdb_path)

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を指定可能
  - print(result.to_dict())

- ニュース収集ジョブを実行する（RSS → raw_news 保存 → 銘柄紐付け）
  - from kabusys.data.news_collector import run_news_collection
  - # known_codes は抽出に使う有効銘柄コードの集合（None だと紐付けはスキップ）
  - results = run_news_collection(conn, sources=None, known_codes=known_codes_set)
  - print(results)  # {source_name: saved_count}

- カレンダー（夜間バッチ）更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)
  - print("saved:", saved)

- 監査ログ用スキーマ初期化（audit）
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

運用上のポイント
----------------
- jquants_client は内部でレート制御とリトライ/トークンリフレッシュを行います。API レートやエラーを考慮した設計です。
- DuckDB への保存関数は冪等性を考慮しており、同一キーでの再実行に耐えます（ON CONFLICT を利用）。
- news_collector は SSRF/XML/Gzip ボム対策や受信サイズ制限を備えています。外部 URL を扱う際のセキュリティに注意済みです。
- ETL は差分更新を行い、backfill_days により後出し修正を吸収します。品質チェックは fail-fast ではなく問題を収集して返す方針です。
- 環境（KABUSYS_ENV）に応じた実行モードを戦略・発注層で参照して切り替えてください（development / paper_trading / live）。

ディレクトリ構成
----------------

主要ファイル・ディレクトリ（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                # 環境変数ロード・設定管理（.env 自動ロード・検証）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      # RSS ニュース収集・保存・銘柄抽出
    - schema.py              # DuckDB スキーマ定義 / init_schema / get_connection
    - pipeline.py            # ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py # カレンダー管理・営業日判定
    - audit.py               # 監査ログスキーマ・初期化
    - quality.py             # データ品質チェック
  - strategy/                # 戦略モジュール（拡張ポイント）
    - __init__.py
  - execution/               # 発注 / ブローカー連携（拡張ポイント）
    - __init__.py
  - monitoring/              # 監視・メトリクス（拡張ポイント）
    - __init__.py

設計上の注記
------------
- Python 3.10 の型表記（| 型合併）や typing の利用を前提としています。
- jquants_client は urllib（標準）を使用しており、requests 依存はありませんが、必要に応じて置換可能です。
- DuckDB を永続化に利用しているため、DB ファイルのバックアップ・管理に注意してください。
- strategy / execution / monitoring はこのパッケージの拡張ポイントです。既存モジュールと連携する形で実装してください。

トラブルシューティング
---------------------
- .env が読み込まれない場合:
  - プロジェクトルートの特定は __file__ を基点に .git または pyproject.toml を探索します。パッケージ配布後や特殊構成の場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用するか、直接環境変数を設定してください。
- J-Quants の認証エラー:
  - JQUANTS_REFRESH_TOKEN が正しいか確認してください。get_id_token は 401 を受けた際に自動でリフレッシュを試みますが、リフレッシュ自体が失敗すると例外になります。
- DuckDB の権限・パス問題:
  - デフォルトの DUCKDB_PATH は data/kabusys.duckdb です。親ディレクトリは init_schema が自動作成しますが、書き込み権限を確認してください。

貢献
----
- strategy / execution / monitoring 部分の実装や、新しいデータソースの追加、テストの追加は歓迎します。Pull Request の際はユニットテストと簡潔な説明を添えてください。

ライセンス
---------
- 本リポジトリのライセンス情報はプロジェクトルートに置いてください（ここでは指定なし）。

お問い合わせ
------------
- 不具合報告や仕様の質問は Issue を立てるか、README に記載の連絡先にお問い合わせください。

以上。必要なら README に含めるサンプル .env.example や具体的な CLI スクリプト例、より詳細な運用手順（Cron / Airflow 連携例 等）を追加できます。どの内容を追加しましょうか？