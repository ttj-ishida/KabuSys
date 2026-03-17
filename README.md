# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants / RSS 等から市場データ・ニュースを取得して DuckDB に格納し、ETL・品質検査・監査ログを通して戦略・実行層に渡すための基盤機能を提供します。

主な設計方針:
- API レート制御・リトライ・トークンリフレッシュ対応（J-Quants）
- DuckDB を用いた冪等な保存（ON CONFLICT を利用）
- ニュース取得での SSRF 対策・XML セキュリティ対策（defusedxml）
- データ品質チェックを用意し、問題検出を可視化
- 監査（audit）テーブルでシグナル→発注→約定のトレーサビリティを確保

---

## 主な機能一覧

- データ取得
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - RSS からのニュース収集（正規化・ID生成・トラッキングパラメータ削除）
- ETL パイプライン
  - 差分更新（最終取得日からの差分 + バックフィル）
  - カレンダー先読み（営業日調整）
  - データ保存（raw / processed / feature / execution 層のスキーマ）
- 品質チェック
  - 欠損、重複、スパイク（前日比急変）、日付不整合（未来日・非営業日）
- 監査ログ
  - signal_events / order_requests / executions を含む監査テーブル群
  - UUID ベースでシグナルから約定までトレース可能
- ニュースと銘柄紐付け
  - RSS から記事を収集し raw_news に保存、記事中の4桁銘柄コード抽出・news_symbols に保存

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10+（型注釈に union 型などを使用）
- DuckDB を利用するためローカルでライブラリが必要

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 例（必要なパッケージを個別にインストールする場合）:
     - pip install duckdb defusedxml
   - プロジェクトに pyproject.toml や requirements.txt があればそれを利用してください。
   - 開発インストール（プロジェクトがパッケージ化されている場合）:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` から自動読み込みされます（CWD に依存しない探索ロジック）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャネル ID（必須）
   - 任意／デフォルト:
     - KABUSYS_ENV — {development | paper_trading | live}（デフォルト: development）
     - LOG_LEVEL — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）
     - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）

   - 簡易 `.env` 例:
     - JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで実行:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - 監査ログ（audit）を別 DB で初期化する場合:
     - from kabusys.data.audit import init_audit_db
     - audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   - init_schema は親ディレクトリを自動作成します。

---

## 使い方（代表的な呼び出し例）

以下はライブラリを直接インポートして利用する例です。CLI は付属しません（必要に応じてラッパースクリプトを作成してください）。

1. 日次 ETL を実行する（J-Quants の id_token は内部的にリフレッシュされる）
   - Python スクリプト例:
     - from datetime import date
       from kabusys.data.schema import init_schema
       from kabusys.data.pipeline import run_daily_etl
       conn = init_schema("data/kabusys.duckdb")
       result = run_daily_etl(conn, target_date=date.today())
       print(result.to_dict())

   - run_daily_etl の主な引数:
     - target_date: ETL の基準日（省略時は今日）
     - id_token: 明示的に ID トークンを注入可能（通常は不要）
     - run_quality_checks: 品質チェックを実行するか（デフォルト True）
     - backfill_days: 後出し修正吸収のためのバックフィル日数（デフォルト 3）

2. J-Quants から特定期間の株価を取得して保存
   - from kabusys.data import jquants_client as jq
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,2,1))
     jq.save_daily_quotes(conn, records)

   - 注意点: 内部でレート制限（120 req/min）やリトライ・401 リフレッシュが行われます。

3. RSS ニュース収集ジョブ
   - from kabusys.data.news_collector import run_news_collection
     conn = init_schema("data/kabusys.duckdb")
     results = run_news_collection(conn, known_codes={"7203","6758"})
     print(results)  # {source_name: inserted_count, ...}

   - fetch_rss は defusedxml を使い XML Bomb 等に対策済みで、リダイレクト先のスキーム／プライベートIP検査を行います。

4. 品質チェックのみ実行
   - from kabusys.data.quality import run_all_checks
     conn = duckdb.connect("data/kabusys.duckdb")
     issues = run_all_checks(conn, target_date=date.today())
     for i in issues:
         print(i)

---

## 実装上のポイント（知っておくと便利）

- 環境変数自動ロード:
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索し `.env` / `.env.local` を自動で読み込みます。
  - テストや特殊用途では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能です。

- J-Quants クライアント:
  - リクエストは固定間隔スロットリングでレート制御。
  - 指数バックオフのリトライ（最大3回）。408/429/5xx をリトライ対象。
  - 401 受信時はリフレッシュトークンで id_token を自動更新して一度リトライ。
  - 取得時の fetched_at を UTC で記録し look-ahead bias 対策。

- ニュース収集:
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等保存。
  - トラッキングパラメータ（utm_* 等）を除去してからハッシュ化。
  - レスポンスサイズ上限・gzip 解凍後の上限検査あり。

- DuckDB スキーマ:
  - Raw / Processed / Feature / Execution（監査含む）を定義。
  - 多数のインデックスを作成し、よく使うクエリを高速化。
  - init_schema() は冪等で、既存テーブルは上書きせずスキップします。

---

## 主要なディレクトリ構成

(簡易ツリー)

- src/
  - kabusys/
    - __init__.py
    - config.py                 -- 環境変数 / 設定読み込み
    - data/
      - __init__.py
      - jquants_client.py       -- J-Quants API クライアント（取得／保存）
      - news_collector.py       -- RSS 収集・正規化・DB 保存
      - pipeline.py             -- ETL パイプライン（差分更新・品質チェック統合）
      - schema.py               -- DuckDB スキーマ定義・初期化
      - audit.py                -- 監査ログテーブル（signal/order/execution）
      - quality.py              -- データ品質チェック群
    - strategy/
      - __init__.py             -- 戦略層（拡張ポイント）
    - execution/
      - __init__.py             -- 発注実行層（拡張ポイント）
    - monitoring/
      - __init__.py             -- 監視・メトリクス（拡張ポイント）

---

## 拡張・運用メモ

- 実運用（live）では KABUSYS_ENV を `live` に設定し、ログレベルなど運用要件を調整してください。
- 実際の発注実装（kabu API 通信・注文ロジック）は execution 層を拡張して実装します。現状は基盤機能が中心です。
- ログは標準的な logging を使用しています。LOG_LEVEL 環境変数で制御できます。
- DuckDB ファイルのバックアップや VACUUM 相当の運用は別途検討してください（DuckDB はファイルベースの軽量 DB）。

---

README に書かれているコード呼び出し例はライブラリ内部 API を直接使うサンプルです。プロダクションでの実行はエラーハンドリング・リトライ設計・秘密情報管理（シークレットの安全な保管）を適切に行ってください。README にない追加の CLI やシステム統合が必要であれば、その要件に合わせてラッパースクリプトやデーモン化用の実装を追加してください。