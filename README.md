# KabuSys

日本株向けの自動売買 / 研究パイプラインライブラリです。バックテスト、特徴量計算、シグナル生成、データ取得（J‑Quants）、ニュース収集などのモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引の研究・運用向けに設計されたモジュール群です。主な目的は次の通りです。

- DuckDB を用いたデータ管理とファクター計算
- 研究用ファクター生成（momentum, volatility, value 等）
- features / ai_scores を統合したシグナル生成（BUY / SELL）
- ポートフォリオ構築（候補選定・配分・サイジング・セクター制限）
- バックテストエンジン（擬似約定・履歴記録・評価指標）
- J‑Quants API クライアントによるデータ取得（株価・財務・カレンダー）
- RSS ベースのニュース収集と銘柄紐付け

設計方針として、ルックアヘッドバイアス対策・冪等処理・堅牢なエラーハンドリングを重視しています。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / 環境変数の自動読み込み（.env.local が .env を上書き）
  - 必須設定の抽出（settings オブジェクト経由）

- kabusys.data
  - J‑Quants クライアント（トークン自動リフレッシュ、リトライ、レート制限）
  - raw データの DuckDB への保存ユーティリティ
  - ニュース収集（RSS）・テキスト前処理・銘柄抽出

- kabusys.research
  - ファクター計算（momentum, volatility, value）
  - ファクター探索・IC 計算・統計サマリー

- kabusys.strategy
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals）

- kabusys.portfolio
  - 候補選定・配分（equal / score）・position sizing（risk_based 等）
  - セクター集中制限・レジーム乗数

- kabusys.backtest
  - バックテストエンジン（run_backtest）
  - ポートフォリオシミュレータ（擬似約定・スリッページ・手数料）
  - メトリクス計算（CAGR, Sharpe, MaxDD, Win rate 等）
  - CLI エントリポイント（python -m kabusys.backtest.run）

---

## セットアップ手順

1. リポジトリをクローン（またはプロジェクトを任意の場所に配置）

   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（推奨）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール

   このコードベースは少なくとも以下を必要とします（プロジェクトの pyproject/requirements を参照してください）。

   - duckdb
   - defusedxml

   例:

   ```bash
   pip install duckdb defusedxml
   # 追加で開発用依存があればインストール
   ```

4. パッケージを開発モードでインストール（任意）

   ```bash
   pip install -e .
   ```

5. 環境変数設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと、自動的に読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須／推奨）:

   - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境（development / paper_trading / live。デフォルト: development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）

   例 `.env`（プロジェクトルート）:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

6. DuckDB スキーマの初期化（スキーマ定義モジュールを使用）

   例:

   ```python
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

   ※ schema モジュールがプロジェクトに含まれている前提です。初期テーブル（prices_daily, raw_prices, raw_financials, features, signals, positions, ai_scores, market_regime, market_calendar, stocks, raw_news, news_symbols 等）を作成してください。

---

## 使い方

ここでは典型的なワークフローの例を示します。

1. データ収集（J‑Quants）と保存

   - J‑Quants から株価日足や財務データを取得し、DuckDB に保存します。
   - J‑Quants クライアント例:

     ```python
     from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
     from kabusys.data.schema import init_schema
     from datetime import date

     conn = init_schema('data/kabusys.duckdb')
     token = get_id_token()  # settings.jquants_refresh_token を参照して取得
     recs = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,12,31))
     save_daily_quotes(conn, recs)
     conn.close()
     ```

2. ニュース収集（RSS）

   - RSS を取得して raw_news / news_symbols に保存します。

     ```python
     from kabusys.data.news_collector import run_news_collection
     from kabusys.data.schema import init_schema

     conn = init_schema('data/kabusys.duckdb')
     known_codes = set()  # stocks テーブルからコードを読み込んで渡すのが推奨
     run_news_collection(conn, known_codes=known_codes)
     conn.close()
     ```

3. 特徴量構築

   - DuckDB コネクションと基準日を渡して features テーブルを作成します。

     ```python
     from kabusys.strategy.feature_engineering import build_features
     from kabusys.data.schema import init_schema
     from datetime import date

     conn = init_schema('data/kabusys.duckdb')
     build_features(conn, target_date=date(2024,1,31))
     conn.close()
     ```

4. シグナル生成

   - features と ai_scores を統合して signals テーブルを更新します。

     ```python
     from kabusys.strategy.signal_generator import generate_signals
     from kabusys.data.schema import init_schema
     from datetime import date

     conn = init_schema('data/kabusys.duckdb')
     generate_signals(conn, target_date=date(2024,1,31))
     conn.close()
     ```

5. バックテスト実行（CLI）

   - CLI でバックテストを実行できます（事前に DB を整備しておく必要あり）。

     ```bash
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
     ```

   - 主なオプション:
     - --slippage, --commission
     - --allocation-method (equal, score, risk_based)
     - --max-positions, --max-utilization, --max-position-pct
     - --risk-pct, --stop-loss-pct, --lot-size

   実行後、CAGR / Sharpe / Max Drawdown / Win rate / Payoff ratio / Total Trades が出力されます。

---

## 注意事項・運用上のポイント

- 環境ファイルの自動読み込み:
  - パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出して `.env` / `.env.local` を読み込みます。
  - 読み込み優先順位: OS 環境 > .env.local > .env
  - OS 環境変数を保護するため `.env.local` の上書きは OS 環境に設定されたキーを上書きしません（内部的に protected set を使用）。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを指定してください。live モードかどうかは settings.is_live で判定できます。

- Look-ahead バイアス対策:
  - features やシグナル生成は target_date 時点のデータに基づいて計算するように設計されています。
  - J‑Quants など外部データ取得では fetched_at（UTC）を記録して「いつそのデータを利用可能になったか」をトレースしてください。

- 冪等性:
  - 各種 DB 保存関数は ON CONFLICT を使った更新または DO NOTHING を使った重複排除を行っています。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン等）
  - config.py — 環境変数 / .env 読み込み / Settings
  - data/
    - jquants_client.py — J‑Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS 取得・前処理・DB 保存・銘柄抽出
    - (schema.py 等スキーマ定義を想定)
  - research/
    - factor_research.py — momentum / volatility / value の計算
    - feature_exploration.py — IC, 将来リターン, 統計サマリー
  - strategy/
    - feature_engineering.py — features の構築・正規化・保存
    - signal_generator.py — final_score 計算・BUY/SELL シグナル生成
  - portfolio/
    - portfolio_builder.py — 候補選定・配分重み（equal / score）
    - position_sizing.py — 株数計算（risk_based / equal / score）
    - risk_adjustment.py — セクター制限・レジーム乗数
  - backtest/
    - engine.py — バックテストの全体ループ
    - simulator.py — ポートフォリオ擬似約定・履歴管理
    - metrics.py — 評価指標計算
    - run.py — CLI エントリポイント
    - clock.py — 模擬時計（将来拡張用）
  - portfolio/ (パッケージ初期化で主要関数を再エクスポート)
  - research/, strategy/, backtest/ 等のパッケージ初期化ファイルあり

---

## 開発・拡張ポイント（参考）

- 単元情報（lot_size）を銘柄ごとに管理するマスタを導入するとより現実に近いサイジングが可能です（現在は全銘柄共通値）。
- price 欠損時のフォールバック（前日終値や取得原価）を position sizing / sector cap の評価に導入することで欠損による過小評価を改善できます。
- ニュース抽出の精度向上や AI スコアの導入による news コンポーネントの強化。
- 分足シミュレーションやリアルタイム実行（kabu API 実装）への拡張。

---

## 問い合わせ / コントリビュート

改善提案やバグ報告、Pull Request はリポジトリの Issue / PR にて受け付けてください。コーディング規約やテスト方針がある場合は CONTRIBUTING.md に従ってください。

---

以上が README.md の概要です。必要であれば、.env.example の雛形や DuckDB のスキーマ定義例、よくある運用手順（ETL スケジュール、cron / Airflow の例）を追加で作成します。どの情報を優先して追記しますか？