# KabuSys

日本株向けの自動売買／リサーチ用ライブラリセット。データ取得（J-Quants）、特徴量生成、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株アルゴリズム運用のためのコンポーネント群を提供します。主な目的は以下です。

- J-Quants API 等からのデータ取得と DuckDB へ格納（時系列・財務・カレンダー）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量正規化と features テーブルへの格納
- ファクター＋AIスコアを統合した売買シグナル生成（BUY/SELL）
- ポートフォリオ構築、サイジング、セクター制約、レジームに応じた資金配分
- バックテストエンジン（擬似約定、スリッページ・手数料モデル、メトリクス）
- ニュース収集と銘柄紐付け（RSS → raw_news / news_symbols）
- 環境変数管理（.env 自動ロードなど）

設計方針としては「研究コードと実運用コードの分離」「ルックアヘッドバイアスの排除」「DuckDB による軽量なデータ管理」「冪等性を意識した ETL/保存処理」が採用されています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ付き）
  - news_collector: RSS 収集・前処理・DB 保存（SSRF対策・サイズ制限・トラッキング除去）
- research/
  - factor_research: モメンタム・ボラティリティ・バリュー等のファクター計算（prices_daily, raw_financials ベース）
  - feature_exploration: 将来リターン計算、IC（Spearman）などの探索的解析ユーティリティ
- strategy/
  - feature_engineering: ファクターの正規化・ユニバースフィルタ・features テーブルへの UPSERT
  - signal_generator: features と ai_scores を統合して BUY/SELL シグナルを生成、signals テーブルへ書き込み
- portfolio/
  - portfolio_builder: 候補選定・重み計算（等金額、スコア加重）
  - position_sizing: 株数計算（risk_based / equal / score）、単元丸め、aggregate cap
  - risk_adjustment: セクター上限フィルタ、レジーム乗数計算
- backtest/
  - engine: バックテストの全体ループ（データの in-memory コピー、シミュレータ呼び出し、シグナル生成の連携）
  - simulator: 擬似約定、ポートフォリオ履歴管理、約定レコード生成
  - metrics: バックテスト評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff）
  - run: CLI エントリーポイント（python -m kabusys.backtest.run）
- config: .env 自動読み込み・環境変数アクセスラッパー（必須値チェック、環境 / ログレベル判定）

---

## 要件（推奨）

- Python 3.10+
- 必須パッケージ（主に）
  - duckdb
  - defusedxml
- 標準ライブラリのみで動作する部分も多いですが、実行環境では上記依存をインストールしてください。

例（pipenv / venv を使う）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージをeditableでインストールする場合（プロジェクトルートで）
pip install -e .
```

---

## 環境変数 / 設定

config.Settings で参照する主な環境変数（必須は README 内で明示）:

- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード（実行時必要なら）
  - SLACK_BOT_TOKEN — Slack 通知用（必要な機能を使う場合）
  - SLACK_CHANNEL_ID — Slack 通知先チャンネル
- 任意 / デフォルトあり:
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
  - LOG_LEVEL — "DEBUG" | "INFO" | ...
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を起点）にある `.env` / `.env.local` を自動で読み込みます。
- テスト等で自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローンしワークディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # requirements.txt がある場合
   # 主要依存の個別インストール
   pip install duckdb defusedxml
   ```

3. 環境変数を用意
   - プロジェクトルートに `.env` を作成（.env.example を参考に）
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     ```

4. DuckDB スキーマ初期化
   - コード中で `from kabusys.data.schema import init_schema` を使って DB を初期化する想定（schema モジュールはプロジェクト内に存在する前提）。
   - 例（Python REPL）:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema('data/kabusys.duckdb')
     # 必要なテーブルが作成される想定
     conn.close()
     ```

---

## 主要な使い方（例）

- バックテスト（CLI）
  ```bash
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --db data/kabusys.duckdb \
    --cash 10000000 \
    --allocation-method risk_based
  ```

- Python API（DuckDB 接続を使う例）
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import build_features, generate_signals
  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import init_schema

  conn = init_schema('data/kabusys.duckdb')

  # 1) 特徴量構築
  build_features(conn, target_date=date(2024, 1, 4))

  # 2) シグナル生成
  generate_signals(conn, target_date=date(2024, 1, 4))

  # 3) バックテスト（期間を指定）
  result = run_backtest(conn, start_date=date(2023, 1, 1), end_date=date(2023, 12, 31))
  print(result.metrics)
  conn.close()
  ```

- J-Quants データ取得・保存（ETL の一例）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema('data/kabusys.duckdb')
  quotes = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
  save_daily_quotes(conn, quotes)
  conn.close()
  ```

- ニュース収集
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema('data/kabusys.duckdb')
  known_codes = set(row[0] for row in conn.execute("SELECT code FROM stocks").fetchall())
  run_news_collection(conn, known_codes=known_codes)
  conn.close()
  ```

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys/ 配下の主要ファイルと役割の抜粋です。

- kabusys/
  - __init__.py — パッケージ定義（version, export）
  - config.py — 環境変数読み込み / Settings
  - data/
    - jquants_client.py — J-Quants API クライアント（取得 / 保存ユーティリティ）
    - news_collector.py — RSS 収集、前処理、raw_news / news_symbols 保存
    - (schema.py 等は DB スキーマ初期化用に存在する想定)
  - research/
    - factor_research.py — momentum / volatility / value の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - strategy/
    - feature_engineering.py — ファクター正規化と features テーブルへの書込
    - signal_generator.py — final_score 計算と signals 生成（BUY/SELL）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・aggregate cap
    - risk_adjustment.py — セクター制約、レジーム乗数
  - backtest/
    - engine.py — バックテストループ、in-memory コピー、サイジング連携
    - simulator.py — 擬似約定 / mark-to-market / トレード記録
    - metrics.py — バックテスト指標計算
    - run.py — CLI ラッパー
  - execution/ — 発注周りの実装（空の __init__.py が含まれている）
  - monitoring/ — 監視・通知関連（該当実装が追加される想定）

---

## 注意事項 / 運用上のポイント

- ルックアヘッドバイアス防止:
  - feature / signal の計算は target_date 時点で入手可能なデータのみを使用する設計です。バックテストでは DB に保存した「その時点で得られていたデータ」を使って再現性を確保してください。
- 冪等性:
  - 多くの保存処理（raw_prices / raw_financials / market_calendar / raw_news 等）は ON CONFLICT あるいは INSERT ... DO NOTHING を用い冪等化されています。
- レート制限 / リトライ:
  - J-Quants クライアントは 120 req/min のレート制御、指定ステータスに対する指数バックオフ、401 の自動トークン更新を実装しています。
- テスト / デバッグ:
  - config モジュールは自動で .env を読み込みます。テスト時に自動ロードを抑えたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 貢献 / 拡張案

- execution 層に実際の発注 API（kabuステーション等）実装を追加
- 銘柄毎の単元情報（lot size）を stocks マスタに保持し position_sizing を拡張
- 分足シミュレーション対応（SimulatedClock の拡張）
- モニタリング・アラート（Slack 通知等）の実装強化

---

必要であれば README に「schema の初期定義サンプル」「.env.example」のテンプレートや、より詳細な CLI 使用例（パラメータ説明）を追記できます。どの情報を追加しましょうか？