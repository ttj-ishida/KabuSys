KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。  
データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、監査ログ/スキーマ定義までを含むモジュール群を提供します。  
設計方針としては「ルックアヘッドバイアス回避」「冪等性」「外部API呼び出しの堅牢化（リトライ／レート制御）」「DBトランザクションによる原子性」を重視しています。

主な機能
--------
- J-Quants API クライアント（認証・ページング・レート制御・リトライ）
  - 株価日足、財務データ、マーケットカレンダー等の取得・DuckDB 保存
- ETL パイプライン（日次差分取得・バックフィル・品質チェック）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 特徴量計算（momentum / volatility / value 等）と Z スコア正規化
- シグナル生成（複数コンポーネントスコアの統合、BUY/SELL 判定、Bear レジーム抑制）
- ニュース収集（RSS → 正規化 → raw_news 保存、銘柄抽出）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day）
- 監査ログ（signal → order → execution のトレーサビリティ）
- 汎用統計ユーティリティ（zscore_normalize 等）

セットアップ手順
----------------

1. リポジトリをクローン／プロジェクトを配置
   - パッケージは src/kabusys 以下に配置されています。

2. Python 環境（推奨: 3.10+）を用意し、必要パッケージをインストール
   - 最低依存（コード内から参照される主な外部パッケージ）:
     - duckdb
     - defusedxml
   - 例（pip）:
     - pip install duckdb defusedxml

3. 環境変数 / .env ファイルを準備
   - ルート（pyproject.toml や .git があるディレクトリ）に置いた .env / .env.local を自動で読み込みます（優先順位: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用等）。
   - 必要な環境変数（主要）
     - JQUANTS_REFRESH_TOKEN  — J-Quants 用リフレッシュトークン（必須）
     - KABU_API_PASSWORD      — kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID       — Slack チャンネル ID（必須）
     - DUCKDB_PATH            — DuckDB ファイルパス（既定: data/kabusys.duckdb）
     - SQLITE_PATH            — SQLite（監視等）パス（既定: data/monitoring.db）
     - KABUSYS_ENV            — 実行環境 (development|paper_trading|live)（既定: development）
     - LOG_LEVEL              — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（既定: INFO）
   - .env の例:
     - JQUANTS_REFRESH_TOKEN=xxxx...
     - KABU_API_PASSWORD=secret
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

4. DuckDB スキーマ初期化
   - Python REPL などで次のように実行します:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を指定するとインメモリ DB を使用できます（テスト用）。

使い方（主要 API 例）
--------------------

- 基本インポート
  - from kabusys.config import settings
  - from kabusys.data.schema import init_schema, get_connection
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.strategy import build_features, generate_signals
  - from kabusys.data.news_collector import run_news_collection

- DB 初期化
  - conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（市場カレンダー・株価・財務を差分取得）
  - from datetime import date
  - res = run_daily_etl(conn, target_date=date.today())
  - res は ETLResult オブジェクト（取得数・保存数・品質問題等を含む）

- 特徴量構築（features テーブルへ保存）
  - from datetime import date
  - n = build_features(conn, target_date=date.today())
  - n は upsert した銘柄数

- シグナル生成（signals テーブルへ保存）
  - count = generate_signals(conn, target_date=date.today(), threshold=0.6, weights=None)
  - threshold や weights を引数で上書き可能（weights は各コンポーネントの重み）

- ニュース収集ジョブ（RSS から raw_news を保存し、既知銘柄との紐付けも行う）
  - known_codes = {"7203", "6758", ...}  # 抽出対象の銘柄コードセット
  - results = run_news_collection(conn, sources=None, known_codes=known_codes)
  - results は {source_name: 新規保存数} の辞書

- schema の既存 DB へ接続
  - conn = get_connection("data/kabusys.duckdb")  # init_schema は初回のみ使う

運用／実行に関する注意点
-----------------------
- J-Quants API のレート制限（120 req/min）をモジュール内で制御しますが、複数プロセスから同一トークンで同時に呼ぶ場合は注意してください。
- トークン期限切れ時は自動的にリフレッシュを試みます（get_id_token にてリフレッシュトークンを使用）。
- ETL は差分更新とバックフィル（既定: 3 日）を行い、API 側の後出し修正を吸収する設計です。
- DuckDB への保存は基本的に冪等性（ON CONFLICT / DO UPDATE）を考慮しています。
- ログレベルや環境（development/paper_trading/live）は KABUSYS_ENV, LOG_LEVEL で制御します。
- テスト時に .env の自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主なファイル）
------------------------------
（src/kabusys 以下を抜粋）

- __init__.py
  - パッケージのバージョン・公開 API を定義

- config.py
  - .env / 環境変数の読み込み・Settings クラス（各種設定値の取得）

- data/
  - jquants_client.py        — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py        — RSS → raw_news の収集・前処理・保存
  - schema.py                — DuckDB スキーマ定義・init_schema/get_connection
  - pipeline.py              — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py   — 市場カレンダー管理（営業日判定等）
  - features.py              — zscore_normalize の再エクスポート
  - stats.py                 — zscore_normalize など統計ユーティリティ
  - audit.py                 — 監査ログ用 DDL（signal / order / execution のトレーサビリティ）
  - quality.py               — （品質チェックモジュール：pipeline から呼ばれる想定。省略ファイルがある場合は参照）

- research/
  - factor_research.py       — momentum/volatility/value 等のファクター計算
  - feature_exploration.py   — 将来リターン計算、IC（Spearman）・統計サマリー
  - __init__.py              — 研究用 API のエクスポート

- strategy/
  - feature_engineering.py   — raw ファクターを統合・正規化して features に書き込む
  - signal_generator.py      — features + ai_scores から final_score を算出、BUY/SELL を生成
  - __init__.py              — strategy API のエクスポート

- execution/
  - __init__.py              — 発注/約定に関する層（今後の拡張ポイント）

テスト・デバッグ
----------------
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます（ユニットテスト時に便利）。
- init_schema(":memory:") を用いればインメモリ DB で高速に単体テスト可能です。
- jquants_client._urlopen や news_collector._urlopen などはテストでモックしやすい設計になっています。

ライセンス / 貢献
-----------------
（このコードベースにライセンス文が別途あればここに記載してください。なければプロジェクトに合わせて追加してください。）

付記（設計上の留意点）
--------------------
- ルックアヘッドバイアスに対する配慮が随所に組み込まれており、各処理は target_date 時点の情報のみを使うよう設計されています。
- DB 操作はトランザクションで囲んで日付単位での置換（DELETE→INSERT）を行い、冪等性と原子性を確保しています。
- 外部ネットワークアクセス（RSS・API）は SSRF・XML Bomb・大容量応答対策を組み込んでいます（news_collector の実装参照）。

この README はコード中のドキュメント（docstring）を基に作成しています。実運用に入れる前に .env の安全な管理、バックアップ、監視アラート等の追加整備を推奨します。