# KabuSys

日本株向けの自動売買 / 研究プラットフォーム。  
特徴量計算、シグナル生成、ポートフォリオ構築、バックテスト、データ収集（J-Quants / RSS）などをモジュール化したライブラリです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象としたアルゴリズムトレーディング基盤です。研究（ファクター計算・探索）から、特徴量作成、シグナル生成、ポートフォリオ構築、約定の擬似シミュレーション、バックテストまで一貫して扱える設計になっています。外部データは主に DuckDB に保存して扱い、J-Quants API や RSS ニュースからの取得処理を備えます。

設計方針の要点:
- ルックアヘッドバイアス回避のため、常に「その日時点で利用可能なデータ」のみを用いる
- DuckDB を用いたローカル DB 管理
- 各フェーズ（research / feature / strategy / portfolio / execution / backtest）が分離された純粋関数／モジュール設計
- 冪等な DB 書き込み（ON CONFLICT 等）と堅牢なエラーハンドリング

---

## 主な機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足、財務、上場銘柄情報、マーケットカレンダー）
  - RSS フィードからニュース収集（SSRF対策・トラッキング除去・記事ID生成）
  - DuckDB への冪等保存ユーティリティ

- 研究・特徴量
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量正規化（Zスコア）と features テーブル生成

- シグナル生成
  - features と AI スコアを統合して final_score を計算
  - BUY / SELL シグナル生成（閾値・ベア相場抑制・エグジット条件）

- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、リスクベース配分
  - セクター集中制限、レジームに応じた投下資金乗数

- 約定・バックテスト
  - 擬似約定を行う PortfolioSimulator（スリッページ・手数料モデル対応）
  - 日次モック実行ループを備えたバックテストエンジン
  - バックテスト評価指標（CAGR、Sharpe、MaxDrawdown、勝率、Payoff 等）

- ユーティリティ
  - 環境変数・設定管理（.env 自動読み込み、必須チェック）
  - RSS 前処理 / 銘柄コード抽出等

---

## セットアップ手順

以下はローカル環境での最小セットアップ例です。

前提:
- Python 3.9+ を推奨（コードは型ヒントに | を使っているため 3.10 推奨）
- Git が使えること

1. リポジトリをクローン（既にファイルがある場合は不要）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows (PowerShell)
   ```

3. 必要パッケージをインストール  
   最低限必要な外部依存:
   - duckdb
   - defusedxml

   例:
   ```
   pip install duckdb defusedxml
   ```

   ※ 実運用・開発で追加パッケージが必要な場合は requirements.txt を用意している想定で
   ```
   pip install -r requirements.txt
   ```

4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数の設定  
   プロジェクトルートの `.env` / `.env.local` を読み込みます（自動読み込み）。  
   必須な環境変数（主要なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - DUCKDB_PATH (省略可): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH (省略可): SQLite（monitoring 用、デフォルト: data/monitoring.db）
   - KABUSYS_ENV (省略可): development | paper_trading | live（デフォルト development）
   - LOG_LEVEL (省略可): DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   自動読み込みを無効化したい場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

6. DuckDB スキーマ初期化  
   プロジェクト内の schema 初期化関数を使います（実装済みのは data.schema.init_schema を参照）。
   例:
   ```py
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

---

## 使い方

ライブラリはモジュール単位で利用できます。ここでは代表的なコマンド・関数呼び出し例を示します。

- バックテスト CLI
  DuckDB に必要テーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）があることが前提です。

  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```

  主なオプション:
  - --slippage, --commission, --max-position-pct, --allocation-method (equal/score/risk_based) など

- Python API でバックテスト実行
  ```py
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(
      conn=conn,
      start_date=date(2023,1,1),
      end_date=date(2023,12,31),
      initial_cash=10_000_000,
  )
  conn.close()

  # 結果
  print(result.metrics)
  ```

- 特徴量構築（features テーブルへの書き込み）
  ```py
  from datetime import date
  import duckdb
  from kabusys.strategy.feature_engineering import build_features
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  count = build_features(conn, date(2024, 1, 31))
  print(f"upserted features: {count}")
  conn.close()
  ```

- シグナル生成
  ```py
  from datetime import date
  from kabusys.strategy.signal_generator import generate_signals
  conn = init_schema("data/kabusys.duckdb")
  n = generate_signals(conn, date(2024, 1, 31))
  print(f"generated signals: {n}")
  conn.close()
  ```

- ニュース収集（RSS）
  ```py
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
  print(results)
  conn.close()
  ```

- J-Quants からのデータ取得/保存（例）
  ```py
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  conn = init_schema("data/kabusys.duckdb")
  recs = fetch_daily_quotes(date_from=..., date_to=...)
  saved = save_daily_quotes(conn, recs)
  conn.close()
  ```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants API リフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL (任意): kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack Bot トークン（通知用）
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID（通知用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite path for monitoring（デフォルト data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

config.py はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に .env / .env.local を自動読み込みします。

---

## ディレクトリ構成（抜粋）

（主要ファイル・モジュールのツリー）

- src/kabusys/
  - __init__.py
  - config.py
  - backtest/
    - __init__.py
    - engine.py
    - metrics.py
    - simulator.py
    - clock.py
    - run.py  (CLI entry)
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - (schema.py, calendar_management.py などが参照される想定)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - execution/         (空パッケージ: 実際の発注実装を想定)
  - monitoring/        (監視・通知周りの実装想定)
  - (その他モジュール・サポートコード)

各モジュールの役割:
- data/* : 外部データ取得（J-Quants）、ニュース収集、DuckDB への保存
- research/* : 研究用ファクター計算・探索ユーティリティ
- strategy/* : 特徴量の作成、シグナル生成
- portfolio/* : 候補選定、配分、サイジング、リスク制御
- backtest/* : シミュレータ、バックテストエンジン、評価指標

---

## 開発・運用上の注意

- データの「取得日時 (fetched_at)」を記録し、ルックアヘッドバイアスを防止する設計になっています。バックテストでは過去に取得されたデータのみを利用するよう DB を準備してください。
- J-Quants API はレート制限があります（120 req/min）。jquants_client は固定間隔スロットリングとリトライを実装していますが、運用時は注意してください。
- news_collector は外部 RSS 取得時に SSRF 対策やレスポンスサイズ制限、XML の安全なパース（defusedxml）を行っています。
- production（live）運用時は KABUSYS_ENV を `live` に設定し、安全確認を徹底してください（実取引 API の扱いに注意）。

---

## ライセンス・貢献

（ここにライセンスやコントリビューションの方針を追記してください）

---

README に記載した内容はコードベースの現状機能に基づく概要です。さらに詳しい仕様（StrategyModel.md、PortfolioConstruction.md、BacktestFramework.md、DataPlatform.md 等）に準拠した設計ノートが別途存在する想定です。必要であれば、各機能の詳細ドキュメントや使用例を追加します。