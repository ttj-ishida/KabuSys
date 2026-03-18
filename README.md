# KabuSys

日本株自動売買プラットフォームの内部ライブラリコレクションです。  
データ取得（J-Quants）、DuckDBベースのデータスキーマ・ETL、ニュース収集、特徴量計算、研究用ユーティリティ、監査ログなどを含みます。

注意：このリポジトリはフルワークフローのライブラリ群を提供しますが、実際の発注機能やストラテジー本体は別モジュール（strategy / execution 等）で組み合わせて使用します。strategy / execution / monitoring パッケージは参照点として用意されていますが、現時点では実装がほとんど含まれていません。

---

## 主要な機能（概要）

- 環境設定
  - .env / .env.local から自動で環境変数を読み込む仕組み（自動ロードは無効化可能）。
  - 必須設定値を Settings クラス経由で取得。

- Data (DuckDB) 層
  - DuckDB 用スキーマ定義と初期化（data.schema.init_schema）
  - Raw / Processed / Feature / Execution / Audit の多層スキーマ
  - 監査ログ用スキーマ（order_requests, executions 等）

- データ取得 / 保存
  - J-Quants API クライアント（rate limit / リトライ / トークン自動リフレッシュを実装）
  - 株価（日足）、財務データ、市場カレンダーの取得と DuckDB への冪等保存

- ETL パイプライン
  - 差分取得・バックフィル対応の ETL（data.pipeline.run_daily_etl）
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- ニュース収集
  - RSS 取得・前処理・記事ID生成（トラッキングパラメータ除去）・DuckDB への保存
  - SSRF 対策、レスポンスサイズ上限など堅牢化

- 研究（Research）ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）算出、統計サマリー
  - Zスコア正規化ユーティリティ

- 汎用ユーティリティ
  - 統計関数、カレンダー管理、監査ログ初期化など

---

## 必須環境変数

以下はライブラリ内で _必須_ として参照される主な環境変数です。`.env` や OS 環境として設定してください。

- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション等の API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID（必須）

任意 / デフォルトあり:

- KABUSYS_ENV: development / paper_trading / live（default: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（default: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（default: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化する（1 を設定）

.env.example を作ってプロジェクトルートに配置してください（config.py のエラー文言を参照）。

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 本リポジトリに pyproject.toml / setup がある前提で:
     - python -m pip install -e . 
   - もしくは最低限必要なライブラリを手動でインストール:
     - python -m pip install duckdb defusedxml

   （プロジェクトに requirements.txt がない場合、上記を参考に必要パッケージを追加してください。）

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか OS 環境変数を設定します。例:
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C1234567890
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトで:
     from kabusys.data import schema
     from kabusys.config import settings
     conn = schema.init_schema(settings.duckdb_path)

---

## 使い方（主な操作例）

以下は簡単な利用例（Python スクリプト / REPL）。

- DuckDB 接続とスキーマ初期化
  from kabusys.data import schema
  from kabusys.config import settings
  conn = schema.init_schema(settings.duckdb_path)

- 日次 ETL 実行（株価 / 財務 / カレンダー取得 + 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- ニュース収集ジョブ（RSS から raw_news 保存・銘柄紐付け）
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に使う有効なコード集合（例: {'7203','6758',...}）
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)

- J-Quants から株価を直接取得する（fetch）
  from kabusys.data.jquants_client import fetch_daily_quotes
  quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  print(len(quotes))

- 研究用ファクター計算
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
  # conn は DuckDB 接続
  mom = calc_momentum(conn, target_date=date(2024,1,31))
  vol = calc_volatility(conn, target_date=date(2024,1,31))
  val = calc_value(conn, target_date=date(2024,1,31))
  fwd = calc_forward_returns(conn, target_date=date(2024,1,31))
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

- カレンダー管理ユーティリティ
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  is_trading_day(conn, date(2024,1,1))
  next_trading_day(conn, date(2024,1,1))
  get_trading_days(conn, start_date, end_date)

- 監査ログ初期化（監査専用 DB を用いる場合）
  from kabusys.data import audit
  audit_conn = audit.init_audit_db("data/audit.duckdb")

---

## 注意事項 / 運用上のポイント

- 環境（KABUSYS_ENV）:
  - 有効値: development / paper_trading / live
  - live モードでは発注や実運用に接続する際に追加の安全策を講じる設計を意図しています。常に設定を確認してください。

- J-Quants API:
  - rate limit（デフォルト 120 req/min）をモジュール内で制御しますが、実運用時は API 利用規約およびクォータを確認してください。
  - get_id_token() は自動リフレッシュを行います。refresh token は安全に管理してください。

- DuckDB スキーマ:
  - init_schema は冪等（既存テーブルを上書きしない）なので既存データに対して安全に実行できます。
  - audit.init_audit_schema は UTC タイムゾーン固定など監査要件に合わせた初期化を行います。

- ニュース収集:
  - RSS の content は前処理（URL 除去・空白正規化）されます。記事ID はトラッキングパラメータ等を除去した URL の SHA256 先頭 32文字で生成します。
  - SSRF 対策や response サイズ制限が実装されていますが、外部接続は十分に監視してください。

- 品質チェック:
  - ETL 後に run_all_checks を実行すると、欠損・重複・スパイク・日付不整合を検出できます。重大な品質問題があればログ/通知で対応してください。

---

## ディレクトリ構成（主要ファイル／モジュール）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存）
    - news_collector.py       — RSS ニュース収集・保存ロジック
    - schema.py               — DuckDB スキーマ定義・初期化
    - stats.py                — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - features.py             — 特徴量ユーティリティ公開（zscore 再エクスポート）
    - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
    - audit.py                — 監査ログ（signal / order_request / executions）初期化
    - etl.py                  — ETL 公開インターフェース（ETLResult 再エクスポート）
    - quality.py              — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py  — 将来リターン / IC / summary / rank
    - factor_research.py      — momentum / volatility / value ファクター計算
  - strategy/                 — 戦略関連パッケージ（未実装のプレースホルダ）
  - execution/                — 発注実行関連パッケージ（未実装のプレースホルダ）
  - monitoring/               — 監視関連パッケージ（プレースホルダ）

---

## 貢献 / 拡張案

- strategy / execution / monitoring の実装を追加し、発注フローを組み立てる。
- Slack 通知やエラーモニタリングを追加して ETL / 実行状況を可視化する。
- feature 層・AI スコアの実装、ポートフォリオ最適化ロジックの追加。
- テストカバレッジ（ユニット・統合テスト）の整備。

---

必要であれば .env.example のサンプルや具体的な使用スクリプト（cronジョブ / Airflow DAG 例）、CI 用のセットアップ手順なども作成できます。どの情報を優先して追加しますか？