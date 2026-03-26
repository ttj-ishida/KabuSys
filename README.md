KabuSys — 日本株自動売買フレームワーク
======================================

概要
----
KabuSys は日本株向けの自動売買（および研究/バックテスト）用ライブラリです。  
ファクター計算、特徴量エンジニアリング、シグナル生成、ポートフォリオ構築、バックテスト用シミュレータ、データ収集（J‑Quants / RSS）などの主要機能をモジュール単位で提供します。設計は「ルックアヘッドバイアス防止」「冪等性」「テスト容易性」を重視しています。

主な機能
--------
- データ取得 / ETL
  - J‑Quants API クライアント（株価日足・財務データ・マーケットカレンダー取得、保存機能）
  - RSS ニュース収集（前処理・記事ID生成・銘柄抽出・DB 保存）
- 研究用ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - ファクター探索・IC 計算・統計サマリー
- 特徴量エンジニアリング
  - 生ファクターの正規化（Z スコア）・ユニバースフィルタ・features テーブルへの書き込み
- シグナル生成
  - features と AI スコアを統合して final_score を算出、BUY / SELL シグナルを生成・保存
  - Bear レジーム抑制、エグジット（ストップロス／スコア低下）判定
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、リスクベース配分、セクターキャップ適用
  - 株数決定（単元丸め・aggregate cap）
- バックテスト
  - 擬似約定モデル（スリッページ・手数料・部分約定）
  - 日次スナップショット、トレード記録、各種評価指標（CAGR、Sharpe、MaxDD、勝率、Payoff）
  - CLI でのバックテスト実行
- 設定管理
  - 環境変数 / .env 自動読み込み（プロジェクトルート検出ベース）

要件（推奨）
-------------
- Python 3.10+
- 必要な主要ライブラリ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリ以外の依存はプロジェクトの pyproject.toml / requirements を参照してください）

セットアップ手順
----------------
1. リポジトリをクローン / プロジェクトルートへ移動
   - git clone ... && cd <repo>

2. 仮想環境を用意（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール
   - pip install -e .    # プロジェクト配布形態に依存。pyproject.toml がある想定

4. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml

5. 環境変数設定
   - プロジェクトルートに .env（および任意で .env.local）を作成すると自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

推奨 .env（最小例）
- JQUANTS_REFRESH_TOKEN=your_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=your_slack_bot_token
- SLACK_CHANNEL_ID=your_slack_channel_id
- DUCKDB_PATH=data/kabusys.duckdb      # 既定値
- SQLITE_PATH=data/monitoring.db       # 既定値
- KABUSYS_ENV=development              # 有効値: development / paper_trading / live
- LOG_LEVEL=INFO                       # 有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL

注意:
- 設定は Settings クラス経由で取得され、不足する必須変数は起動時に例外になります。
- KABUSYS_ENV の有効値は "development" / "paper_trading" / "live"（小文字）です。

基本的な使い方
--------------

プログラムから（例）
- DuckDB スキーマ初期化（プロジェクトの schema 初期化関数を使用）
  - from kabusys.data.schema import init_schema
  - conn = init_schema("path/to/kabusys.duckdb")

- 特徴量を作る（build_features）
  - from datetime import date
  - from kabusys.strategy import build_features
  - count = build_features(conn, target_date=date(2024, 1, 31))

- シグナル生成（generate_signals）
  - from kabusys.strategy import generate_signals
  - n = generate_signals(conn, target_date=date(2024, 1, 31))

- J‑Quants からデータ取得・保存（例）
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - recs = fetch_daily_quotes(date_from=..., date_to=...)
  - save_daily_quotes(conn, recs)

- RSS ニュース収集（例）
  - from kabusys.data.news_collector import run_news_collection
  - result = run_news_collection(conn, known_codes=set_of_codes)

バックテスト CLI
- 用法（例）
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2024-12-31 --db path/to/kabusys.duckdb
- 主なオプション
  - --start / --end : バックテスト期間（含む）
  - --cash : 初期資金（デフォルト 10_000_000）
  - --slippage / --commission : スリッページ率 / 手数料率
  - --allocation-method : equal | score | risk_based
  - --max-positions, --max-utilization, --risk-pct, --stop-loss-pct, --lot-size
  - --db : DuckDB ファイルパス（必須）

パッケージ公開 API（代表）
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date)
- kabusys.backtest.run_backtest(conn, start_date, end_date, ...)
- kabusys.data.jquants_client.*（fetch / save 系）
- kabusys.data.news_collector.run_news_collection(...)
- kabusys.portfolio.*（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）

自動 .env 読み込みの挙動
---------------------
- 実行時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に .env を自動ロードします。
- 読み込み優先順位: OS 環境 > .env.local > .env
- テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（抜粋）
-----------------------
- src/kabusys/
  - __init__.py                — パッケージ定義（エクスポート一覧）
  - config.py                  — 環境変数 / 設定管理（Settings）
  - data/
    - jquants_client.py        — J‑Quants API クライアント + DuckDB 保存処理
    - news_collector.py        — RSS 取得・記事前処理・DB 保存・銘柄抽出
    - (schema.py 等)          — DB スキーマ初期化（参照される想定）
  - research/
    - factor_research.py       — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py   — IC / forward returns / 統計サマリ
  - strategy/
    - feature_engineering.py   — ファクター正規化 → features テーブルへ
    - signal_generator.py      — final_score 計算と signals テーブルへの書き込み
  - portfolio/
    - portfolio_builder.py     — 候補選定、重み計算
    - position_sizing.py       — 株数算出・ラウンド処理・aggregate cap
    - risk_adjustment.py       — セクターキャップ、レジーム乗数
  - backtest/
    - engine.py                — バックテストループ、全体統合
    - simulator.py             — 模擬約定 / マークトゥマーケット / トレード記録
    - metrics.py               — バックテスト指標計算
    - run.py                   — CLI エントリポイント
    - clock.py                 — 将来向けの模擬時計（補助）
  - portfolio/、execution/、monitoring/ などの追加モジュール（実装に応じて展開）

設計上の注意点 / 補足
--------------------
- Look‑ahead バイアス防止: 各処理は target_date 時点の情報のみを用いる設計になっています（例: features 作成やシグナル生成）。
- 冪等性: DB への INSERT は可能な限り ON CONFLICT や日付単位の置換（DELETE → INSERT）で実装されています。
- エラー耐性: データ取得はリトライやレート制御、RSS は SSRF 対策・サイズ制限・XML 脆弱性対策を実装しています。
- テスト: 設定読み込みや外部アクセスは環境変数フラグやモックで制御可能な設計です。

貢献 / 開発
-----------
- 開発時は仮想環境を作成し、依存を明示的にインストールしてください。
- コードはモジュール単位でユニットテストしやすいよう純粋関数を多用しています（DB 参照は引数で渡す設計）。
- 新しい ETL あるいはデータソースを追加する際は、Look‑ahead と冪等性に注意してください。

ライセンス
----------
- （ここにプロジェクトのライセンスを明記してください。例: MIT）

以上。README に載せるべき追加情報（サンプル .env.example、CI / テスト実行方法、依存一覧など）があれば教えてください。必要に応じて追記します。