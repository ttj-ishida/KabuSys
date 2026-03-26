KabuSys
=======

日本株向けの自動売買 / 研究用フレームワークの一部実装です。  
バックテスト、ファクター計算、特徴量生成、シグナル生成、データ取得（J-Quants）、ニュース収集、ポートフォリオ構築、簡易な実行シミュレータなどのモジュール群を備えています。

主な目的
- 研究（factor research / feature engineering / feature exploration）
- シグナル生成（strategy）
- バックテスト（backtest）
- データ ETL（J-Quants クライアント、ニュース収集）
- ポートフォリオ構築とサイズ決定（portfolio）

機能一覧
- 環境設定読み込み（.env 自動ロード / Settings）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN 等）
- データ取得 / 保存
  - J-Quants API クライアント（レート制御、リトライ、トークン自動更新）
  - DuckDB への保存ユーティリティ（raw_prices / raw_financials / market_calendar 等）
- ニュース収集
  - RSS フィード取得、前処理、raw_news / news_symbols への保存
  - SSRF/サイズ/XML 脆弱性対策済み
- 研究用モジュール
  - Momentum / Volatility / Value などのファクター計算（research/factor_research）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計（feature_exploration）
  - Z スコア正規化ユーティリティの利用
- 特徴量作成（strategy/feature_engineering）
  - raw ファクターを正規化・フィルタして features テーブルへ書き込み
- シグナル生成（strategy/signal_generator）
  - features + ai_scores を統合して final_score を算出し BUY/SELL を生成
  - Bear レジームの抑制、エグジット（ストップロス / スコア低下）判定
- ポートフォリオ構築（portfolio）
  - 候補選定、等配分/スコア加重配分、リスクベース配分、セクターキャップ、レジーム乗数
  - 株数決定（単元丸め / aggregate cap / 部分約定対応）
- バックテストフレームワーク（backtest）
  - インメモリ DuckDB へデータをコピーして独立にバックテスト実行
  - PortfolioSimulator による約定・履歴管理
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）

セットアップ手順（ローカル開発環境）
- 前提
  - Python 3.10 以上（型注釈の | 演算子等を使用）
- 推奨パッケージ（例）
  - duckdb
  - defusedxml
  - そのほか標準ライブラリ以外の依存があれば requirements.txt を参照してください

例）
1) 仮想環境作成・有効化
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows (PowerShell)

2) インストール（プロジェクトルートで）
   pip install --upgrade pip
   pip install duckdb defusedxml

   ※ パッケージ配布用に setup.py / pyproject.toml がある場合は
   pip install -e . で編集可能インストールができます。

3) 環境変数設定
   プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます。
   自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必要な主要環境変数（例）
   - JQUANTS_REFRESH_TOKEN  … J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD      … kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL      … kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN        … Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID       … 通知先 Slack チャンネル ID（必須）
   - DUCKDB_PATH            … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH            … 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV            … development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL              … DEBUG/INFO/…（デフォルト: INFO）

使い方（代表例）

- DuckDB スキーマ初期化 / DB 接続
  ※ schema モジュール（kabusys.data.schema）で init_schema(db_path) を使ってスキーマ初期化する想定です。
  例:
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- J-Quants から日足取得して保存
    from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    from kabusys.config import settings
    conn = init_schema(settings.duckdb_path)
    records = fetch_daily_quotes(date_from=..., date_to=...)
    save_daily_quotes(conn, records)
    conn.close()

- ニュース収集（RSS）
    from kabusys.data.news_collector import run_news_collection
    conn = init_schema("data/kabusys.duckdb")
    known_codes = {"7203","6758", ...}  # 抽出に用いる銘柄コードセット
    results = run_news_collection(conn, known_codes=known_codes)
    conn.close()

- 特徴量構築
    from kabusys.strategy.feature_engineering import build_features
    conn = init_schema("data/kabusys.duckdb")
    from datetime import date
    n = build_features(conn, target_date=date(2024, 1, 31))
    print("upserted features:", n)

- シグナル生成
    from kabusys.strategy.signal_generator import generate_signals
    from datetime import date
    conn = init_schema("data/kabusys.duckdb")
    count = generate_signals(conn, target_date=date(2024, 1, 31))
    print("signals written:", count)

- バックテスト（CLI）
  プロジェクトに含まれる CLI エントリポイントを使う例:
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 \
      --slippage 0.001 --commission 0.00055 \
      --allocation-method risk_based \
      --max-positions 10 \
      --lot-size 100 \
      --db data/kabusys.duckdb

  出力例として CAGR, Sharpe, Max Drawdown, Win Rate 等が表示されます。

- バックテストを Python API で実行する
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.backtest.engine import run_backtest
    conn = init_schema("data/kabusys.duckdb")
    result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
    print(result.metrics)
    conn.close()

主要設定（補足）
- 配分方式: allocation_method は "equal" | "score" | "risk_based"
- レジーム乗数: calc_regime_multiplier により bull/neutral/bear の乗数を適用
- セクター上限: apply_sector_cap でセクター集中リスクを制限
- 単元丸め: lot_size（デフォルト 100）に基づいて数量を丸めます

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                            # 環境変数設定管理
  - data/
    - jquants_client.py                   # J-Quants API クライアント + 保存
    - news_collector.py                   # RSS 収集・前処理・DB 保存
    - (schema.py, stats.py, calendar_management.py 等を想定)
  - research/
    - factor_research.py                  # Momentum / Volatility / Value 等
    - feature_exploration.py              # 将来リターン / IC / summary
  - strategy/
    - feature_engineering.py              # features 作成
    - signal_generator.py                 # final_score とシグナル生成
  - portfolio/
    - portfolio_builder.py                # 候補選定 / 重み計算
    - position_sizing.py                  # 株数決定・aggregate cap
    - risk_adjustment.py                  # セクター上限 / レジーム乗数
  - backtest/
    - engine.py                           # バックテスト エンジン
    - simulator.py                        # PortfolioSimulator（擬似約定）
    - metrics.py                          # バックテスト評価指標
    - run.py                              # CLI エントリポイント
    - clock.py
  - execution/                             # 実取引実行レイヤ（空のパッケージ）
  - monitoring/                            # 監視・通知関連（想定）
  - portfolio/__init__.py
  - strategy/__init__.py
  - research/__init__.py
  - backtest/__init__.py

注意事項 / ベストプラクティス
- Look-ahead bias に注意
  - 特徴量・シグナル生成は target_date 時点で利用可能なデータのみを使う設計を心がけていますが、ETL 時のデータ取得タイミングには十分注意してください。
- 本番実行（kabuステーション API、実売買）は慎重に
  - 本実装はバックテスト・研究向けのロジックを多く含みます。実際の発注や口座資金の移動を行う前にペーパートレードで十分検証してください。
- 環境変数の扱い
  - .env の自動ロードはプロジェクトルート（.git または pyproject.toml を起点）を探索します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用して自動ロードを無効にできます。

貢献
- バグ報告や機能追加は issue / PR を歓迎します。コードスタイルやテストカバレッジを合わせてご提供ください。

以上がこのコードベースの概要と使い方の説明です。必要であれば具体的なサンプルスクリプト（データ取得 → features 作成 → シグナル生成 → バックテストまでのワークフロー）を用意しますのでお知らせください。