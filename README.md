# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ「KabuSys」のリポジトリ用 README。

このドキュメントはコードベースの主要な機能、セットアップ方法、基本的な使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株のデータ収集・ETL・特徴量計算・研究（ファクター分析）・監査ログ管理を含む、自動売買システム向けのユーティリティ群です。主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダー取得（レート制限・リトライ・トークン自動更新に対応）
- DuckDB を用いたデータスキーマ定義と永続化（Raw / Processed / Feature / Execution レイヤ）
- RSS によるニュース収集とニュース→銘柄紐付け（SSRF 対策、トラッキングパラメータ除去等）
- ETL（差分取得・バックフィル・品質チェック）パイプライン
- 研究用ファクター計算（Momentum / Volatility / Value 等）と IC・統計サマリ計算
- 発注・監査ログ（audit）用のスキーマ整備（トレーサビリティを確保）

設計方針として「外部 API への不必要な呼び出しを避ける」「DuckDB 上の SQL と純粋な Python（標準ライブラリ）で実装」「ETL の冪等性確保」「セキュリティ（SSRF 等）対策」を重視しています。

---

## 主な機能一覧

- 設定管理
  - .env ファイルおよび環境変数の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）

- データ取得 / 保存（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - レート制限（120 req/min）、リトライ、401 時のトークン自動更新

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日を基に差分取得 + バックフィル）
  - 日次 ETL 実行 run_daily_etl（カレンダー → 株価 → 財務 → 品質チェック）
  - ETLResult による実行結果サマリ

- スキーマ管理（kabusys.data.schema）
  - DuckDB 用の全テーブル定義（Raw / Processed / Feature / Execution）
  - init_schema / get_connection ユーティリティ

- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（急騰・急落）、重複、日付不整合を検出
  - QualityIssue オブジェクトで問題を返す

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理・正規化（トラッキングパラメータ除去）
  - SSRF / gzip bomb / XML 攻撃対策（defusedxml 使用）
  - raw_news, news_symbols テーブルへの冪等保存

- 研究モジュール（kabusys.research）
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査スキーマ
  - init_audit_schema / init_audit_db

- 補助ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - マーケットカレンダー管理（営業日判定・next/prev_trading_day 等）
  - ニュース中の銘柄コード抽出

---

## セットアップ手順

前提
- Python 3.9+（ソースは型注釈に Python 3.10+ の書き方を含むため 3.10 を推奨）
- pip が使用可能
- ネットワーク接続（J-Quants API、RSS フィード）

1. リポジトリをクローン／配置

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 必要ライブラリ（例）:
     - duckdb
     - defusedxml
   - 例:
     pip install duckdb defusedxml

   （プロジェクトで pip の requirements.txt / pyproject.toml がある場合はそれに従ってください）

4. 環境変数 / .env の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から以下ファイルを自動読込します:
     - .env（優先度: OS 環境変数 > .env.local > .env）
     - .env.local（存在する場合 .env を上書きする）
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

   - 主な環境変数（README 用抜粋、必須は _require() により要求されます）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - KABU_API_BASE_URL (任意; デフォルト http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
     - SLACK_CHANNEL_ID (必須) — Slack チャネルID
     - DUCKDB_PATH (任意; デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (任意; デフォルト data/monitoring.db)
     - KABUSYS_ENV (任意; development/paper_trading/live。デフォルト development)
     - LOG_LEVEL (任意; DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト INFO)

   - .env の例（簡略）
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=yyyyy
     SLACK_BOT_TOKEN=xxxxx
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG

5. データベース初期化（DuckDB）
   - Python REPL やスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - 監査用 DB を別ファイルで初期化する場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

注: init_schema は親ディレクトリがなければ自動作成します。

---

## 基本的な使い方（例）

以下は最小限の実行例です。実行前に .env を適切に設定してください。

- 設定参照
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.is_dev, settings.log_level)

- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)

- 日次 ETL を実行する（市場カレンダー・株価・財務の差分取得 + 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可
  print(result.to_dict())

- J-Quants から生データを取得して保存（個別）
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)

- ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758"}  # 有効な銘柄コードセット
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)

- 研究用ファクター計算
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
  mom = calc_momentum(conn, target_date=date(2024,1,31))
  vol = calc_volatility(conn, target_date=date(2024,1,31))
  val = calc_value(conn, target_date=date(2024,1,31))
  # 正規化
  normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

- IC 計算（factor と将来リターンのランク相関）
  fwd = calc_forward_returns(conn, target_date=date(2024,1,31), horizons=[1,5])
  ic = calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)

- 監査ログ初期化（既存接続に追加）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)  # conn は init_schema で得た接続など

---

## 注意点・設計上の留意事項

- 環境変数の必須チェックに失敗すると ValueError が投げられます。JQUANTS_REFRESH_TOKEN など必須変数を設定してください。
- J-Quants クライアントはレート制限（120 req/min）やリトライを備えていますが、API の利用上限には注意してください。
- news_collector は外部からの XML をパースするため defusedxml を使用し、SSRF 防止やサイズ上限チェックを実装しています。
- ETL 関数は差分更新・バックフィル方式で動作し、save_* 系関数は ON CONFLICT を使った冪等保存を行います。
- DuckDB のバージョンによりサポートされる機能（外部キーの CASCADE や一部制約）に差異があるため、コメントにある注意点を確認してください。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することでパッケージインポート時の .env 自動読み込みを無効化できます（テスト時に便利）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイルと簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数ロードと Settings（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch_*, save_*）
    - news_collector.py
      - RSS フィード収集・前処理・DB 保存
    - schema.py
      - DuckDB スキーマ定義、init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - features.py
      - features の公開インターフェース（zscore_normalize を再エクスポート）
    - calendar_management.py
      - market_calendar の管理・営業日判定
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）の初期化
    - etl.py
      - ETL 公開インターフェース（ETLResult の再エクスポート）
    - quality.py
      - データ品質チェック
  - research/
    - __init__.py
    - factor_research.py
      - Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算・IC・統計サマリ
  - strategy/
    - __init__.py
    - （戦略実装用スペース）
  - execution/
    - __init__.py
    - （発注 API 等）
  - monitoring/
    - __init__.py
    - （監視・メトリクス用）

---

## トラブルシューティング（よくある問題）

- ValueError: 環境変数が設定されていません
  - settings の必須変数（JQUANTS_REFRESH_TOKEN 等）を .env または環境変数で設定してください。

- duckdb がインポートできない
  - duckdb パッケージをインストールしてください（pip install duckdb）。

- J-Quants API の HTTPError / Rate limit
  - レート制限や接続問題が発生することがあります。ログを確認し、API キーやネットワーク設定を確認してください。

- RSS 取得で parse エラーやサイズ超過
  - news_collector はサイズ・形式不正時に空リストを返す設計です。該当ソースの URL / レスポンスを確認してください。

---

必要に応じて各モジュールごとにより詳細なドキュメント（関数ごとの使用例、テスト・運用手順、CI / デプロイ手順）を追加できます。README の補足や特定機能の詳細化を希望する場合は、どの部分を深堀りしたいか教えてください。