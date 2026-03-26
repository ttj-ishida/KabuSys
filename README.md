README
======

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買 / 研究フレームワークです。  
DuckDB をデータ層に用い、ファクター計算・特徴量生成・シグナル生成・ポートフォリオ構築・バックテストを一貫して実行できます。  
主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「ネットワーク・ファイル入出力の堅牢化（SSRF対策等）」です。

主な機能
--------
- データ収集
  - J-Quants API クライアント（株価日足、財務データ、上場銘柄情報、マーケットカレンダー）
  - RSS ニュース収集（SSRF/サイズ/BOM対策・トラッキングパラメータ除去）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB SQL ベース）
  - ファクター探索・IC 計算・統計サマリー
- 特徴量エンジニアリング
  - ファクターの正規化（Z スコア）・ユニバースフィルタ・features テーブルへの UPSERT
- シグナル生成
  - ファクター＋AIスコアを統合し BUY/SELL シグナルを生成（レジーム判定・ベア相場抑制・エグジット条件）
- ポートフォリオ構築
  - 候補選定・重み付け（等金額 / スコア加重 / リスクベース）
  - セクター制限、レジーム乗数、ポジションサイズ計算、単元丸め、aggregate cap のスケール調整
- バックテスト
  - シミュレータ（スリッページ・手数料モデル、部分約定、マーク・トゥ・マーケット）
  - バックテストエンジン（DB コピーしてインメモリで安全に実行）
  - 評価指標（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio 等）
- 補助ユーティリティ
  - 環境変数・設定管理（.env 自動読み込み）
  - レートリミッタ・HTTP リトライ・トークン自動リフレッシュ

前提条件
--------
- Python 3.10+
- DuckDB（python パッケージ）
- defusedxml（RSS の安全なパース用）
- （任意）J-Quants API の利用には有効なリフレッシュトークン
- システムでの .env を用いた設定を想定

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. パッケージをインストール
   - Python パッケージは pyproject.toml がある想定です:
     - pip install -e .
   - 開発用に最低限必要なライブラリのみ手動で入れる場合:
     - pip install duckdb defusedxml
4. 環境変数 (.env) を作成
   - プロジェクトルートに .env（または .env.local）を配置すると自動で読み込まれます（自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数は下記参照。
5. DuckDB スキーマ初期化
   - パッケージ内の schema 初期化関数を利用する想定:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - 注意: backtest を実行する場合は prices_daily / features / ai_scores / market_regime / market_calendar が必要です（データ取得は jquants_client 等で行ってください）。

環境変数（.env 例）
-------------------
以下は主に config.Settings で参照されるキー例です（必須はコメントに記載）。

例 (.env):
    # J-Quants（必須: JQUANTS_REFRESH_TOKEN）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

    # kabu ステーション API（必須: KABU_API_PASSWORD）
    KABU_API_PASSWORD=your_kabu_api_password
    # KABU_API_BASE_URL は省略可（デフォルト: http://localhost:18080/kabusapi）
    KABU_API_BASE_URL=http://localhost:18080/kabusapi

    # Slack（必須: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567

    # DB パス（省略可: デフォルト値あり）
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db

    # 動作モード（development | paper_trading | live）
    KABUSYS_ENV=development

    # ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
    LOG_LEVEL=INFO

注意:
- Settings は JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_* を必須としています。テストや一部機能だけを使う場合は設定を省略できることがありますが、呼び出す機能に応じて必要になるため注意してください。
- .env 自動ロード順: OS 環境変数 > .env.local > .env。

使い方（例）
------------

1) バックテスト（CLI）
- 事前に DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）を用意してください。
- CLI 実行例:
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
- 主要オプション: --cash, --slippage, --commission, --allocation-method (equal|score|risk_based), --max-positions, --lot-size 等。

2) Python API を使った手動実行（REPL / スクリプト）
- 特徴量構築:
    from datetime import date
    import duckdb
    from kabusys.strategy import build_features
    conn = duckdb.connect("data/kabusys.duckdb")
    build_features(conn, date(2024, 1, 4))
- シグナル生成:
    from kabusys.strategy import generate_signals
    generate_signals(conn, date(2024, 1, 4))
- バックテスト呼び出し:
    from kabusys.backtest.engine import run_backtest
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
    # result.history, result.trades, result.metrics を利用

3) データ収集（J-Quants）
- J-Quants から日足等を取得して DuckDB に保存するワークフロー例:
    from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    token = get_id_token()
    recs = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,12,31))
    save_daily_quotes(conn, recs)

4) ニュース収集
- RSS 取得と保存の例:
    from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})

注記と運用上のポイント
---------------------
- Look-ahead バイアス防止: features/signal の計算は target_date の時点までの情報のみを利用する設計です。バックテストでも同様の注意事項を守ってください。
- Bear レジームでは BUY シグナルを抑制する仕様があります（generate_signals 内の判定）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数/設定管理
- data/
  - jquants_client.py             — J-Quants API クライアント（取得・保存）
  - news_collector.py             — RSS ニュース収集・保存
  - (schema.py, calendar_management 等は別途実装)
- research/
  - factor_research.py            — Momentum/Volatility/Value の計算
  - feature_exploration.py        — IC/forward returns/summary 等
- strategy/
  - feature_engineering.py        — features の構築（正規化・UPSERT）
  - signal_generator.py           — BUY/SELL シグナルの生成
- portfolio/
  - portfolio_builder.py          — 候補選定・重み計算
  - position_sizing.py            — 株数計算（risk_based / equal / score）
  - risk_adjustment.py            — セクター上限・レジーム乗数
- backtest/
  - engine.py                     — バックテストループ（run_backtest）
  - simulator.py                  — PortfolioSimulator（約定・履歴管理）
  - metrics.py                    — バックテスト指標計算
  - run.py                        — CLI entry point
  - clock.py                      — （将来拡張用の）模擬時計
- portfolio/..., strategy/... (パッケージエクスポート用 __init__.py 等)

貢献
----
- バグ修正・拡張はプルリクエストを歓迎します。大きな設計変更は事前に Issue を立てて議論してください。
- テスト（ユニット/統合）を用意するとマージがスムーズになります。

免責事項
--------
- 本プロジェクトは研究・教育目的のコードベースです。本番運用（特に real money）で使用する前に十分なレビューと検証を行ってください。投資の最終責任は利用者にあります。

以上。README に含めてほしい追加点や、利用例（特定のワークフロー）の詳述を希望される場合はお知らせください。