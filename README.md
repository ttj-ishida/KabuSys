KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのライブラリ／フレームワークです。  
主に以下レイヤーを備えます。

- データ収集・ETL（J-Quants API、RSS ニュース）
- データベーススキーマ管理（DuckDB）
- 研究用ファクター計算・特徴量生成（research）
- 戦略のシグナル生成（strategy）
- バックテストフレームワーク（backtest）
- ニュース収集・銘柄紐付け（news_collector）
- 実行・発注レイヤ（execution）やモニタリング（monitoring）用の骨組み

設計上のポイント
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- DuckDB をコア DB として採用（in-memory も可能）
- 各保存処理は冪等（ON CONFLICT / upsert）を重視
- J-Quants API に対するレート制御・リトライ・自動トークンリフレッシュを実装

主な機能
--------
- データ取得・保存
  - J-Quants から日足・財務データ・マーケットカレンダー取得（kabusys.data.jquants_client）
  - RSS からニュース収集と raw_news / news_symbols への保存（kabusys.data.news_collector）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）を提供（kabusys.data.pipeline）
- スキーマ管理
  - DuckDB のスキーマ初期化・接続ヘルパ（kabusys.data.schema.init_schema / get_connection）
- 研究・特徴量
  - モメンタム／ボラティリティ／バリュー等のファクター計算（kabusys.research.factor_research）
  - クロスセクション Z スコア正規化等の統計ユーティリティ（kabusys.data.stats）
  - ファクター探索・IC 計算（kabusys.research.feature_exploration）
  - 特徴量構築（kabusys.strategy.feature_engineering.build_features）
- シグナル生成
  - features + ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成（kabusys.strategy.signal_generator.generate_signals）
  - Bear レジーム検知や売却（エグジット）ルールを実装
- バックテスト
  - 日次ループベースのバックテストエンジン（kabusys.backtest.engine.run_backtest）
  - ポートフォリオシミュレータ（スリッページ・手数料モデルを考慮）（kabusys.backtest.simulator）
  - バックテスト評価指標（CAGR、Sharpe、MaxDD、勝率など）（kabusys.backtest.metrics）
  - CLI エントリポイント（python -m kabusys.backtest.run）

セットアップ
----------
推奨: 仮想環境を作成して依存をインストールしてください。

1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクト配布に setuptools / pyproject を使っている場合は pip install -e . が使えます）

3. DuckDB スキーマを初期化
   - Python から:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()

環境変数
--------
kabusys は .env / .env.local（プロジェクトルート）および OS 環境変数を自動でロードします（無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。主な必須設定は以下。

必須（例）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client に使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（execution 層用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — 通知対象チャンネル ID

任意
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）デフォルト: INFO
- DUCKDB_PATH — デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（data/monitoring.db）

.sample .env（例）
----------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

使い方（主要ワークフロー）
------------------------

1) スキーマ初期化
- Python REPL / スクリプトで:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()

2) データ取得（ETL）
- 株価・財務データの差分 ETL（pipeline の関数を利用）
  from kabusys.data.pipeline import run_prices_etl
  result = run_prices_etl(conn, target_date=date.today())

- RSS ニュース収集
  from kabusys.data.news_collector import run_news_collection
  res = run_news_collection(conn, sources=None, known_codes=set_of_codes)

3) 特徴量構築
- features を構築（target_date を指定）
  from kabusys.strategy import build_features
  build_features(conn, target_date)

4) シグナル生成
- generate_signals で signals テーブルに BUY/SELL を書き込む
  from kabusys.strategy import generate_signals
  generate_signals(conn, target_date)

5) バックテスト
- CLI 実行例:
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

- ライブラリ経由:
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date, end_date)
  conn.close()

主要モジュール / ディレクトリ構成
------------------------------
以下は src/kabusys 配下の主要ファイルと説明（抜粋）です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings クラス（必須キー取得のヘルパ）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（レート制御・リトライ・保存関数）
    - news_collector.py       — RSS 取得・前処理・DB 保存（SSRF 対策・gzip 制限等）
    - pipeline.py             — ETL パイプライン（差分取得・バックフィル・品質チェック）
    - schema.py               — DuckDB スキーマ定義・init_schema / get_connection
    - stats.py                — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py      — momentum / volatility / value のファクター計算
    - feature_exploration.py  — forward returns / IC / factor summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py  — ファクター正規化・features テーブルへの UPSERT
    - signal_generator.py     — final_score 計算・BUY/SELL の生成と signals への保存
  - backtest/
    - __init__.py
    - engine.py               — run_backtest（in-memory コピーを用いた日次バックテスト）
    - simulator.py            — PortfolioSimulator（約定モデル・mark-to-market）
    - metrics.py              — バックテスト評価指標計算
    - run.py                  — CLI エントリポイント
    - clock.py                — SimulatedClock（将来的用途）
  - execution/                — 発注/実行レイヤ（空のパッケージ、将来実装）
  - monitoring/               — 監視・メトリクス（将来実装）

開発メモ / 注意点
-----------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）から行われます。テスト時に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のスキーマは init_schema() で冪等に作成されます。既存 DB に対してはスキーマ変更に注意してください（バックアップ推奨）。
- J-Quants API はレート制限（120 req/min）があります。jquants_client は固定間隔スロットリングとリトライを実装していますが、過度の同時実行は避けてください。
- news_collector は外部への HTTP リクエストを行います。SSRF・gzip bomb 等の防護処理を実装していますが、運用時は接続先とタイムアウト設定に注意してください。
- generate_signals / build_features は target_date ベースで動作します。ルックアヘッドを起こさないために target_date の扱いを厳密にしてください。

貢献・拡張
-----------
- execution や monitoring に追加入力することで、実際の発注やアラート連携が可能です（kabuステーション API / Slack）。
- AI スコア算出パイプラインを ai_scores テーブルに書き込めば signal_generator が組み込みます。
- 分単位シミュレーションや複雑なポジションサイジングは backtest の拡張ポイントです。

問い合わせ
----------
不具合報告や改善提案はリポジトリの Issue にお願いします。README に記載のない実装意図やアルゴリズム詳細（StrategyModel.md / DataPlatform.md に相当する設計文書）が必要な場合は、リポジトリ内ドキュメントを参照してください。

以上。