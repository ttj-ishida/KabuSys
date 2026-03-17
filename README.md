# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。データ収集・ETL、データ品質チェック、ニュース収集、監査ログスキーマなどを提供します。J-Quants / kabuステーション / Slack 等と連携して、戦略・発注ロジックのためのデータ基盤を構築することを目的としています。

## 概要
KabuSys は次のレイヤーを中心に実装されたコンポーネント群です。

- データ取得（J-Quants API からの株価・財務・市場カレンダー取得）
- ETL パイプライン（差分更新、バックフィル、先読みカレンダー）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS → 正規化 → DuckDB 保存、銘柄抽出）
- DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
- 監査ログ（シグナル→発注→約定のトレース用スキーマ）

設計上の要点:
- API レート制限とリトライ（J-Quants クライアント）
- ID トークンの自動リフレッシュ（401 時）
- DuckDB への冪等保存（ON CONFLICT / RETURNING を活用）
- SSRF・XML Bom 等セキュリティ対策（news_collector）
- トランザクション単位での DB 操作、エラー時のロールバック
- 環境変数 / .env の自動読み込み（パッケージルートを探索）

## 主な機能一覧
- jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（refresh トークンから idToken を取得）
  - RateLimiter、指数バックオフ、401 リフレッシュ対応
- data.pipeline
  - 差分更新の ETL 実装（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 日次 ETL の統合エントリポイント run_daily_etl（品質チェック可）
- data.schema
  - DuckDB 用スキーマ初期化（init_schema / get_connection）
  - Raw / Processed / Feature / Execution 用のテーブルとインデックス定義
- data.audit
  - 監査ログ用テーブル初期化（init_audit_schema / init_audit_db）
  - シグナル・発注要求・約定のトレーサビリティを意識した DDL
- data.news_collector
  - RSS フィード取得、XML パース（defusedxml 使用）、URL 正規化、記事ID生成
  - save_raw_news / save_news_symbols（DuckDB への冪等保存）
  - SSRF 対策、受信サイズ上限、gzip 対応、トラッキングパラメータ除去
- data.quality
  - 欠損、重複、スパイク、日付整合性チェック（run_all_checks）

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションや union 型を利用）
- duckdb, defusedxml 等の依存パッケージ

1. リポジトリをクローン
   git clone <repo-url>

2. 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）
   例: pip install -e .

4. 環境変数 / .env を準備
   プロジェクトルートに .env または .env.local を置くと自動読み込みされます（パッケージ起動時）。
   自動読み込みを無効にしたい場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必須の環境変数（Settings クラス参照）:
   - JQUANTS_REFRESH_TOKEN  （J-Quants のリフレッシュトークン）
   - KABU_API_PASSWORD      （kabuステーション API 用パスワード）
   - SLACK_BOT_TOKEN        （Slack Bot Token）
   - SLACK_CHANNEL_ID       （Slack チャンネル ID）
   推奨 / 任意:
   - KABU_API_BASE_URL （デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH       （デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH       （デフォルト: data/monitoring.db）
   - KABUSYS_ENV       （development / paper_trading / live、デフォルト development）
   - LOG_LEVEL         （DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

   簡易 .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化
   Python REPL やスクリプトから DuckDB を初期化します。

   例:
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

   監査ログのみ別 DB にするとき:
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

## 使い方（代表例）

- DuckDB スキーマの初期化
  ```
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行して J-Quants から差分取得・保存・品質チェック
  ```
  from kabusys.data import pipeline
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

  run_daily_etl は次のふるまいをします:
  - 市場カレンダーの先読み取得（デフォルト 90 日）
  - 株価データの差分取得（最終取得日 - backfill_days から）
  - 財務データの差分取得
  - 品質チェック（run_quality_checks=True の場合）
  ETLResult オブジェクトで取得数・保存数・品質問題・エラーを確認できます。

- ニュース収集ジョブ
  ```
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄コードセット（抽出に使用）
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)
  ```

- J-Quants の個別 API 呼び出し（テストや細かい制御用）
  ```
  from kabusys.data import jquants_client as jq
  idt = jq.get_id_token()
  records = jq.fetch_daily_quotes(id_token=idt, date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- 品質チェック単独実行
  ```
  from kabusys.data import quality
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- 監査テーブル初期化（既存の conn に追加）
  ```
  from kabusys.data import audit
  audit.init_audit_schema(conn)
  ```

## 環境変数自動読み込みについて
- パッケージはパッケージファイルの位置からプロジェクトルートを探索し、`.env` と `.env.local` を自動で読み込みます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- テストや特殊用途で自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## セキュリティ・運用上の注意
- J-Quants リフレッシュトークン等は安全に管理してください（リポジトリにコミットしない）。
- news_collector は SSRF、XML Bomb、gzip バンプ等への対策を設けていますが、外部 URL の取り扱いには注意してください。
- 実運用（live）では KABUSYS_ENV を `live` に設定し、発注ロジックやログレベル等の適切な運用フローを確立してください。

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py                     : 環境設定・.env 自動読み込み・Settings クラス
- data/
  - __init__.py
  - jquants_client.py           : J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py          : RSS ニュース収集 / 前処理 / DuckDB 保存
  - schema.py                  : DuckDB スキーマ定義・初期化
  - pipeline.py                : ETL パイプライン（差分取得・統合日次ETL）
  - audit.py                   : 監査ログテーブル（シグナル→発注→約定）
  - quality.py                 : データ品質チェック
- strategy/
  - __init__.py                : 戦略周りのプレースホルダ（戦略ロジックを配置）
- execution/
  - __init__.py                : 発注 / 実行周りのプレースホルダ
- monitoring/
  - __init__.py                : 監視・稼働監視周りのプレースホルダ

（README に記載した API 名や機能は上記の各モジュールの docstring / 関数定義に基づきます。）

## 開発・テスト
- 単体テストや統合テストでは、環境変数自動読み込みを無効にして（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）、テスト用の一時 DB（":memory:" 等）やモックを使用してください。
- news_collector._urlopen や jquants_client のネットワーク呼び出しはテストでモック／スタブ化しやすいように設計されています。

---

ご不明点や README に追加してほしい具体的な例（cron 連携、Dockerfile、CI ワークフロー、requirements.txt の整備など）があればお知らせください。必要に応じてサンプル .env.example や運用ガイドを追記します。