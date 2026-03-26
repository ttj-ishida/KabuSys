KabuSys
=======

日本株向けの自動売買・リサーチ基盤ライブラリです。ファクター計算、特徴量生成、シグナル生成、ポートフォリオ構築、バックテスト、データ収集（J‑Quants / RSS）など、量的運用パイプラインに必要な主要コンポーネントを含みます。

主な目的
- 研究（factor research / feature engineering）とバックテストのための再現可能な処理フローを提供
- DuckDB を用いたローカルデータストアを前提とした ETL / analytics
- 本番の発注/監視層と分離した設計で、安全にロジックを検証できる

機能一覧
- データ取得 / 保存
  - J-Quants API クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info）
  - RSS ベースのニュース収集器（SSRF対策、記事正規化、銘柄抽出、DB保存）
  - DuckDB への冪等保存ユーティリティ
- リサーチ / ファクター計算
  - momentum / volatility / value 等のファクター計算（prices_daily / raw_financials を参照）
  - forward returns / IC（Spearman） / 統計サマリー等の解析ユーティリティ
  - z-score 正規化ユーティリティ連携
- 特徴量エンジニアリング
  - ファクター正規化、ユニバースフィルタ（株価・流動性）、features テーブルへの UPSERT（冪等）
- シグナル生成（strategy）
  - feature と AI スコアを統合し final_score を算出、BUY/SELL シグナルを features/ai_scores/positions を参照して生成
  - Bear レジーム抑制・ストップロス等のエグジットロジック
- ポートフォリオ構築
  - 候補選定（スコア順）、等配分 / スコア加重、リスクベースのポジションサイズ計算
  - セクター集中制限、レジーム乗数（投下資金の縮小）
- バックテストフレームワーク
  - run_backtest(): データの一部をインメモリ DuckDB にコピーして、シミュレータ（擬似約定、スリッページ、手数料）で日次ループを再現
  - 評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio 等）計算
  - CLI エントリーポイント（python -m kabusys.backtest.run）
- 設定管理
  - .env / 環境変数読み込み、自動ロード（プロジェクトルート検出）と必須変数チェック

動作環境・前提
- Python 3.10 以上（PEP 604 の型 | を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス: J‑Quants API / RSS フィードへ接続するための適切なネットワーク環境と API トークンが必要

セットアップ手順（開発環境向け）
1. リポジトリをクローン / 作業ディレクトリへ移動
   - 例: git clone <repo> && cd <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - UNIX/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があれば pip install -e . などを使用）

4. パッケージを編集可能モードでインストール（任意）
   - pip install -e .

環境変数 / .env
- 自動的にプロジェクトルート（.git または pyproject.toml を探索）内の .env, .env.local を読み込みます。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須の環境変数（アプリケーションで使用）
- JQUANTS_REFRESH_TOKEN : J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード（execution 層で使用）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（monitoring 等）
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意 / デフォルト設定
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

（例）.env
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

使い方（基本例）
- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 特徴量生成
  from datetime import date
  from kabusys.strategy.feature_engineering import build_features
  cnt = build_features(conn, target_date=date(2024, 1, 31))
  print(f"アップサートした銘柄数: {cnt}")

- シグナル生成
  from kabusys.strategy.signal_generator import generate_signals
  generate_signals(conn, target_date=date(2024, 1, 31))

- バックテスト（Python API）
  from datetime import date
  from kabusys.backtest.engine import run_backtest
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  print(result.metrics)

- バックテスト（CLI）
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --db data/kabusys.duckdb \
    --cash 10000000

- J‑Quants データ取得例
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=..., date_to=...)
  save_daily_quotes(conn, records)

- ニュース収集例
  from kabusys.data.news_collector import run_news_collection
  run_news_collection(conn, known_codes=set_of_codes)

注意事項 / 設計上のポイント
- ルックアヘッドバイアス対策: 特徴量・シグナルは target_date 時点のデータのみを使用する設計になっています（prices/financials の「日時の扱い」に注意）。
- DuckDB へのデータ挿入は基本的に冪等（ON CONFLICT / UPSERT）を意識しています。
- J‑Quants API はレート制限（120 req/min）とリトライ/トークンリフレッシュのロジックを実装しています。
- NewsCollector は SSRF 対策やサイズ制限、XML パースの安全策（defusedxml）を備えています。
- バックテストでは、本番 DB を直接汚染しないために必要データをインメモリの DuckDB にコピーして実行します。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - jquants_client.py       — J‑Quants API クライアント + DB保存
    - news_collector.py       — RSS ニュース収集・DB保存
    - (その他: schema.py 等が期待される)
  - research/
    - factor_research.py      — momentum / volatility / value 等のファクター計算
    - feature_exploration.py  — IC / forward returns / summary 等
  - strategy/
    - feature_engineering.py  — features テーブル作成（正規化等）
    - signal_generator.py     — final_score 計算・signals 生成
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・aggregate cap
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py               — バックテストループ（run_backtest）
    - simulator.py            — ポートフォリオシミュレータ（擬似約定）
    - metrics.py              — バックテスト評価指標計算
    - run.py                  — CLI エントリポイント
    - clock.py                — 模擬時計（将来拡張用）
  - execution/                 — 発注 / 実行層（実装は別途）
  - monitoring/               — 監視 / Slack 通知等（実装は別途）
  - portfolio/__init__.py
  - research/__init__.py
  - strategy/__init__.py
  - backtest/__init__.py

（注）上記はコードベースの主要モジュールを抜粋したものです。schema.py や data/calendar_management など、実行に必要な追加モジュールがプロジェクトに存在する前提です。

トラブルシューティング
- 環境変数未設定に対しては Settings クラスが ValueError を投げます。README の環境変数一覧を確認して .env を作成してください。
- Python の型表記（|）を使っているため、3.10 未満では SyntaxError になります。Python バージョンを確認してください。
- DuckDB テーブルが不足していると各処理で SQL エラーになります。init_schema 等でスキーマを作成・初期データ投入してください。

貢献 / 開発
- コードの追加・修正は機能単位のユニットテストを追加してください（DuckDB を使った統合テストが有用です）。
- 外部 API 呼び出し部分はモック可能なように設計されています（テスト時はネットワークアクセスを避けることを推奨）。

---

以上がこのコードベースの概要と使い方です。必要であれば、README に記載する具体的な .env.example、requirements.txt のサンプル、またはスキーマ初期化スクリプトの使用例を追記します。どの追加情報が必要か教えてください。