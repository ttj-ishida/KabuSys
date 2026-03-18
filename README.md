# KabuSys

日本株向けの自動売買基盤ライブラリです。データ収集（J-Quants 等）・ETL・品質チェック・特徴量計算・監査ログ・ニュース収集といった機能を提供し、戦略・発注レイヤと組み合わせて自動売買システムを構築するための基盤を担います。

バージョン: 0.1.0

---

## 機能概要

- データ収集
  - J-Quants API から株価（日次 OHLCV）、財務データ、JPX カレンダーをページネーション対応で取得（レート制御／リトライ／トークン自動リフレッシュ対応）
- ETL（差分更新）
  - DuckDB へ冪等（ON CONFLICT）で保存。差分取得・バックフィル・カレンダー先読みをサポート
- データ品質チェック
  - 欠損、重複、スパイク（前日比異常）、日付不整合（未来日付や非営業日のデータ）を検出
- ニュース収集
  - RSS フィードから記事取得、前処理、記事ID生成（URL正規化＋SHA-256）、DuckDB へ冪等保存、既知銘柄コード抽出
  - SSRF 対策・受信サイズ制限・gzip 解凍制御など安全性設計
- 研究（Research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Zスコア正規化ユーティリティ
- スキーマ／監査ログ
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - 監査用テーブル（signal / order_request / executions 等）を初期化するユーティリティ
- 設定管理
  - .env / .env.local、自動ロード（プロジェクトルート検出）と環境変数経由の設定取得

---

## 主要な設計方針（抜粋）

- 本番口座・発注 API へは研究・データ処理モジュールからアクセスしない（分離）
- 冪等性（ON CONFLICT）とトランザクションでデータ整合性を保つ
- Look-ahead bias 対策として fetched_at を記録
- セキュリティ対策（RSS の SSRF ブロック、defusedxml、受信サイズ制限）
- 外部依存は最小限（標準ライブラリ中心、DuckDB と defusedxml を利用）

---

## 必要環境 / 依存ライブラリ

- Python 3.9+（型表記や Pathlib などを前提）
- 必須パッケージ（例）
  - duckdb
  - defusedxml

プロジェクトのパッケージ管理ファイルがあればそれに従ってください。簡易インストール例:

pip install duckdb defusedxml

（プロジェクト配布に requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリを取得して作業ディレクトリへ移動

2. 依存パッケージをインストール

   pip install -r requirements.txt
   または
   pip install duckdb defusedxml

3. 環境変数（.env）を用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` / `.env.local` を自動読み込みします。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須の環境変数（ライブラリ起動時に参照されます）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabu ステーション API パスワード（発注・執行を使う場合）
   - SLACK_BOT_TOKEN       : Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID

   任意・デフォルト値あり:
   - KABUSYS_ENV           : development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL             : DEBUG/INFO/...（デフォルト: INFO）
   - KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視 DB など（デフォルト: data/monitoring.db）

   例 `.env`:

   JQUANTS_REFRESH_TOKEN=xxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password

4. DuckDB スキーマ初期化（最初の一回だけ）

   Python REPL やスクリプトで:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   監査ログ専用 DB を作る場合:

   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要なユースケース）

- 日次 ETL（株価・財務・カレンダー取得と品質チェック）

  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)
  print(result.to_dict())

- ニュース収集ジョブ（RSS から raw_news へ保存・銘柄紐付け）

  from kabusys.data.news_collector import run_news_collection

  # known_codes: 銘柄抽出に使う既知の銘柄コード集合
  res = run_news_collection(conn, known_codes={"7203","6758"})
  print(res)  # {source_name: saved_count, ...}

- J-Quants API からの個別取得（テストや調査用）

  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

  quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  fins = fetch_financial_statements()

- ファクター計算 / 研究用ユーティリティ

  from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic

  # DuckDB 接続 conn と target_date を渡して使用
  momentum = calc_momentum(conn, target_date)
  vol = calc_volatility(conn, target_date)
  value = calc_value(conn, target_date)

  forward = calc_forward_returns(conn, target_date)
  ic = calc_ic(factor_records=momentum, forward_records=forward, factor_col="mom_1m", return_col="fwd_1d")

- 特徴量の Z スコア正規化

  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(records, ["mom_1m", "atr_pct"])

---

## よく使う API / 関数（抜粋）

- data.schema.init_schema(db_path) : DuckDB スキーマを初期化して接続を返す
- data.jquants_client.fetch_daily_quotes(...) : J-Quants から日次株価を取得
- data.jquants_client.save_daily_quotes(conn, records) : raw_prices へ保存（冪等）
- data.pipeline.run_daily_etl(conn, ...) : 日次 ETL のエントリポイント（カレンダー→株価→財務→品質チェック）
- data.news_collector.run_news_collection(conn, sources=None, known_codes=None) : RSS 一括収集ジョブ
- research.calc_momentum / calc_volatility / calc_value : ファクター計算
- research.calc_forward_returns / calc_ic / factor_summary / rank : 研究ユーティリティ
- data.stats.zscore_normalize : クロスセクションの Z スコア正規化

---

## 環境変数一覧（要/任意）

必須（アプリ起動時に参照。未設定だと ValueError）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルト値あり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

自動 .env ロードの制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                    — 環境変数・設定管理（自動 .env ロード、必須取得ヘルパ）
- data/
  - __init__.py
  - jquants_client.py          — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py         — RSS 収集・前処理・保存・銘柄抽出
  - schema.py                 — DuckDB スキーマ定義・初期化関数（init_schema / get_connection）
  - stats.py                  — 共通統計ユーティリティ（zscore_normalize）
  - pipeline.py               — ETL パイプライン（run_daily_etl 等）
  - quality.py                — データ品質チェック
  - calendar_management.py    — JPX カレンダー管理 / 営業日ユーティリティ
  - audit.py                  — 監査ログ（signal/order_request/executions）の初期化ユーティリティ
  - features.py               — features 用公開インターフェース（zscore 再エクスポート）
  - etl.py                    — ETLResult 型の公開
- research/
  - __init__.py (再エクスポート)
  - feature_exploration.py    — 将来リターン計算、IC、factor_summary、rank
  - factor_research.py        — Momentum/Volatility/Value 等のファクター計算
- strategy/                    — 戦略層（骨組み。各戦略実装をここに配置）
- execution/                   — 発注・注文管理（発注連携層）
- monitoring/                  — 監視用モジュール（監視 DB 等）

各ファイルには docstring と詳細な設計コメントがあり、DB カラムや SQL の意図、エラー処理方針が記述されています。

---

## 運用上の注意

- J-Quants のレート制限（120 req/min）を尊重するよう実装されていますが、大量並列での呼び出しは避けてください。
- DuckDB はローカルファイルベースの DB です。複数プロセスでの同時書き込みや運用方法については DuckDB のドキュメントに従ってください。
- 監査ログ用テーブルは削除せず追記する前提です（トレーサビリティ確保）。
- 自動 .env ロードはプロジェクトルートを基準に行います。CI やテストでこれを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

## 貢献・拡張のヒント

- strategy/ 以下に戦略実装（シグナル生成 → signal_events 登録 → order_requests 登録 → 実行）を追加してください。
- execution 層で kabu API（kabu-station）との連携を実装すると発注・約定を自動化できます（KABU_API_PASSWORD, KABU_API_BASE_URL を使用）。
- 分析・研究用途には research モジュールの関数を組み合わせ、zscore_normalize で標準化してからポートフォリオ最適化等へ繋げてください。

---

README は以上です。必要があれば、セットアップスクリプトや具体的なサンプルワークフロー（CI での日次 ETL 実行スクリプト、systemd / cron の例など）を追加します。どの例が欲しいか教えてください。