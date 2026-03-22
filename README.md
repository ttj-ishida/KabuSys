# KabuSys

日本株向けの自動売買システム（ライブラリ）。  
データ収集（J-Quants、RSS 等）、データ整形（DuckDB スキーマ）、特徴量計算、シグナル生成、バックテストシミュレータを含みます。実運用向けの発注／実行層は別モジュール（execution）へ分離する設計です。

---

## 概要

KabuSys は以下のレイヤーで構成されたトレーディングプラットフォームのコア機能を提供します。

- Data Layer：J-Quants API クライアント、RSS ニュース収集、DuckDB スキーマと ETL パイプライン
- Feature Layer：研究で算出した raw ファクターの正規化・保存（features テーブル）
- Strategy Layer：特徴量と AI スコアを統合して売買シグナルを生成
- Backtest：擬似約定・ポートフォリオシミュレーション・メトリクス計算
- Research：ファクター計算・因果・IC などの分析ユーティリティ
- Execution（骨格）：実際の発注ロジックは別モジュールへ連携可能

設計上のポイント：
- ルックアヘッドバイアス回避（target_date 時点の情報のみ使用）
- DuckDB を用いたローカル DB（冪等な INSERT/UPSERT）
- API レート制御・リトライ・トークン自動更新（J-Quants クライアント）
- ニュース収集は SSRF 対策・サイズ制限・正規化を実装

---

## 主な機能一覧

- J-Quants API クライアント（fetch / save）
  - 日足（OHLCV）、財務データ、マーケットカレンダー取得
  - レートリミット、リトライ、ID トークン自動リフレッシュ対応
- ニュース収集（RSS）
  - URL 正規化、記事 ID 生成、テキスト前処理、銘柄抽出、DB 保存
- DuckDB スキーマ定義 / 初期化
  - raw / processed / feature / execution レイヤーのテーブル定義
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ、features テーブル UPSERT）
- シグナル生成（final_score 計算、Bear レジーム抑制、BUY/SELL 生成）
- バックテストフレームワーク
  - PortfolioSimulator（擬似約定、スリッページ、手数料）
  - run_backtest（DBからデータをコピーして日次シミュレーション）
  - メトリクス計算（CAGR, Sharpe, MaxDD, WinRate, Payoff 等）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- ユーティリティ（統計関数、日付/カレンダー処理 等）

---

## セットアップ手順

前提
- Python >= 3.10
- DuckDB（Python パッケージ）
- ネットワークアクセス（J-Quants API、RSS）

推奨手順（UNIX 系端末の例）:

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトで requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数を設定
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG|INFO|...)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)

   .env ファイル例 (.env または .env.local):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   注意: パッケージ起動時にプロジェクトルートの `.env` / `.env.local` を自動読み込みします。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB スキーマ初期化
   ```
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```
   またはアプリケーションコードから `init_schema` を呼び出してください。

---

## 使い方（代表的な操作）

以下は主要機能の簡単な使用例です。実際はアプリケーション側でラッパーやジョブスケジューラを使って呼び出します。

- DuckDB 接続の取得 / スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")  # 初回のみ
  # または既存 DB へ接続:
  # conn = get_connection("data/kabusys.duckdb")
  ```

- J-Quants から日足を取得して保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  rows = fetch_daily_quotes(date_from=..., date_to=...)
  saved = save_daily_quotes(conn, rows)
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # known_codes は銘柄抽出に使う有効コード集合（任意）
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set_of_codes)
  ```

- 特徴量作成（feature_engineering）
  ```python
  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, target_date=date(2024, 1, 31))
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
  ```

- バックテスト（CLI）
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```

- バックテスト（プログラムから）
  ```python
  from kabusys.backtest.engine import run_backtest
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  # result.history / result.trades / result.metrics を参照
  ```

- 研究ユーティリティ（IC, forward returns 等）
  ```python
  from kabusys.research import calc_forward_returns, calc_ic, factor_summary
  fwd = calc_forward_returns(conn, target_date)
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

---

## 重要な設定（環境変数）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション連携用パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルトは http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知用 Slack 設定（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default data/monitoring.db）
- KABUSYS_ENV — 実行環境（development, paper_trading, live）
- LOG_LEVEL — ログレベル
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動読み込みを無効にする

設定は .env または環境変数で提供してください。Settings クラス（kabusys.config）からアクセスできます。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - schema.py
    - stats.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - backtest/
    - __init__.py
    - engine.py
    - simulator.py
    - metrics.py
    - run.py
    - clock.py
  - execution/
    - __init__.py  (発注層は別実装/連携を想定)
  - monitoring/ (パッケージ想定：README の監視・メトリクス用途に使用)

各モジュールの役割は上の「主な機能一覧」を参照してください。

---

## 開発・運用上の注意

- 型アノテーションや構文は Python 3.10+ を想定しています。
- DuckDB のバージョンや SQL 機能（ON CONFLICT, RETURNING 等）に依存するため、互換性に注意してください。
- J-Quants の API レートリミット (120 req/min) を厳守するため内部でスロットリングを行います。大量取得時は時間を要します。
- ニュースの RSS 取得は SSRF/サイズ攻撃対策を入れていますが、public RSS 以外を指定する場合は注意してください。
- 本リポジトリには execution 層が最小構成または空の骨格として用意されています。実資金での運用時は十分なテストとリスク管理を実装してください。

---

必要であれば、README にサンプル .env.example、より詳しい ETL / 運用手順、デプロイ（スケジューラ／コンテナ化）やテスト方法を追記します。どの部分を詳しく書いてほしいか教えてください。