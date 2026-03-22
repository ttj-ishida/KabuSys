# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集、擬似約定シミュレーションなど、研究〜運用に必要な主要コンポーネントを提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「API レート制限・堅牢なリトライ」「DuckDB によるローカルデータ管理」です。

バージョン: 0.1.0

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（株価日足・財務・市場カレンダー）
  - raw / processed / feature / execution 層を持つ DuckDB スキーマ定義と初期化
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Z スコア正規化ユーティリティ
- 戦略（Strategy）
  - 特徴量作成（build_features）
  - シグナル生成（generate_signals）：features と ai_scores を統合して BUY / SELL を生成
- バックテスト（Backtest）
  - ポートフォリオシミュレータ（スリッページ・手数料モデル・約定ロジック）
  - 日次ループでのシミュレーション（run_backtest）
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio 等）
  - CLI エントリポイント: python -m kabusys.backtest.run
- ニュース（News）
  - RSS フィード収集（fetch_rss）と前処理（URL 正規化、テキスト正規化）
  - raw_news / news_symbols への冪等保存
  - SSRF / XML Bomb 等のセキュリティ対策（defusedxml / リダイレクト検査 / レスポンスサイズ制限）
- 設定管理
  - .env / 環境変数自動読み込み（プロジェクトルート判定）
  - 必須変数チェック（Settings）

---

## セットアップ手順

前提
- Python 3.10 以上（| 型アノテーション、match 等の利用を想定）
- Git（プロジェクトルート検出に使用されます）

1. リポジトリをクローン / 作業ディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell)
   ```

3. 必要パッケージをインストール
   - 主要依存: duckdb, defusedxml
   - 開発・追加依存はプロジェクトの pyproject.toml / requirements に合わせてインストールしてください。
   ```bash
   pip install duckdb defusedxml
   # またはプロジェクトルートに requirements.txt があれば
   # pip install -r requirements.txt
   ```

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（起動時）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（config.Settings が要求するもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - KABU_API_PASSWORD: kabu ステーション API パスワード（発注系を使う場合）
   - （任意）KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - （任意）LOG_LEVEL: DEBUG / INFO / ...（デフォルト: INFO）
   - データベースパス（デフォルトを利用する場合は設定不要）
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (監視用 DB, 例: data/monitoring.db)

   例 `.env`（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化
   - Python REPL かスクリプトから schema.init_schema を呼んで初回テーブル作成を行います（:memory: も可）。
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")  # data/ 配下は自動作成されます
   ```

---

## 使い方（主な例）

以下は主要なユースケースの最小例です。詳細は各モジュールの docstring を参照してください。

1. バックテスト（CLI）
   - 事前に DuckDB に prices_daily, features, ai_scores, market_regime, market_calendar などを用意してください。
   - 実行例:
     ```bash
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
     ```

2. スキーマ初期化（プログラム的に）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

3. J-Quants から日足を取得して保存（簡易例）
   ```python
   import duckdb
   from kabusys.data import jquants_client as jq
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   records = jq.fetch_daily_quotes(date_from=..., date_to=...)
   saved = jq.save_daily_quotes(conn, records)
   ```

4. ETL パイプライン（株価差分ETL）の呼び出し（プログラム）
   - pipeline.run_prices_etl 等の関数を使って差分取得・保存を行います。
   ```python
   from kabusys.data.pipeline import run_prices_etl
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   fetched, saved = run_prices_etl(conn, target_date=date.today())
   ```

5. 特徴量作成 + シグナル生成（DuckDB 接続が必要）
   ```python
   import duckdb
   from datetime import date
   from kabusys.strategy import build_features, generate_signals
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   d = date(2024, 1, 4)
   n_features = build_features(conn, d)
   n_signals = generate_signals(conn, d)  # signals テーブルに書き込まれる
   ```

6. ニュース収集の実行
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット（抽出用）
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   ```

---

## 環境変数 / 設定（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須 for execution) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知設定
- DUCKDB_PATH — DuckDB ファイルパス（既定 data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（既定 data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合に 1 を設定

注意: Settings クラスは必須環境変数が欠けていると ValueError を投げます。`.env.example` を参考に `.env` を用意してください（プロジェクトに合わせて作成）。

---

## ディレクトリ構成

以下は主要ファイル・モジュールの一覧（プロジェクトの src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + 保存ロジック
    - pipeline.py                   — ETL パイプライン
    - news_collector.py             — RSS ニュース収集・保存
    - schema.py                     — DuckDB スキーマ定義 / init_schema
    - stats.py                      — Z スコア等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py        — ファクター正規化・features 作成
    - signal_generator.py           — final_score 計算と BUY/SELL 生成
  - backtest/
    - __init__.py
    - engine.py                     — バックテストの全体ループ
    - simulator.py                  — 擬似約定・ポートフォリオ管理
    - metrics.py                    — バックテスト評価指標計算
    - clock.py                      — (将来用) 模擬時計
    - run.py                        — CLI エントリポイント（python -m ...）
  - execution/                      — 発注 / 実行層（空の __init__.py がある）
  - monitoring/                     — 監視系（placeholder）
  - backtest/ (上記)

各モジュールの docstring に設計意図・使用方法・注意点が詳細に書かれています。実運用では features / ai_scores / market_regime / market_calendar などの前処理データが揃っている必要があります。

---

## 開発メモ / 注意事項

- DuckDB を用いたスキーマは冪等（ON CONFLICT 操作や INSERT ... DO UPDATE）を意図しています。ETL は差分更新・バックフィル設計です。
- ニュース収集は RSS の XML を扱うため defusedxml を利用し、SSRF・Gzip Bomb 等に対して複数の安全対策を実装しています。
- J-Quants クライアントは固定間隔のレート制限（120 req/min）を守るためスロットリングとリトライを備えます。ID トークン自動リフレッシュが組み込まれています。
- 本コードベースは研究と運用の橋渡しを意識しており、「発注（execution）層」を切り離すことで本番口座への誤発注リスクを下げています。実運用で発注を有効化する場合は additional security / approval が必要です。
- `KABUSYS_ENV=live` 設定時は特に注意してください（実際の発注・Slack 通知など）。

---

必要であれば、README に例となる .env.example（実際のキー名と簡単な説明）、CI 用の起動手順、より詳細な ETL / Backtest のワークフロー図やサンプルデータ準備手順を追加します。どの情報を優先して追加しますか？