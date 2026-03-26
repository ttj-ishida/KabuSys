KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株を対象とした自動売買・バックテスト・データ収集のための Python ライブラリです。  
特徴量計算、シグナル生成、ポートフォリオ構築、擬似約定シミュレータ、バックテストエンジン、J-Quants / RSS によるデータ取得・ETL 等のモジュールを含みます。  
設計は「ルックアヘッドバイアス回避」「冪等性」「テスト可能性」を重視しており、DuckDB を用いた分析・バックテストを想定しています。

主な機能
--------
- データ取得/保存
  - J-Quants API クライアント（株価日足・財務データ・マーケットカレンダー取得、保存用ユーティリティ）
  - RSS ニュース収集（前処理・記事ID生成・銘柄抽出・DB 保存）
- 研究（research）
  - ファクター計算（Momentum / Volatility / Value）
  - ファクター探索・IC 計算・統計サマリー
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング（strategy.feature_engineering）
  - 生ファクターを正規化・合成して features テーブルへ書き込む
- シグナル生成（strategy.signal_generator）
  - features + ai_scores を統合して final_score を算出し BUY / SELL を生成
  - Bear レジーム抑制、エグジット（ストップロス、スコア低下）判定
- ポートフォリオ構築（portfolio）
  - 候補選定、重み算出（等配分 / スコア加重）、株数サイジング（リスクベース等）
  - セクター集中制限、レジーム乗数
- バックテスト（backtest）
  - インメモリ DuckDB によるデータ準備
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）
  - 日次ループでの発注/約定・positions 書き戻し・シグナル生成連携
  - メトリクス算出（CAGR・Sharpe・MaxDD・勝率・Payoff 等）
  - CLI エントリポイントで期間指定のバックテスト実行
- 実行環境設定
  - .env / .env.local / OS 環境変数から設定を読み込むユーティリティ（自動ロードを無効にするフラグあり）

セットアップ
-----------
前提
- Python 3.10+（typing の一部で | 記法を利用）
- DuckDB（Python パッケージ）
- defusedxml（RSS パース安全化）
- その他標準ライブラリ（urllib, datetime, logging 等）

例: 仮想環境作成とパッケージインストール
- Unix / macOS
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install duckdb defusedxml
- Windows (PowerShell)
  - python -m venv .venv
  - .\.venv\Scripts\Activate.ps1
  - pip install --upgrade pip
  - pip install duckdb defusedxml

※ プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください。  
※ 本 README 作成時点ではパッケージ配布ファイルは含まれていないため、開発環境ではソースツリー直下で pip install -e . を想定できます。

環境変数（必須 / 代表例）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須） — strategy/data の取得で使用
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 動作モード（development / paper_trading / live。デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL。デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動ロードを無効化

プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただしテスト目的等で自動ロードを無効化可能）。

使い方（主要な例）
-----------------

1) DuckDB スキーマ初期化（想定 API）
- コード中で kabusys.data.schema.init_schema(db_path) を呼ぶことで DB 接続とスキーマ初期化を行う想定です。
  例:
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

2) 特徴量の構築（features テーブルへ挿入）
- build_features(conn, target_date)
  例:
    from datetime import date
    from kabusys.strategy import build_features
    build_features(conn, target_date=date(2024, 1, 31))

  この関数は prices_daily / raw_financials を参照して normalized features を features テーブルに日付単位で UPSERT（完全置換）します。

3) シグナル生成（signals テーブルへ挿入）
- generate_signals(conn, target_date, threshold=0.6, weights=None)
  例:
    from kabusys.strategy import generate_signals
    generate_signals(conn, target_date=date(2024,1,31), threshold=0.60)

  Bear レジーム判定や AI スコアの補完ロジックを含み、BUY/SELL を signals テーブルへ日付単位で置換します。

4) バックテスト実行（CLI）
- 提供されているエントリポイント:
    python -m kabusys.backtest.run --start YYYY-MM-DD --end YYYY-MM-DD --db path/to/kabusys.duckdb [その他オプション]

  例:
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db data/kabusys.duckdb \
      --allocation-method risk_based --max-positions 10

  主なオプション（抜粋）:
    --cash: 初期資金（円）
    --slippage: スリッページ率（デフォルト 0.001）
    --commission: 手数料率（デフォルト 0.00055）
    --allocation-method: equal | score | risk_based（デフォルト risk_based）
    --lot-size: 単元株数（デフォルト 100）

  実行結果としてバックテストの主要メトリクス（CAGR / Sharpe / MaxDD / WinRate / Payoff / Trades）が標準出力に表示され、内部的に history / trades / metrics が計算されます。

5) ニュース収集（RSS）
- 関数 run_news_collection(conn, sources=None, known_codes=None, timeout=30) を使用して RSS ソースから記事を取得・保存します。  
  例:
    from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(['7203','6758']))

  取得した記事は raw_news / news_symbols へ保存され、記事 → 銘柄の紐付け処理も行えます。

6) J-Quants API 利用
- get_id_token(), fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...) によるデータ取得と save_* 関数による DuckDB への保存が可能です。  
  取得は自動リトライ・レート制御・401 リフレッシュを備えています。

主要 API（呼び出し例）
- strategy.build_features(conn, date)
- strategy.generate_signals(conn, date)
- backtest.run_backtest(conn, start_date, end_date, initial_cash=..., ...)
- data.jquants_client.fetch_daily_quotes(...)
- data.news_collector.run_news_collection(...)

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / .env 自動ロード / Settings
- data/
  - jquants_client.py       — J-Quants API クライアント + DuckDB 保存ユーティリティ
  - news_collector.py       — RSS 取得・前処理・保存・銘柄抽出
  - (その他: schema.py, calendar_management 等が想定)
- research/
  - factor_research.py      — Momentum / Volatility / Value ファクター計算
  - feature_exploration.py  — 将来リターン / IC / 統計サマリー
- strategy/
  - feature_engineering.py  — features の構築
  - signal_generator.py     — final_score → signals 生成ロジック
- portfolio/
  - portfolio_builder.py    — 候補選定 / 重み計算
  - position_sizing.py      — 株数計算（risk_based / equal / score）
  - risk_adjustment.py      — セクター制限 / レジーム乗数
- backtest/
  - engine.py               — バックテストループ（データ準備・発注ロジック）
  - simulator.py            — PortfolioSimulator（擬似約定・履歴管理）
  - metrics.py              — バックテストメトリクス計算
  - run.py                  — CLI エントリポイント
  - (clock.py 他)
- execution/                 — 実運用の execution 層（API 呼び出し等、未詳細）
- monitoring/               — 監視・ログ・通知関連（未詳細）

設計上の注意点 / 運用上の注意
----------------------------
- ルックアヘッドバイアス回避:
  - features / signals / raw データ取得は「対象日時点で利用可能なデータのみ」を使う設計です。バックテストでは過去データのみをコピーして実行してください。
- 冪等性:
  - 保存系関数（save_* / build_features / generate_signals 等）は日付単位で置換（DELETE→INSERT）することで冪等性を確保します。
- 環境読み込み:
  - config.Settings はプロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を自動ロードします。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テスト・モック:
  - ネットワーク呼び出しや時間に依存する部分は外部から差し替え可能（例: news_collector._urlopen をモック）な設計になっています。

貢献 / 拡張案
--------------
- stocks マスタに銘柄ごとの lot_size を持たせ、position_sizing を拡張する
- execution 層の kabu/証券会社 API 実装（注文送信・約定確認）
- AI スコア算出パイプラインの追加（ai_scores テーブルの自動生成）
- 分足シミュレーションの実装（SimulatedClock の活用）

ライセンス / 著作権
------------------
（ライセンス情報をここに記載してください。省略している場合はリポジトリの LICENSE を参照してください。）

問い合わせ
----------
問題報告や質問はリポジトリの Issues を利用してください。