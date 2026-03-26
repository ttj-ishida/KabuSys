# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリ（バックテスト含む）。

このリポジトリは以下を目的としています：
- DuckDB を用いた時系列データの ETL / 保持
- 量的ファクター計算・特徴量生成
- シグナル生成（BUY / SELL）
- ポートフォリオ構築・サイジング・リスク制御
- バックテスト実行（擬似約定・スリッページ・手数料モデル）
- ニュース収集（RSS）および記事と銘柄の紐付け
- J-Quants API 経由のデータ収集（OHLCV / 財務 / 市場カレンダー）

注：この README はソースコードを参照して作成しています。詳細な設計仕様（StrategyModel.md 等）は別途参照してください。

## 主な機能一覧

- data
  - J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - ニュース収集（RSS）と記事の正規化・DB保存
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量探索ユーティリティ（IC, forward returns 等）
- strategy
  - 特徴量正規化・features テーブル生成（build_features）
  - 最終スコア計算とシグナル生成（generate_signals）
- portfolio
  - 候補選定、重み計算（等金額 / スコア重み）
  - ポジションサイジング（等配分 / スコア / リスクベース）
  - セクター集中制限・レジーム乗数
- backtest
  - ポートフォリオシミュレータ（擬似約定・部分約定・手数料/スリッページ）
  - バックテストエンジン（全体ループ・トレード履歴保存）
  - メトリクス計算（CAGR, Sharpe, MaxDD, WinRate, Payoff 等）
  - CLI ランナー（python -m kabusys.backtest.run）
- monitoring / execution（骨組みあり、詳細は実装に依存）

## 必要要件（想定）

最低限の Python パッケージ（ソースで参照されているもの）：
- Python 3.10+
- duckdb
- defusedxml

標準ライブラリの urllib / datetime / logging 等を使用しています。実際に動かす際は pyproject.toml / requirements.txt を参照して依存を整えてください（本リポジトリのパッケージ化手順に従ってインストール可）。

## 環境変数（主要）

このプロジェクトは環境変数から設定を読み込みます。.env / .env.local をプロジェクトルートに置くと自動で読み込まれます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

最低限設定が必要な環境変数：
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）

任意 / デフォルトあり：
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

例（.env）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （開発時は pip install -e . でインストールできるようにする）

4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、環境変数をエクスポートしてください。
   - 自動ロードは .git または pyproject.toml でプロジェクトルートを検出して行われます。

5. DuckDB スキーマ初期化
   - コード中にある kabusys.data.schema.init_schema(path) を用いてスキーマを初期化してください。
   - 事前データ（prices_daily / raw_financials / market_calendar / stocks 等）を投入する必要があります（バックテストや signal 生成に必須）。

## 使い方

ここでは代表的な実行例を紹介します。

- バックテスト（CLI）

  必要なデータ（prices_daily, features, ai_scores, market_regime, market_calendar 等）が入った DuckDB ファイルを用意してください。

  実行例:
  - python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-29 \
      --cash 10000000 --db path/to/kabusys.duckdb \
      --allocation-method risk_based --lot-size 100

  主なオプション:
  - --start / --end: バックテスト期間（YYYY-MM-DD）
  - --db: DuckDB ファイルパス
  - --cash: 初期資金（円）
  - --slippage / --commission: スリッページ率・手数料率
  - --allocation-method: equal | score | risk_based

- プログラムからバックテストを呼ぶ

  Python で直接利用可能です。

  例:
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  conn = init_schema("path/to/kabusys.duckdb")
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  conn.close()

  戻り値は BacktestResult（history, trades, metrics）です。

- 特徴量構築（Feature Engineering）

  build_features(conn, target_date) を呼び出すと、
  research モジュールの生ファクターを統合して `features` テーブルへ UPSERT します。

  例:
  from kabusys.strategy import build_features
  build_features(conn, date(2024, 1, 4))

- シグナル生成

  generate_signals(conn, target_date, threshold=0.6, weights=None)
  が `signals` テーブルに BUY / SELL シグナルを書き込みます。

- J-Quants からデータ取得 / 保存

  fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar と
  それらを保存する save_daily_quotes / save_financial_statements / save_market_calendar が提供されています。
  認証は get_id_token() を介して行います（環境変数の refresh token を利用）。

- ニュース収集

  RSS フィードを取得して raw_news / news_symbols に保存する run_news_collection(conn, sources, known_codes) が提供されています。
  - URL のスキーム検証、SSRFチェック、gzip・サイズ上限等の安全対策を実施しています。

## .env 読み込みの挙動

- プロジェクトルート（このファイルの位置から見て .git または pyproject.toml のある親ディレクトリ）を自動検出し、`.env` を読み込みます。
- 読み込み順序: OS 環境 > .env.local > .env
- 自動読み込みを無効化する: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の形式は一般的な KEY=VALUE、export KEY=VALUE、クォート（'"/）やインラインコメントに対応します。

## 主要なディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py — 環境変数と設定の読み込み
- data/
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py — RSS ニュース収集と DB 保存
  - (schema.py, calendar_management.py 等は別ファイルでスキーマ / カレンダー取得を提供)
- research/
  - factor_research.py — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py — IC / forward returns / summary 等
- strategy/
  - feature_engineering.py — features テーブル構築
  - signal_generator.py — final score と signals テーブル作成
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・スケールダウン・単元丸め
  - risk_adjustment.py — セクター上限・レジーム乗数
- backtest/
  - engine.py — バックテストループ・データコピー・戦略連携
  - simulator.py — 擬似約定とポートフォリオ状態管理
  - metrics.py — バックテストメトリクス
  - run.py — CLI エントリポイント
  - clock.py — 将来拡張用の模擬時計
- portfolio/、execution/、monitoring/ — 実稼働用のエントリ（骨組み）

（実際のリポジトリには data/schema.py や monitoring など追加ファイルがある想定です）

## 開発上の注意点・設計上の留意点

- ルックアヘッドバイアス防止のため、特徴量・シグナル生成は target_date 時点の「当時利用可能なデータ」を前提として設計されています。バックテストで利用するデータを投入する際は、過去時点で利用可能だったデータのみを用いること。
- J-Quants クライアントはレート制限（120 req/min）とリトライロジックを内蔵しています。トークンリフレッシュ領域は安全に作られていますが、API 利用時はレートとコストに注意してください。
- news_collector は外部 URL を扱うため SSRF 対策、受信サイズ制限、defusedxml による XML 安全化等の対策を施しています。
- バックテストでの約定は「SELL を先に、BUY を後に」処理します。SELL は現状全量クローズ（部分利確未対応）です。

## 参考 / 次のステップ

- DuckDB のスキーマを用意して実データをロードする（prices_daily / raw_financials / stocks / market_calendar 等）。
- research モジュールでの生ファクター計算→ feature_engineering.build_features の実行。
- generate_signals で signals を生成し、run_backtest で戦略の過去パフォーマンス確認。
- ニュース収集パイプラインを定期実行して raw_news を蓄積・銘柄紐付け。

---

ご要望があれば、
- 具体的な .env.example ファイルを生成する
- DuckDB スキーマ定義（schema.py）から初期化手順をドキュメント化する
- CI / テスト実行手順を README に追記する
などを追加で作成します。どれが必要か教えてください。