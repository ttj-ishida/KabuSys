# KabuSys

日本株向け自動売買・研究プラットフォーム（KabuSys）のコードベース README（日本語）

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム取引・研究・バックテストを行うための内部ライブラリ群です。  
主な目的は以下：

- データ取得（J-Quants、RSS ニュース等）と DuckDB への格納
- 研究用ファクター計算・特徴量生成
- シグナル生成（AI スコアを含む統合スコアリング）
- ポートフォリオ構築（銘柄選定・配分・リスク調整・サイジング）
- バックテストフレームワーク（擬似約定・メトリクス算出）
- ニュース収集（RSS）と銘柄紐付け

コードはモジュール化され、研究（research）／データ（data）／戦略（strategy）／ポートフォリオ（portfolio）／バックテスト（backtest）等の責務に分離されています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（認証、自動リフレッシュ、ページネーション、レート制御、保存用関数）
  - raw_prices / raw_financials / market_calendar 等への保存ユーティリティ
- data/news_collector.py
  - RSS フィード取得、XML 安全パース、記事正規化、raw_news 保存、銘柄抽出・news_symbols 保存
  - SSRF 対策・サイズ制限・トラッキングパラメータ除去
- research/factor_research.py
  - Momentum / Volatility / Value / Liquidity 等のファクター計算（DuckDB を直接参照）
- research/feature_exploration.py
  - 将来リターン計算、IC（Spearman）、ファクター統計サマリ等
- strategy/feature_engineering.py
  - 研究で算出した生ファクターを正規化・クリップして features テーブルへ UPSERT
- strategy/signal_generator.py
  - features + ai_scores を統合して final_score を算出し BUY/SELL シグナルを signals テーブルに保存
  - Bear レジーム抑制やエグジットルール（ストップロスなど）を実装
- portfolio/
  - portfolio_builder.py：候補選定・配分重み（等配分 / スコア加重）
  - position_sizing.py：株数計算（risk_based / equal / score）・単元丸め・aggregate cap
  - risk_adjustment.py：セクター上限適用・レジーム乗数
- backtest/
  - engine.py：バックテスト全体ループ（データコピー・注文生成・ポートフォリオ管理）
  - simulator.py：擬似約定・ポートフォリオ状態管理・履歴・約定記録
  - metrics.py：CAGR / Sharpe / MaxDD / WinRate / Payoff 等の計算
  - run.py：CLI からバックテストを実行するエントリポイント

---

## 要件（推奨）

- Python 3.10+
- DuckDB（Python パッケージ）
- defusedxml（ニュースパーシングの安全化）
- 標準ライブラリ以外の依存はソース中で参照されるパッケージを確認してください（例: duckdb, defusedxml）。

インストール例（仮）:
```bash
python -m pip install duckdb defusedxml
```

（実際は packaging / requirements ファイルを参照してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt  # もし用意されている場合
   ```
3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb defusedxml
   ```
4. 環境変数（または .env）を準備  
   config モジュールは自動でプロジェクトルート（.git または pyproject.toml のある場所）から `.env` と `.env.local` を読み込みます（優先度: OS 環境 > .env.local > .env）。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（config.Settings より）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意（デフォルトあり）:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
   - DUCKDB_PATH — デフォルト data/kabusys.duckdb
   - SQLITE_PATH — デフォルト data/monitoring.db

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_pwd
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
5. DB スキーマ初期化  
   コード内では `kabusys.data.schema.init_schema(path)` が参照されています（schema モジュールによりテーブルが初期化されます）。初期化関数を呼び出して DuckDB ファイルを作成してください。
   例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

---

## 使い方

以下は代表的な実行フロー例と API の呼び方です。

- バックテスト（CLI）
  ```bash
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb \
    --allocation-method risk_based --lot-size 100
  ```
  run.py は結果を標準出力にメトリクスを表示します。

- バックテスト（プログラムから）
  ```python
  import duckdb
  from kabusys.backtest.engine import run_backtest

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  # result.history, result.trades, result.metrics を利用
  conn.close()
  ```

- 特徴量生成（features テーブルへ UPSERT）
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy.feature_engineering import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  ```

- シグナル生成（signals テーブルへ）
  ```python
  from kabusys.strategy.signal_generator import generate_signals
  generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
  ```

- J-Quants からのデータ取得・保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token

  token = get_id_token()
  recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, recs)
  ```

- ニュース収集（RSS）と保存
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set_of_codes)
  ```

注意点：
- 多くのモジュールは DuckDB 接続を受け取り、テーブル（prices_daily / features / ai_scores / market_regime / positions / signals 等）を前提としています。バックテストは本番 DB を直接更新しないために内部でインメモリ接続にコピーして実行します（engine._build_backtest_conn）。
- signal_generator は Bear レジームでは BUY を抑制する等の戦略ルールを実装しています。

---

## 自動環境変数読み込みの挙動（重要）

- config.py はプロジェクトルートを .git または pyproject.toml で検出し、そこで `.env` と `.env.local` を自動読み込みします。
- 読み込み順と優先度:
  1. OS 環境変数（既存値は保護）
  2. .env.local（override=True、OS 環境を保護）
  3. .env（override=False）
- 自動読み込み無効化:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すれば自動ロードを無効化します（テスト用途等）。

---

## 期待されるデータベースの主なテーブル（抜粋）

- raw_prices, prices_daily
- raw_financials
- features
- ai_scores
- signals
- positions
- market_regime
- market_calendar
- stocks
- raw_news, news_symbols

（schema の詳細は `kabusys.data.schema` を参照してください）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）
```
src/
  kabusys/
    __init__.py
    config.py
    data/
      jquants_client.py
      news_collector.py
      ... (schema, calendar_management など想定)
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    strategy/
      feature_engineering.py
      signal_generator.py
      __init__.py
    portfolio/
      portfolio_builder.py
      risk_adjustment.py
      position_sizing.py
      __init__.py
    backtest/
      engine.py
      simulator.py
      metrics.py
      run.py
      clock.py
      __init__.py
    execution/
      __init__.py
    monitoring/
      (監視関連モジュール — 実装に依存)
    portfolio/
      ...
```

---

## 開発・貢献に関するメモ

- ログレベルは環境変数 `LOG_LEVEL` で制御します（デフォルト INFO）。
- 実戦運用時は `KABUSYS_ENV=paper_trading` や `live` に設定して挙動を切り替えます（config.Settings.is_paper / is_live で判定）。
- 研究用関数群はバックテストのルックアヘッドを防ぐため、必ず target_date 時点までのデータのみを利用するよう設計されています。
- ニュース収集は外部ネットワークを扱うため SSRF / XML Bomb / 大容量レスポンス対策を多数実装しています。変更時はセキュリティ面のレビューを強く推奨します。

---

この README はコードの現状（ソーススニペット）に基づく概要です。具体的な運用手順・依存関係や schema の詳細はプロジェクト内のドキュメント（例: DataPlatform.md, StrategyModel.md, PortfolioConstruction.md, BacktestFramework.md）や `kabusys.data.schema` を合わせて参照してください。