KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買 / 研究フレームワークです。  
データ収集（J-Quants、RSS）、ファクター計算、特徴量エンジニアリング、シグナル生成、ポートフォリオ構築、バックテストシミュレータまで一貫して提供します。  
モジュール設計は「ルックアヘッドバイアス排除」「DuckDB ベースのデータレイク」「冪等な ETL / DB 書き込み」「テスト可能な純粋関数化」を重視しています。

主な機能
--------
- データ取得・保存
  - J-Quants API クライアント（価格・財務・上場情報・マーケットカレンダー） — rate limit / retry / token refresh を実装
  - RSS ニュース収集、記事前処理、銘柄抽出（SSRF対策・gzip対応・トラッキングパラメータ除去）
  - DuckDB への冪等保存（ON CONFLICT / INSERT ... RETURNING 使用）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials 参照）
  - Zスコア正規化ユーティリティ、IC / 相関 /統計サマリ機能
- 特徴量エンジニアリング
  - 研究結果を正規化・クリップして features テーブルへ UPSERT（冪等）
- シグナル生成
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成して signals に保存
  - Bear レジーム抑制、ストップロス判定等のルール実装
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額／スコア加重／リスクベースのサイジング
  - セクター上限適用、レジーム乗数（bull/neutral/bear）
- バックテスト
  - メモリ上シミュレータ（約定モデル：スリッページ、手数料、部分約定、単元丸め）
  - 日次ループで signals → 約定 → positions 更新 → 時価評価 → 次日発注 を再現
  - バックテスト評価指標（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio）
  - CLI 実行エントリポイントを提供

セットアップ（手順）
------------------

前提
- Python 3.10+ を想定（typing の union 表記などを使用）
- DuckDB を利用するため C 環境が必要な場合があります

基本手順（開発環境）
1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - 本リポジトリの pyproject.toml/requirements.txt に依存があればそちらを利用してください。
   - 最低限必要なパッケージ例:
     - pip install duckdb defusedxml

   （注）実装で使用している外部パッケージはソース内から確認してください。

4. パッケージをインストール（開発モード）
   - pip install -e .

環境変数（必須・推奨）
- 自動でプロジェクトルートの .env（および .env.local）を読み込みます（.git または pyproject.toml を基準に検索）。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

必須（実行に必要な環境変数）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API（kabuステーション）パスワード（運用時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

その他（データベースパス等、デフォルトあり）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

使い方（代表的ワークフロー）
--------------------------

1) DuckDB スキーマ初期化
- スキーマ初期化関数を提供しています（kabusys.data.schema.init_schema）。
  - 例:
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

  （注: schema モジュールはプロジェクト内にある想定です。初期化後、必要テーブルが作成されます）

2) データ収集（J-Quants）
- J-Quants からデータを取得し DuckDB に保存
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を利用
  - recs = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
  - save_daily_quotes(conn, recs)

- 財務データ、上場情報、マーケットカレンダーも同様に fetch_* / save_* が利用可能

3) ニュース収集
- RSS からニュースを収集して raw_news に保存
  - from kabusys.data.news_collector import run_news_collection
  - run_news_collection(conn, sources=None, known_codes=set_of_codes)

4) 特徴量作成
- DuckDB の接続と日付を渡して features を生成
  - from kabusys.strategy import build_features
  - build_features(conn, target_date=date(2024,1,1))

5) シグナル生成
- features / ai_scores / positions を参照して signals を生成
  - from kabusys.strategy import generate_signals
  - generate_signals(conn, target_date=date(2024,1,1), threshold=0.6)

6) バックテスト実行（API）
- run_backtest 関数に本番 DB 接続と日付を渡すとバックテストを実行します
  - from kabusys.backtest.engine import run_backtest
  - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000, ...)

7) バックテスト CLI
- 実行例:
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2024-12-31 --db data/kabusys.duckdb
- CLI は各種パラメータ（slippage, commission, allocation-method, lot-size 等）を受け取ります。

主要 API（要約）
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, save_daily_quotes, fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar, fetch_listed_info
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
- kabusys.strategy
  - build_features(conn, date), generate_signals(conn, date)
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...), BacktestResult, simulator / metrics utilities

ディレクトリ構成（主要ファイル）
------------------------------
以下はソース配下の主要モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env ロードと Settings
  - data/
    - jquants_client.py     — J-Quants API クライアント（取得・保存）
    - news_collector.py     — RSS ニュース収集・保存・銘柄抽出
    - schema.py             — DuckDB スキーマ初期化（想定）
    - calendar_management.py — 取引日取得等（想定）
    - stats.py              — 正規化ユーティリティ等（想定）
  - research/
    - factor_research.py    — momentum/volatility/value の算出
    - feature_exploration.py— IC / forward returns / summary
  - strategy/
    - feature_engineering.py— features 作成
    - signal_generator.py   — signals 作成ロジック
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 発注株数計算
    - risk_adjustment.py    — セクター制限・レジーム乗数
  - backtest/
    - engine.py             — バックテストループ（run_backtest）
    - simulator.py          — 約定モデル・ポートフォリオ管理
    - metrics.py            — バックテスト評価指標
    - run.py                — CLI エントリポイント
    - clock.py              — 将来用の模擬時計
  - execution/              — 実運用（kabu API 等）層（骨格）
  - monitoring/             — 監視・アラート系（骨格）
  - portfolio/              — パッケージエクスポート（__init__.py）

実運用での注意点 / ベストプラクティス
-------------------------------------
- Look-ahead バイアス排除: 特徴量・シグナル生成は target_date 時点で利用可能なデータのみを使うことを設計上徹底しています。ETL 時も fetched_at を記録してください。
- 環境設定: .env/.env.local の優先順位は OS 環境 > .env.local > .env。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを抑制できます。
- レジーム運用: KABUSYS_ENV を適切に設定して paper_trading/live の動作を切り替えてください（settings.is_live 等でチェック可能）。
- 単元株丸め、手数料、スリッページはバックテストと本番で整合性を持たせること。バックテストではデフォルト lot_size=100 を想定しています。

貢献 / 開発
------------
- 新しいデータソースやファクターを追加する場合は research/ または data/ 下にモジュールを追加し、既存の build_features / generate_signals のフローと互換性を保つこと。
- テストは純粋関数（research/portfolio/ backtest/metrics 等）に対してユニットテストを書きやすい構造になっています。

ライセンス / その他
-------------------
- 本リポジトリに含まれるライセンス情報に従ってください（LICENSE ファイル等）。

---

この README はコードベースの主要機能と典型的なワークフローをまとめたものです。実行に必要な追加の設定（DuckDB スキーマ定義、requirements）はプロジェクト内の schema / pyproject.toml / requirements ファイルを参照してください。必要であれば、README に具体的なスキーマ作成手順やサンプル .env を追記します。