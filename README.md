KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
主な目的は「データ収集（J‑Quants 等） → 特徴量計算 → シグナル生成 → バックテスト / 発注シミュレーション」を一貫して行うためのモジュール群を提供することです。

設計方針のポイント
- DuckDB を中心としたローカル DB にデータを保持し、ETL は冪等（ON CONFLICT）で実装。
- ルックアヘッドバイアスを避けるため「target_date 時点のデータのみ」を使って計算。
- API 呼び出しはレート制御・リトライ・トークンリフレッシュ等を備える（J‑Quants クライアント）。
- バックテストは本番 DB を汚染しないため、インメモリ接続へデータをコピーして実行。

主な機能一覧
- data
  - jquants_client: J‑Quants API クライアント（株価・財務・カレンダー取得、DuckDB 保存）
  - news_collector: RSS からニュース収集、前処理、銘柄抽出、DuckDB 保存
  - schema: DuckDB のスキーマ初期化 / 接続ユーティリティ（init_schema, get_connection）
  - pipeline: ETL の差分更新ロジック（差分取得・保存・品質チェック）
  - stats: Z スコア正規化などの統計ユーティリティ
- research
  - factor_research: モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy
  - feature_engineering.build_features: 生ファクターの統合・正規化・features テーブルへの保存
  - signal_generator.generate_signals: features + ai_scores を利用した BUY / SELL シグナル生成
- backtest
  - engine.run_backtest: 日次ループでのバックテスト実行（インメモリ DB コピー、ポートフォリオシミュレータ使用）
  - simulator.PortfolioSimulator / metrics: 擬似約定・資産評価・バックテスト指標計算
  - run: CLI からのバックテスト起動エントリポイント
- config
  - 環境変数の読み込み・管理（.env 自動読み込み、必須チェックを含む Settings クラス）

セットアップ手順
----------------
前提: Python 3.10+（typing の | 記法を使用）を想定します。

1. リポジトリをクローン／配置
   - 任意ディレクトリにソースを置きます。プロジェクトルートの判定は .git または pyproject.toml を基準とします。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows

3. 依存ライブラリのインストール（最低限）
   - pip install duckdb defusedxml
   - その他実行に必要なパッケージがあれば requirements.txt を用意している場合は pip install -r requirements.txt を実行してください。

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を作成して以下の変数を設定します（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - KABUSYS_ENV=development|paper_trading|live  # デフォルト development
     - LOG_LEVEL=INFO
     - DUCKDB_PATH=data/kabusys.duckdb  # 任意パス
   - 注意: config モジュールは起動時に自動で .env を読み込みます（ルートの検出に失敗する場合は読み込みをスキップ）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. データベース初期化
   - Python REPL / スクリプトで DuckDB スキーマを初期化します:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ":memory:" でも可
     conn.close()

使い方（代表例）
----------------

1) バックテスト（CLI）
- モジュールに同梱のランナーを使って実行できます。
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 \
    --slippage 0.001 \
    --commission 0.00055 \
    --max-position-pct 0.20 \
    --db data/kabusys.duckdb

- またはプログラムから呼び出す例:
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()

2) データベースの初期化（スクリプト）
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # 以降 conn を使って ETL / feature / signal などを実行
  conn.close()

3) ETL（J‑Quants から株価・財務・カレンダーを取得して保存）
  from kabusys.data.schema import init_schema
  from kabusys.data import jquants_client as jq
  conn = init_schema("data/kabusys.duckdb")
  id_token = jq.get_id_token()  # settings.jquants_refresh_token が使われる
  records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  jq.save_daily_quotes(conn, records)
  conn.close()

- pipeline モジュールには差分更新を自動化する関数が用意されています（例: run_prices_etl）。プロジェクト環境に合わせて呼び出してください。

4) ニュース収集
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
  conn.close()

5) 特徴量作成とシグナル生成
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features, generate_signals
  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024,1,31))        # features テーブルを作成
  m = generate_signals(conn, target_date=date(2024,1,31))     # signals テーブルを作成
  conn.close()

主要な設定（環境変数）
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH: デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（動作モード）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

注意点 / 運用メモ
- J‑Quants API はレート制限（120 req/min）があるため、jquants_client は内部でレート制御を行います。大規模取得時は待ち時間が発生します。
- DuckDB スキーマは init_schema() で一括作成します（冪等）。
- ETL は差分更新を基本としています。初回は古い日付からのバックフィルを行ってください。
- バックテストは本番 DB を直接変更しないよう、run_backtest はインメモリ接続へ必要データをコピーして実行します。
- ニュース収集では外部スクリプトや公開 RSS を取得するため、SSRF 対策やサイズ制限を実装しています（defusedxml 等を使用）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数/設定管理
- data/
  - __init__.py
  - jquants_client.py       — J‑Quants API クライアント（取得＋保存）
  - news_collector.py       — RSS 取得・前処理・DB 保存・銘柄抽出
  - pipeline.py             — ETL 差分更新ロジック
  - schema.py               — DuckDB スキーマ定義 / init_schema
  - stats.py                — 統計ユーティリティ（zscore_normalize 等）
- research/
  - __init__.py
  - factor_research.py      — モメンタム / バリュー / ボラティリティの算出
  - feature_exploration.py  — IC / 将来リターン / 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py  — ファクター正規化・features 作成
  - signal_generator.py     — final_score 計算・BUY/SELL 生成
- backtest/
  - __init__.py
  - engine.py               — run_backtest（ループ・シミュレーション）
  - simulator.py            — PortfolioSimulator（擬似約定・評価）
  - metrics.py              — バックテスト指標計算
  - run.py                  — CLI エントリポイント
  - clock.py
- execution/                 — 発注 / 実行周り（プレースホルダ）
- monitoring/                — 監視・メトリクス（プレースホルダ）

貢献 / 開発メモ
- 型アノテーションとドキュメント文字列（docstring）を豊富に含めています。新機能は unit test / integration test を追加してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト環境で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD をセットしてください。
- 外部 API を呼ぶコードのテストでは、ネットワーク呼び出しや urllib/requests 部分をモックすることを推奨します（jquants_client, news_collector など）。

ライセンス
----------
（リポジトリの LICENSE を参照してください。ここでは明記していません。）

補足
----
README に書かれていない細かな挙動やパラメータは各モジュールの docstring を参照してください（モジュールは自己完結したドキュメント文字列を持っています）。README で不明な点があれば、どの部分について詳しく知りたいか教えてください。