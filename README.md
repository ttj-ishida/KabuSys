# KabuSys

日本株向けの自動売買／リサーチ基盤ライブラリ（バックテスト・データ取り込み・特徴量 / シグナル生成 等）

※ 本 README はコードベース（src/kabusys 以下）に基づくドキュメントです。

## プロジェクト概要
KabuSys は日本株の量的運用（リサーチ・バックテスト・運用支援）を目的としたモジュール群です。  
主な役割は以下の通りです。

- データ取得・ETL（J-Quants API、RSS ニュース等）と DuckDB への保存
- 研究向けファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量正規化・features テーブル作成
- シグナル生成（ファクター + AI スコアの統合）
- ポートフォリオ構築（候補選定・配分・リスク調整・サイジング）
- バックテストエンジン（擬似約定・ポートフォリオ追跡・メトリクス算出）
- ニュース収集と記事→銘柄紐付け

設計方針としては「ルックアヘッドバイアス防止」「冪等な DB 操作」「外部 API のレート制御・リトライ」「バックテストは DB を汚さない」などを掲げています。

## 主な機能一覧
- データ
  - J-Quants API クライアント（株価、財務、上場銘柄情報、マーケットカレンダー）
  - RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去）
  - DuckDB への冪等保存ユーティリティ
- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング（strategy.feature_engineering）
  - ファクターのマージ、ユニバースフィルタ、Z スコア正規化、features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し BUY/SELL シグナル生成
  - Bear レジーム抑制、SELL（エグジット）判定
- ポートフォリオ（portfolio）
  - 候補選定、等重/スコア重み、リスク調整（セクターキャップ・レジーム乗数）
  - ポジションサイジング（risk_based / equal / score）
- バックテスト（backtest）
  - run_backtest: インメモリ DuckDB にデータをコピーして日次ループでシミュレーション
  - PortfolioSimulator（擬似約定・スリッページ・手数料モデル）
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff 等）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- その他
  - 環境変数管理（.env 自動ロード・必須チェック）
  - news_collector による記事保存と銘柄抽出

## 要求環境（目安）
- Python 3.10 以上（型注釈に PEP 604 等を使用）
- DuckDB（python duckdb パッケージ）
- defusedxml（RSS XML の安全パース）
- 標準ライブラリ（urllib, sqlite/duckdb, logging 等）

※ 実行に必要な詳細な依存関係はプロジェクトの pyproject.toml / requirements.txt を参照してください（本コード断片では含まれていません）。

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン、ワークディレクトリへ移動
   - 例: git clone ... && cd repo

2. Python 仮想環境作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （プロジェクトに requirements があればそれを使用: pip install -r requirements.txt）
   - 開発インストール（パッケージとして利用する場合）:
     - pip install -e .

4. 環境変数設定 (.env)
   - プロジェクトルート（.git や pyproject.toml のある階層）に .env / .env.local を配置すると自動でロードされます（kabusys.config が自動で読み込み）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1（あるいは Windows で set ...）
   - 必要な環境変数（主要なもの）
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
     - KABU_API_BASE_URL (任意, デフォルト http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須) — Slack 通知用
     - SLACK_CHANNEL_ID (必須)
     - DUCKDB_PATH (任意, デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (任意, デフォルト data/monitoring.db)
     - KABUSYS_ENV (任意, development|paper_trading|live、デフォルト development)
     - LOG_LEVEL (任意, DEBUG|INFO|...、デフォルト INFO)

5. DuckDB DB の準備
   - データパイプラインで使用するテーブル（例: prices_daily, raw_prices, raw_financials, features, ai_scores, market_regime, market_calendar, stocks, positions, signals, raw_news, news_symbols など）を作成しておく必要があります。
   - 本コードでは schema 初期化関数が kabusys.data.schema.init_schema に実装されている想定です（このファイルはコード断片に含まれていません）。

## 使い方（代表例）

- バックテスト（CLI）
  - 事前条件: DuckDB ファイルに必要なテーブル・データが格納されていること
  - 実行例:
    - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db path/to/kabusys.duckdb
  - よく使うオプション:
    - --cash: 初期資金
    - --slippage / --commission: スリッページ・手数料率
    - --allocation-method: equal | score | risk_based
    - --max-positions / --max-utilization / --lot-size など

- バックテストをプログラムから呼ぶ
  - from kabusys.data.schema import init_schema
    conn = init_schema("path/to/kabusys.duckdb")
    from kabusys.backtest.engine import run_backtest
    result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000, ...)
    conn.close()

- 特徴量構築（features 作成）
  - from kabusys.strategy import build_features
    build_features(conn, target_date)
  - conn は DuckDB 接続。prices_daily / raw_financials テーブルを参照します。

- シグナル生成
  - from kabusys.strategy import generate_signals
    generate_signals(conn, target_date, threshold=0.6, weights=None)

- データ取得（J-Quants）
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
    token = get_id_token()
    recs = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
    save_daily_quotes(conn, recs)

- ニュース収集
  - from kabusys.data.news_collector import run_news_collection
    run_news_collection(conn, sources=None, known_codes=set_of_codes)

- ポートフォリオ関数の利用例
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

## 注意点 / 運用上のポイント
- ルックアヘッドバイアスの防止
  - 特徴量 / シグナル生成関数は target_date 時点までのデータのみを参照するよう設計されています。バックテストでは DB に保存された時刻や fetched_at を使って過去の状態を再現してください。
- 冪等性
  - 多くの save_* 関数や features/signals への書き込みは「日付単位で DELETE→INSERT」などで冪等性を保つ実装になっています。
- レート制限・認証
  - J-Quants クライアントは 120 req/min の制限を守るための RateLimiter、401 時トークン自動更新、リトライロジックを備えています。
- セキュリティ
  - news_collector は SSRF 対策、XML の安全パース、レスポンスサイズ制限などを実装しています。
- 環境変数の自動ロード
  - kabusys.config はプロジェクトルートの .env / .env.local を自動で読み込みます。テスト時などでこれを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## ディレクトリ構成（主なファイル）
以下は src/kabusys 以下の主なモジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
  - data/
    - jquants_client.py          — J-Quants API クライアント & DuckDB 保存ユーティリティ
    - news_collector.py         — RSS 収集・前処理・raw_news 保存・銘柄抽出
    - (その他: schema, calendar_management, stats などが想定)
  - research/
    - factor_research.py        — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py    — 将来リターン / IC / 統計サマリー
  - strategy/
    - feature_engineering.py    — features 作成・正規化・フィルタ
    - signal_generator.py       — final_score 計算・BUY/SELL シグナル生成
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 株数算出・集約キャップ処理
    - risk_adjustment.py        — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py                 — run_backtest（インメモリコピー＋日次ループ）
    - simulator.py              — PortfolioSimulator（擬似約定・履歴記録）
    - metrics.py                — バックテスト評価指標計算
    - run.py                    — CLI ラッパー（python -m kabusys.backtest.run）
    - clock.py                  — 将来用の SimulatedClock（現状は参照のみ）
  - portfolio/ __init__.py      — 主要 API のエクスポート
  - strategy/ __init__.py       — build_features, generate_signals エクスポート
  - research/ __init__.py       — 研究用 API のエクスポート

（実際のリポジトリでは data.schema やその他の補助モジュールが存在する想定です。）

## 開発 / デバッグのヒント
- ロギングは config.settings.log_level や環境変数 LOG_LEVEL で制御できます。
- DuckDB 接続は kabusys.data.schema.init_schema() を利用して初期化する想定です（本コード断片では実装参照不可）。
- 単体テストやリサーチ用スクリプトでは KABUSYS_DISABLE_AUTO_ENV_LOAD を ON にして .env の自動ロードを止め、テスト環境で明示的に環境変数を設定すると楽です。

---

追加で README に含めたい例（SQL スキーマ、サンプル .env.example、pip install の正確な依存リスト 等）があれば、その情報を提供してください。README をそれに合わせて拡張します。