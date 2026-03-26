KabuSys
=======

日本株向けの自動売買 / バックテスト / データパイプライン用ライブラリ。  
ファクター計算・特徴量生成・シグナル生成・ポートフォリオ構築・バックテストシミュレータ・外部データ収集（J-Quants、RSS）などのコンポーネントを備え、研究環境とバックテスト環境での再現性ある評価と本番運用（監視・実行）をサポートします。

主な機能
--------
- データ取得・保存
  - J-Quants API クライアント（株価日足、財務データ、JPX カレンダー）
  - RSS ニュース収集（前処理・SSRF/サイズ/XML安全対策）
  - DuckDB への冪等保存ユーティリティ
- 研究用ファクター群
  - momentum / volatility / value 等のファクター計算（DuckDB SQL ベース）
  - ファクターの探索・IC計算・統計サマリー
- 特徴量エンジニアリング
  - 生ファクターの正規化（Z スコア）・ユニバースフィルタ適用・features テーブルへのUPSERT
- シグナル生成
  - features と AI スコアを統合して final_score を算出、BUY/SELL シグナルを生成・signals テーブルへ保存
  - Bear レジーム抑制、売却（stop-loss / score drop）判定
- ポートフォリオ構築
  - 候補選定（スコア順）、等配分／スコア加重／リスクベースのポジションサイジング
  - セクター集中制限、レジーム乗数
- バックテスト
  - イミュータブルなインメモリ DuckDB を構築して現行 DB を汚さずに実行
  - 約定モデル（スリッページ・手数料・部分約定・単元丸め）を持つシミュレータ
  - メトリクス（CAGR, Sharpe, MaxDrawdown, WinRate, Payoff 等）計算
  - CLI エントリポイントで期間指定のバックテスト実行が可能
- ユーティリティ
  - 環境変数 / .env の自動ロード（.git / pyproject.toml を基準）と設定ラッパー
  - News → 銘柄コード抽出・ニュース⇄銘柄紐付け機能

セットアップ
-----------
1. リポジトリをクローン（例）
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. インストール
   - pip install -e .   （プロジェクトを編集可能モードでインストール）
   - 主要な実行に必要な外部依存例:
     - duckdb
     - defusedxml
     - （HTTP 関連は標準ライブラリで実装されている箇所が多いですが、環境に応じて追加パッケージを入れてください）

4. 環境変数 / .env
   - ルートプロジェクトに .env または .env.local を置くと自動で読み込まれます（読み込みは kabusys.config で実装）。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須（またはよく使う）環境変数（例）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須：データ取得）
- KABU_API_PASSWORD — kabuステーション API のパスワード（実運用時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.env の簡易例
----------------
（プロジェクトルートに .env を作成）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（概要）
--------------
- バックテスト（CLI）
  - DuckDB に必要テーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks 等）が事前に整備されている必要があります。
  - 実行例:
    python -m kabusys.backtest.run --start 2023-01-01 --end 2024-12-31 --db data/kabusys.duckdb
  - オプション: --cash, --slippage, --commission, --allocation-method, --max-positions 等

- バックエンド API として利用（Python）
  - DuckDB 接続初期化（schema モジュールを利用）
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
  - バックテスト実行（プログラムから）
    from kabusys.backtest.engine import run_backtest
    result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000, ...)
  - 結果: result.history, result.trades, result.metrics

- 特徴量構築 / シグナル生成（DB を渡して実行）
  - from kabusys.strategy import build_features, generate_signals
  - build_features(conn, target_date)        # features テーブルを更新
  - generate_signals(conn, target_date)      # signals テーブルを更新

- J-Quants データ取得
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, fetch_financial_statements, save_financial_statements
  - id_token = get_id_token()  # get_id_token は settings からリフレッシュトークンを参照
  - data = fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
  - save_daily_quotes(conn, data)

- ニュース収集
  - from kabusys.data.news_collector import run_news_collection
  - run_news_collection(conn, sources=None, known_codes=set_of_codes)

開発向けメモ
--------------
- 環境変数の自動ロードは kabusys.config がプロジェクトルート（.git or pyproject.toml）を探索して .env / .env.local を読み込みます。テスト時に自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB スキーマ初期化: kabusys.data.schema.init_schema(path) を用いて DuckDB 接続を作成してください（schema モジュールに DDL を置く想定）。
- ロギングは標準 logging を使用。LOG_LEVEL を環境変数で設定できます。

ディレクトリ構成（主要部分）
---------------------------
src/kabusys/
- __init__.py
- config.py                         # 環境変数/.env ローダーと Settings
- data/
  - jquants_client.py               # J-Quants API client + DuckDB 保存
  - news_collector.py               # RSS 集約・保存・銘柄抽出
  - ...                             # schema, calendar_management 等を想定
- research/
  - factor_research.py              # momentum/volatility/value の計算
  - feature_exploration.py          # IC, forward returns, summary
- strategy/
  - feature_engineering.py          # features テーブル構築（正規化・フィルタ）
  - signal_generator.py             # final_score 計算・signals 書き込み
- portfolio/
  - portfolio_builder.py            # 候補選定・重み計算
  - position_sizing.py              # 株数決定・aggregate cap
  - risk_adjustment.py              # セクター制限・レジーム乗数
- backtest/
  - engine.py                       # run_backtest（高レベルループ）
  - simulator.py                    # 約定モデル・ポートフォリオ状態
  - metrics.py                      # バックテスト指標計算
  - run.py                          # CLI entrypoint for backtest
  - clock.py
- research/
  - ...                             # 研究用ユーティリティ群
- execution/                         # 実取引実行層（空 __init__ が存在）
- monitoring/                        # 監視・アラート周り（未展示の実装）
- portfolio/__init__.py              # パブリック API エクスポート
- strategy/__init__.py               # パブリック API エクスポート
- backtest/__init__.py               # パブリック API エクスポート
- その他ユーティリティモジュール...

主要な公開 API（例）
- kabusys.strategy.build_features(conn, date)
- kabusys.strategy.generate_signals(conn, date)
- kabusys.backtest.run_backtest(conn, start_date, end_date, ...)
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
- kabusys.data.news_collector.run_news_collection

よくある利用フロー（ETL → 特徴量 → シグナル → バックテスト）
1. J-Quants から prices / financials / calendar を取得して DuckDB に保存
2. feature_engineering.build_features(conn, target_date) で features を構築
3. strategy.signal_generator.generate_signals(conn, target_date) で signals を生成
4. backtest.engine.run_backtest(...) でリターンやリスク特性を評価

ライセンス / 貢献
-----------------
- 本プロジェクトのライセンス情報や貢献ガイド（CONTRIBUTING.md）等があればプロジェクトルートに追加してください。

補足
----
- ドキュメント内の仕様参照（PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md, DataPlatform.md 等）は実装上の設計メモを示しており、詳細設計や定数の根拠はそれらのドキュメントに従います（リポジトリに存在する場合は参照してください）。
- DuckDB のスキーマ初期化や外部接続設定等、運用に必要な初期データ準備は schema モジュールや ETL スクリプトで実施してください。

問題報告・質問
--------------
不具合や仕様に関する質問は Issue を立ててください。README に記載のない使い方や API 参照が必要であれば追補ドキュメントを作成します。