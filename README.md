KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けのデータプラットフォーム、リサーチ、戦略生成、バックテストを含む自動売買システムのコアライブラリです。本リポジトリは以下を主に提供します。

- J-Quants API を用いたマーケットデータ／財務データ取得クライアント
- RSS ニュース収集と記事→銘柄紐付け機能
- DuckDB スキーマ定義・初期化
- ファクター計算（Momentum / Volatility / Value 等）と Z スコア正規化
- 特徴量作成（features テーブルへの保存）
- シグナル生成（final_score に基づく BUY/SELL 判定）
- バックテストエンジン（シミュレータ、約定モデル、メトリクス）
- ETL パイプラインや品質チェックの下請け実装

主要機能一覧
--------------
- data/jquants_client.py
  - J-Quants API から日足・財務・マーケットカレンダーを取得。レート制限・リトライ・トークン自動更新を実装。
  - DuckDB へ冪等保存（ON CONFLICT を利用）。
- data/news_collector.py
  - RSS フィード収集、記事正規化、重複排除、raw_news 保存、記事→銘柄紐付け。
  - SSRF 対策、受信サイズ制限、XML パース安全化（defusedxml）。
- data/schema.py
  - DuckDB の全テーブル定義（Raw / Processed / Feature / Execution 層）とインデックスを作成する init_schema()。
- data/pipeline.py
  - 差分取得・バックフィル・保存・品質チェックを組み合わせた ETL ジョブ（prices_etl 等）。
- data/stats.py
  - クロスセクション Z スコア正規化ユーティリティ。
- research/*
  - ファクター計算（calc_momentum, calc_volatility, calc_value）と特徴量探索（forward returns, IC, summary）。
- strategy/feature_engineering.py
  - 研究で得た raw factor を正規化・結合し features テーブルへ UPSERT。ユニバースフィルタ（最低株価・最低売買代金）や ±3 でのクリップを行う。
- strategy/signal_generator.py
  - features と ai_scores を統合し final_score を計算。BUY/SELL シグナルを signals テーブルへ冪等に書き込む。Bear レジーム抑制、売り条件（ストップロス等）を実装。
- backtest/
  - engine.py: バックテスト全体ループ。インメモリ DuckDB に必要データをコピーして実行。
  - simulator.py: 約定モデル（スリッページ・手数料）とポートフォリオ状態管理。
  - metrics.py: CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio 等を計算。
  - run.py: CLI からのバックテスト起動エントリポイント。

セットアップ手順
----------------
前提: Python 3.9+（ソースは型ヒントに union types 等を使用）を想定しています。

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージ（例）
   - duckdb
   - defusedxml
   - （標準ライブラリ以外の依存のみ明示）
   インストール例:
   - pip install duckdb defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意してください。

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（Settings クラス参照）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（execution 層利用時）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - 任意/デフォルト:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
   - 例 .env（テンプレート）：
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. DuckDB スキーマ初期化
   - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   - あるいは Python REPL 内で:
     from kabusys.data.schema import init_schema
     conn = init_schema('data/kabusys.duckdb')
     conn.close()

使い方（例）
-------------
- J-Quants から日足を取得して保存（簡易例）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema

  conn = init_schema('data/kabusys.duckdb')
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  conn.close()
  ```

- RSS ニュース収集ジョブの実行例
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema('data/kabusys.duckdb')
  known_codes = {'7203', '6758', '9984'}  # 例: 有効銘柄コード集合
  results = run_news_collection(conn, known_codes=known_codes)
  conn.close()
  ```

- 特徴量作成（build_features）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect('data/kabusys.duckdb')
  n = build_features(conn, target_date=date(2024,2,14))
  conn.close()
  ```

- シグナル生成（generate_signals）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect('data/kabusys.duckdb')
  total = generate_signals(conn, target_date=date(2024,2,14))
  conn.close()
  ```

- バックテスト（CLI）
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```
  オプション: --slippage, --commission, --max-position-pct

- バックテストをプログラムから呼ぶ例
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema('data/kabusys.duckdb')
  res = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  print(res.metrics)
  conn.close()
  ```

注意点 / 設計上の留意事項
------------------------
- 自動環境変数ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml を検出）を探索して .env / .env.local を読み込みます。テスト時などに無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Look-ahead バイアス防止:
  - research/strategy モジュールは target_date 時点の情報のみを使うように設計されています。データ取得関数は fetched_at を記録し、いつ情報が得られたかを追跡できるようにしています。
- DuckDB への保存は基本的に冪等（ON CONFLICT / DO UPDATE / DO NOTHING）を前提。
- news_collector は外部 RSS の扱いに注意（SSRF 対策、サイズ上限などを実装）。

ディレクトリ構成
-----------------
（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + 保存ロジック
    - news_collector.py             — RSS 収集・前処理・保存・紐付け
    - schema.py                     — DuckDB スキーマ定義・初期化
    - stats.py                      — Z スコア等の統計ユーティリティ
    - pipeline.py                   — ETL 差分処理の高レベルロジック
  - research/
    - __init__.py
    - factor_research.py            — momentum / volatility / value 計算
    - feature_exploration.py        — forward returns, IC, summary
  - strategy/
    - __init__.py
    - feature_engineering.py        — features テーブル作成
    - signal_generator.py           — signals テーブル作成（BUY/SELL）
  - backtest/
    - __init__.py
    - engine.py                     — バックテストループ/データコピー
    - simulator.py                  — 約定モデル・ポートフォリオ管理
    - metrics.py                    — 評価指標計算
    - run.py                        — CLI エントリポイント
  - execution/                       — 発注・実行関連（プレースホルダ）
  - monitoring/                      — 監視 / アラート用（プレースホルダ）

貢献 / 開発
------------
- 新しいテーブルを追加する場合は data/schema.py の DDL に追加してください。
- DB スキーマを初期化する際は init_schema() を利用してください（既存テーブルは冪等でスキップされます）。
- 単体テストや CI を導入する場合、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い環境依存を排除してテストしてください。

補足
----
- 本 README はコードベースの主要設計と使用例をまとめたサマリです。各モジュールの詳細はソースコード内の docstring を参照してください。
- 実際の運用では API トークン・秘密情報の管理、ログや監視、取り扱うデータ量に合わせた運用設計（バックアップ、DBロック、リソース監視）を必ず検討してください。