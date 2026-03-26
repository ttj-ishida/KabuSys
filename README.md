KabuSys
=======

日本株向けの自動売買・リサーチ基盤ライブラリ（バックテスト、ファクター計算、データ収集など）。

概要
----
KabuSys は日本株の量的運用ワークフローをサポートする Python モジュール群です。主な目的は以下：

- 価格・財務・ニュース等のデータ収集（J-Quants クライアント / RSS ニュース収集）
- 研究向けファクター計算・特徴量正規化（research モジュール）
- 戦略の特徴量合成とシグナル生成（strategy モジュール）
- ポートフォリオ構築（候補選定、重み付け、リスク調整、発注株数決定）
- バックテスト環境（擬似約定、ポートフォリオ履歴、評価指標計算）
- 環境変数による設定管理（自動 .env 読み込み）

主な機能
---------
- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須設定を Settings クラスで提供（settings.jquants_refresh_token など）
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD

- データ取得と ETL
  - J-Quants API クライアント（レート制御・リトライ・自動トークン更新）
    - 株価日足、財務データ、上場情報、マーケットカレンダー取得
  - RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去、記事ID の SHA-256 ベース生成）

- 研究（research）
  - momentum / volatility / value 等のファクター計算（DuckDB 接続を受ける純粋関数）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ

- 特徴量エンジニアリング & シグナル生成（strategy）
  - features テーブルの構築（Z スコア正規化、クリップ、ユニバースフィルタ）
  - ai_scores と統合して final_score を計算し BUY / SELL シグナルを生成
  - Bear レジーム時の BUY 抑制、SELL のエグジット判定（ストップロス等）

- ポートフォリオ構築（portfolio）
  - 候補選定（スコア降順）
  - 等配分 / スコア重み / リスクベース配分
  - セクター集中上限適用、レジーム乗数
  - 株数決定（単元丸め、aggregate cap、部分約定スケールダウン）

- バックテスト（backtest）
  - インメモリ DuckDB を用いた安全なバックテスト用 DB 作成
  - PortfolioSimulator による擬似約定（スリッページ・手数料モデル、部分約定対応）
  - 日次マークツーマーケット、トレード履歴記録
  - メトリクス計算（CAGR、Sharpe、Max Drawdown、勝率、Payoff、総トレード数）
  - CLI エントリポイント: python -m kabusys.backtest.run

セットアップ
------------
前提
- Python 3.10+（一部の型注釈や機能を使用）
- DuckDB（Python パッケージ duckdb）
- ネットワーク接続（J-Quants API / RSS フィード へのアクセス）

インストール（開発環境）
1. リポジトリをクローン
   git clone <repo-url>
2. 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. パッケージをインストール
   pip install -e .      # setup.py / pyproject.toml が必要
   pip install duckdb defusedxml

環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabu API（kabuステーション）パスワード
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャネル ID

任意 / 推奨
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | ...)
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）

.env 自動読み込み
- プロジェクトルートに .env / .env.local を配置すると、パッケージ import 時に自動で読み込まれます。
- テスト等で自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（概要と例）
-----------------

1) バックテスト（CLI）
- 必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）が入った DuckDB ファイルを用意してください。
- 実行例：
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db path/to/kabusys.duckdb \
    --allocation-method risk_based --lot-size 100

2) バックテスト（プログラム的に）
- Python から直接呼ぶ場合（DuckDB 接続を用意）：
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("path/to/kabusys.duckdb")
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  conn.close()
  # result.history, result.trades, result.metrics を参照

3) 特徴量構築・シグナル生成（プログラム）
- DuckDB 接続を渡して関数を呼び出すだけです。
  from kabusys.strategy import build_features, generate_signals
  build_features(conn, target_date)
  generate_signals(conn, target_date)

4) データ取得（J-Quants）
- トークン取得：
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()
- 日足取得・保存：
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=..., date_to=...)
  save_daily_quotes(conn, records)

5) ニュース収集（RSS）
- 単独ソース取得と DB 保存：
  from kabusys.data.news_collector import run_news_collection
  result = run_news_collection(conn, sources=None, known_codes=known_codes_set)
  # result: {source_name: saved_count}

注意事項 / 運用メモ
- Look-ahead bias 対策として、各処理は target_date 時点で利用可能なデータのみを参照する設計になっています（fetched_at 等の記録、取得日指定など）。
- J-Quants API はレート制限とリトライ処理が組み込まれています。API の利用制限に注意してください。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）検出に基づき行われます。別の場所から import した場合は期待通りに動かないことがあります。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                           # 環境変数 / Settings
- data/
  - jquants_client.py                  # J-Quants API クライアント
  - news_collector.py                  # RSS ニュース収集
  - ... (schema, calendar_management 等が想定)
- research/
  - factor_research.py                 # momentum / value / volatility 等
  - feature_exploration.py             # IC / forward returns / summary
- strategy/
  - feature_engineering.py             # features テーブル構築
  - signal_generator.py                # final_score と signals 生成
- portfolio/
  - portfolio_builder.py               # 候補選定・重み計算
  - position_sizing.py                 # 株数算出・aggregate cap
  - risk_adjustment.py                 # セクターキャップ・レジーム乗数
- backtest/
  - engine.py                          # バックテストのメインループ
  - simulator.py                       # 擬似約定・PortfolioSimulator
  - metrics.py                         # バックテスト評価指標
  - run.py                             # CLI エントリポイント
- execution/                            # 発注・実行層（実装ファイルは別途）
- monitoring/                           # 監視・アラート関連（実装ファイルは別途）
- portfolio/__init__.py
- strategy/__init__.py
- research/__init__.py
- backtest/__init__.py

（リポジトリ上で pyproject.toml / setup.py があれば pip インストール可能です。）

貢献
----
バグ報告・機能提案は issue を立ててください。大きな変更は事前に issue で議論をお願いします。

ライセンス
--------
本 README にライセンス情報は含まれていません。リポジトリの LICENSE ファイルを参照してください。

補足
----
- 簡易的な使用例や追加の CLI / ETL スクリプトはプロジェクトの tools / scripts 等に置くことを想定しています。
- DuckDB のスキーマ初期化関数（kabusys.data.schema.init_schema）や市場カレンダー取得ユーティリティなどは本 README の使用例で参照されています。環境に応じてこれらのユーティリティを実装・準備してください。