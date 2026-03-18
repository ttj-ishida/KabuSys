# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）のリポジトリ内ドキュメントです。  
本READMEはコードベース（src/kabusys）を元に作成しています。

概要
- KabuSys は日本株のデータ収集（J-Quants 等）、ETL、データ品質チェック、ニュース収集、監査ログ（トレーサビリティ）などを行うライブラリ群です。
- データ保存には DuckDB を利用し、冪等性・トレーサビリティ・セキュリティ（SSRF対策等）を重視した設計になっています。
- 主にバックエンドバッチ処理（データパイプライン、夜間ジョブ、ETL）や戦略 / 発注基盤の基礎機能を提供します。

主な機能
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制限（120 req/min）制御、リトライ（指数バックオフ）、401→自動トークンリフレッシュ対応
  - 取得時の fetched_at 記録（Look-ahead バイアス回避）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（RSS）
  - RSS 取得 → 前処理（URL除去、空白正規化）→ raw_news 保存
  - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成 → 冪等性保証
  - defusedxml による XML 攻撃対策、SSRF（スキーム/プライベートIP）対策、受信サイズ制限
  - 銘柄コード抽出（4桁数字）と news_symbols への紐付け
- ETL / パイプライン
  - 差分更新ロジック（最終取得日からの差分・backfill 対応）
  - 市場カレンダーの先読み（lookahead）対応
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次 ETL の一括実行（run_daily_etl）
- スキーマ管理（DuckDB）
  - Raw / Processed / Feature / Execution 層のスキーマ定義と初期化（init_schema）
  - 監査用スキーマ（signal_events, order_requests, executions）と初期化ユーティリティ（init_audit_schema / init_audit_db）
- データ品質（quality）
  - 欠損データ、重複、スパイク（前日比）、将来日付・非営業日データ検出
  - QualityIssue オブジェクトで問題を集約

必要条件（推奨）
- Python 3.10+
- 依存パッケージ（代表例）
  - duckdb
  - defusedxml
- （標準ライブラリのみで動く部分も多いですが、上記は主要機能で必須）

セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があればそれを利用してください）

4. パッケージを editable インストール（任意）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルートの .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（コード上で _require() を用いているもの）
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      — kabuステーション等の API パスワード
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot token
     - SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID
   - 任意 / デフォルト値あり
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
   - .env のパース挙動は柔軟で、export KEY=val、クォート、コメント等に対応しています。

使い方（コード例）

- DuckDB スキーマの初期化（ファイル DB）
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  # 既に存在する場合はスキップされ、接続が返ります
  ```

- 監査ログ用 DB 初期化（独立 DB）
  ```python
  from kabusys.data import audit
  conn = audit.init_audit_db("data/audit.duckdb")
  ```

- 日次 ETL の実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- ニュース収集ジョブの実行
  ```python
  from kabusys.data.pipeline import run_news_collection  # 実態は data.news_collector.run_news_collection
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(results)  # {source_name: saved_count}
  ```

- J-Quants の ID トークン取得（テスト・手動）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
  ```

- 個別取得（株価・財務・カレンダー）例
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,12,31))
  financials = fetch_financial_statements(code="7203")
  calendar = fetch_market_calendar()
  ```

設計上の注意点
- API 呼び出しはレートリミット（120 req/min）に従い、内部でスロットリングとリトライを行います。
- すべてのデータ保存はできる限り冪等（ON CONFLICT）で行う設計です。
- RSS 取得は SSRF 対策（スキームチェック、プライベートIPブロック、リダイレクト検査）と読み込みサイズ制限を実装しています。
- データ品質チェックは Fail-Fast ではなく、検出された問題を集めて呼び出し元に返します（呼び出し元で処理判断してください）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（自動 .env ロード）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py
      - RSS 収集と raw_news / news_symbols 保存ロジック
    - pipeline.py
      - ETL（差分更新、run_daily_etl 等）
    - schema.py
      - DuckDB スキーマ定義・初期化（init_schema）
    - calendar_management.py
      - 営業日ロジック・calendar_update_job
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）定義・初期化
    - quality.py
      - データ品質チェック
  - strategy/
    - __init__.py (戦略モジュール用プレースホルダ)
  - execution/
    - __init__.py (発注・実行管理プレースホルダ)
  - monitoring/
    - __init__.py (モニタリング用プレースホルダ)

よくある運用フロー（例）
1. 初期セットアップ: schema.init_schema() で DB を準備
2. 毎夜バッチ:
   - calendar_update_job でカレンダー更新
   - run_daily_etl でデータ取得 → 保存 → 品質チェック
   - 必要に応じて Slack 通知（SLACK_BOT_TOKEN を利用）
3. ニュース収集: cron/スケジューラで news_collector.run_news_collection を定期実行
4. 発注/監査: strategy でシグナル生成 → audit.order_requests による冪等発注ログ → executions の記録

トラブルシューティング / 開発メモ
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は冪等です。既にテーブルがある場合はスキップされます。
- J-Quants の API エラー（401 等）は自動リフレッシュと再試行ロジックがありますが、refresh token が無効だと失敗します。環境変数を確認してください。
- RSS の XML パース失敗やレスポンス過大時はソース単位でスキップされ、他ソースは継続します。

ライセンス / 貢献
- 本ドキュメントはコードベースに基づく簡易 README です。実際のライセンス・貢献ガイドラインはリポジトリに含まれる LICENSE / CONTRIBUTING を参照してください（本コード断片にはそれらが含まれていません）。

問い合わせ
- 開発者や運用担当者向けの質問はリポジトリの Issue を使用してください。README に記載の連絡チャネルがある場合はそちらへ。

以上。必要であれば、README に載せるサンプル .env.example、requirements.txt や簡易起動スクリプトのサンプルなども作成します。どれを追加しますか？