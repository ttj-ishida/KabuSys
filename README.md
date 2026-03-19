KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株を対象とした自動売買システム向けのライブラリ群です。  
データ収集（J-Quants API）、ETL（DuckDB）、特徴量生成、戦略シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなど、自動売買のデータプラットフォームと戦略層の基盤機能を提供します。  
コードはモジュール化されており、Research（因子検証）→ Feature（特徴量）→ Strategy（シグナル）→ Execution（発注）という層構造を想定しています。

主な機能
--------
- J-Quants API クライアント（jquants_client）
  - 日次株価、財務データ、マーケットカレンダーの取得
  - レート制限・リトライ・自動トークンリフレッシュ
- ETL パイプライン（data.pipeline）
  - 差分取得、バックフィル、品質チェックとの統合（run_daily_etl 等）
- DuckDB スキーマ初期化（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
- 特徴量計算（research.factor_research / strategy.feature_engineering）
  - Momentum / Volatility / Value 等の因子計算、Z スコア正規化、ユニバースフィルタ
- シグナル生成（strategy.signal_generator）
  - 特徴量 + AI スコアを統合して final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ保存
- ニュース収集（data.news_collector）
  - RSS 収集、前処理、記事保存（重複排除）、銘柄抽出（4桁コード）
  - SSRF 防止、gzip/サイズ制限、XML 脆弱性対策（defusedxml）
- カレンダー管理（data.calendar_management）
  - 営業日判定、次/前営業日取得、カレンダーの夜間更新ジョブ
- 監査ログ（data.audit）
  - 信号→発注→約定までのトレース用テーブル群

要件
----
- Python >= 3.10（型注釈や | 型合成表記を使用）
- duckdb
- defusedxml
- （標準ライブラリで多く実装されていますが、実運用では上記パッケージをインストールしてください）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストールします（例）:
   - pip install duckdb defusedxml

3. 環境変数を設定します（下記「環境変数」参照）。プロジェクトルートに .env / .env.local を置くと自動で読み込みます（自動ロードはデフォルトで有効）。

4. DuckDB スキーマを初期化します（例）:
   - Python REPL やスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

環境変数（設定）
----------------
config.Settings が利用する主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション等の API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB など（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動 .env ロード:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）を探索して .env を自動読み込みします。
- 読み込み順: OS 環境変数 > .env.local > .env
- 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（クイックスタート）
------------------------

1) スキーマ初期化
- DuckDB ファイルを作成しテーブルを作成します。
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL 実行（株価・財務・カレンダー取得）
- run_daily_etl を使うと差分取得と品質チェックまで実施します。
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl, init_schema  # init_schema は schema モジュール
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

3) 特徴量ビルド
- DuckDB 接続と基準日を渡して features テーブルを作成します。
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")

4) シグナル生成
- features と ai_scores を読み、signals テーブルへ書き込む。
  from datetime import date
  from kabusys.strategy import generate_signals
  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date.today())
  print(f"signals generated: {total}")

5) ニュース収集ジョブ
- RSS ソースから記事を取得・保存し、既知銘柄コードとの紐付けも行えます。
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

6) 研究用ユーティリティ
- 因子計算や将来リターン、IC 計算などが research パッケージにあります。
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
  conn = init_schema("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date.today())
  fwd = calc_forward_returns(conn, date.today())
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")

注意点 / 設計上の振る舞い
-----------------------
- データベース操作は多くの箇所でトランザクション（BEGIN/COMMIT/ROLLBACK）を使用し、日付単位での置換（冪等）を想定しています。
- J-Quants API クライアントはモジュールレベルで ID トークンをキャッシュし、401 で自動リフレッシュします。
- NewsCollector は SSRF 対策、XML 脆弱性対策、レスポンスサイズ制限、トラッキングパラメータ除去などを行います。
- Strategy 層は発注（execution）層に依存しない設計です（signals テーブルへ書き込むのみ）。発注は別途 execution 層で行います。
- .env のパースは export 形式やクォート、インラインコメント等に対応しています。

ディレクトリ構成
----------------
以下は主要ファイル・モジュールの概略（パスは src/kabusys/...）:

- kabusys/__init__.py
- kabusys/config.py
  - 環境変数読み込み・Settings 定義
- kabusys/data/
  - jquants_client.py         — J-Quants API クライアント（fetch/save）
  - news_collector.py        — RSS 収集・記事保存・銘柄抽出
  - schema.py                — DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py              — ETL パイプライン（run_daily_etl など）
  - calendar_management.py   — カレンダー管理・夜間更新ジョブ
  - audit.py                 — 監査ログ / トレーサビリティ用テーブル
  - stats.py                 — zscore_normalize 等の統計ユーティリティ
  - features.py              — data.stats の再エクスポート
  - execution/               — 発注周り（現状空のパッケージが存在）
- kabusys/research/
  - factor_research.py       — Momentum/Volatility/Value の計算
  - feature_exploration.py   — 将来リターン、IC、統計サマリー等
- kabusys/strategy/
  - feature_engineering.py   — features の作成・正規化・保存
  - signal_generator.py      — final_score 計算・BUY/SELL シグナル生成
- kabusys/monitoring/         — 監視関連（存在する場合）

開発
----
- 型注釈とロギングを広く利用しています。静的チェック（mypy）や linter（flake8 等）を導入することで品質向上が期待できます。
- 自動 .env ロードはプロジェクトルート検出に .git または pyproject.toml を使用します。テスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

貢献
----
バグ報告や機能提案は Issue を作成してください。プルリクエストの前に Issue で相談いただけるとスムーズです。

付録: よく使う関数一覧（抜粋）
-----------------------------
- data.schema.init_schema(db_path) → DuckDB 接続（テーブル作成）
- data.pipeline.run_daily_etl(conn, target_date, ...) → ETLResult
- strategy.build_features(conn, target_date) → upsert 件数
- strategy.generate_signals(conn, target_date, threshold, weights) → シグナル総数
- data.jquants_client.fetch_daily_quotes(...) / save_daily_quotes(...)
- data.news_collector.run_news_collection(conn, sources, known_codes)

以上が README の要点です。必要なら README に含めるサンプル .env.example、CLI スクリプト例、シーケンス図や詳細な API 使用例（各関数引数の説明）を追加で作成できます。どの内容を優先して追記しますか？