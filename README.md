# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（研究・データ基盤・戦略・バックテストのコンポーネント群）。

本リポジトリは以下の責務を持つモジュール群で構成されています：
- データ取得・保存（J-Quants, RSS）
- ファクター計算（research）
- 特徴量エンジニアリング・シグナル生成（strategy）
- 発注・約定・ポジション管理（execution / schema）
- バックテストフレームワーク（backtest）
- ETL パイプライン（data.pipeline）

※ この README はソースコード (src/kabusys 以下) を基に作成しています。

---

## 概要

KabuSys は「データ取得 → 特徴量作成 → シグナル生成 → 発注（実運用 or シミュレーション）」というフローを想定した日本株自動売買システム向けライブラリです。DuckDB をデータストアとして使い、J-Quants API や RSS を取り込み、研究用のファクター計算・正規化、戦略シグナル生成、バックテストシミュレーションを提供します。

設計上のポイント：
- ルックアヘッドバイアス対策（取得時刻/fetched_at の記録、target_date ベースの計算）
- 冪等性（DB への保存は ON CONFLICT / UPSERT を使用）
- API レート制限・リトライ実装（J-Quants クライアント）
- ETL の差分更新／バックフィル機能

---

## 機能一覧

主な機能（モジュール別）：

- data/
  - jquants_client: J-Quants API クライアント（トークン更新、ページネーション、保存関数）
  - news_collector: RSS 取得・前処理・DB 保存（SSRF 対策、gzip・サイズ制限）
  - schema: DuckDB スキーマ定義・初期化（raw/processed/feature/execution 層）
  - pipeline: 日次差分 ETL（差分取得・品質チェックフレームワーク）
  - stats: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: momentum/volatility/value 等のファクター計算
  - feature_exploration: 将来リターン, IC, 統計サマリー
- strategy/
  - feature_engineering.build_features: ファクター正規化・features テーブル更新
  - signal_generator.generate_signals: features + ai_scores → BUY/SELL signals 作成
- backtest/
  - engine.run_backtest: DuckDB データをコピーして日次シミュレーションを実行
  - simulator.PortfolioSimulator: 約定処理・スリッページ／手数料モデル・マークトゥマーケット
  - metrics.calc_metrics: バックテスト評価指標（CAGR, Sharpe, MaxDD など）
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- config: 環境変数管理（.env 自動ロード、必須チェック）

---

## セットアップ手順

前提
- Python 3.10+（ソースに `|` 型ヒントを多用）
- Git, ネットワーク接続（J-Quants / RSS を使う場合）

1. リポジトリをクローンしてインストール（開発用）
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   # パッケージをローカル編集可能にインストールする場合:
   pip install -e .
   ```
   ※ requirements.txt 等がある場合はそちらを使用してください（本コード提供には含まれていません）。

2. 環境変数の設定
   プロジェクトルートの `.env` / `.env.local` が自動的に読み込まれます（ただしテスト時などに無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須となる環境変数（Settings 参照）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション等の API パスワード（実行時に使用）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   任意（デフォルト値あり）:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
   - SQLITE_PATH: デフォルト `data/monitoring.db`

   サンプル `.env`（プロジェクトルートに作成）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマ初期化
   Python REPL またはスクリプトからスキーマを作成します。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
   conn.close()
   ```

---

## 使い方（主要な操作例）

以下に主要なユースケースの実行例を示します。

1. バックテスト（CLI）
   DuckDB に必要なテーブル（prices_daily / features / ai_scores / market_regime / market_calendar）が事前にないと動作しません。
   ```bash
   python -m kabusys.backtest.run \
     --start 2023-01-01 --end 2023-12-31 \
     --cash 10000000 --db data/kabusys.duckdb
   ```

2. バックテスト（プログラム呼び出し）
   ```python
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.backtest.engine import run_backtest

   conn = init_schema("data/kabusys.duckdb")
   result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
   print(result.metrics)
   conn.close()
   ```

3. ETL: 株価差分取得（pipeline）
   J-Quants のトークンが設定された環境で：
   ```python
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_prices_etl

   conn = init_schema("data/kabusys.duckdb")
   # target_date は通常当日。backfill_days により前日分を再取得します。
   fetched, saved = run_prices_etl(conn, target_date=date.today())
   conn.close()
   ```

   その他：
   - jquants_client.fetch_daily_quotes / save_daily_quotes を直接呼んで取得→保存も可能。
   - run_news_collection(conn, sources, known_codes) で RSS 収集と銘柄紐付け。

4. 特徴量構築・シグナル生成（戦略）
   DuckDB コネクションを渡して実行します。
   ```python
   from datetime import date
   import duckdb
   from kabusys.strategy import build_features, generate_signals

   conn = duckdb.connect("data/kabusys.duckdb")
   # features の構築（target_date を指定）
   build_count = build_features(conn, target_date=date(2023,6,30))
   # シグナル生成（features / ai_scores / positions を参照）
   signal_count = generate_signals(conn, target_date=date(2023,6,30))
   conn.close()
   ```

5. ニュース収集（RSS）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = init_schema("data/kabusys.duckdb")
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
   conn.close()
   ```

注意点：
- J-Quants API はレート制限（120 req/min）や 401 のトークンリフレッシュ処理が組み込まれています。
- ETL の差分ロジックはデータの最終取得日を参照して取得範囲を決定します（pipeline モジュール参照）。
- `.env` 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                       # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント＋保存ユーティリティ
    - news_collector.py             # RSS 収集・前処理・保存
    - schema.py                     # DuckDB スキーマ定義・init_schema
    - pipeline.py                   # ETL パイプライン
    - stats.py                      # zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py            # momentum/volatility/value 計算
    - feature_exploration.py        # forward returns, IC, summary
  - strategy/
    - __init__.py
    - feature_engineering.py        # build_features
    - signal_generator.py           # generate_signals
  - backtest/
    - __init__.py
    - engine.py                     # run_backtest（全体ループ）
    - simulator.py                  # PortfolioSimulator
    - metrics.py                    # バックテスト評価指標
    - run.py                        # CLI エントリポイント
    - clock.py
  - execution/                       # 発注・実行関連（拡張ポイント）
    - __init__.py
  - monitoring/                      # 監視・メトリクス関連（未実装 / 拡張）
    - __init__.py

---

## 知っておくべきこと / ヒント

- type ヒントや union (|) を利用しているため Python 3.10 以降を推奨します。
- DuckDB のファイルパスはデフォルトで `data/kabusys.duckdb`（Settings.duckdb_path）です。init_schema() で初期化してください。
- news_collector は外部ネットワークを使うため SSRF を意識した防御（リダイレクト検査、プライベートIP拒否）を実装しています。
- jquants_client は API の 401 を検出するとリフレッシュトークンから再取得を試みます。refresh token は環境変数で管理してください。
- テスト時には自動 .env ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` が便利です。
- 実運用（live）モードでは資金移動や実発注系の実装（execution 層）への統合が必要です。本リポジトリのコードは発注 API への直接依存を避ける設計になっています（抽象化されたレイヤーを介して統合してください）。

---

必要であれば README に以下を追加します：
- 詳細な .env.example（全キー一覧）
- CI / テスト実行方法（ユニットテスト例）
- 開発ルール（Lint / 型チェック）
- 実運用移行チェックリスト

どの項目を追加するか指定してください。