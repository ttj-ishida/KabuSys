# KabuSys

日本株自動売買システムのコアライブラリ（リサーチ / データプラットフォーム / 戦略 / バックテスト / 実行基盤の一部実装）。

このリポジトリは DuckDB をデータ層に用い、J-Quants API などからデータを取得して特徴量を生成、シグナルを作成し、バックテストや（将来的な）注文実行に繋げることを目的としています。

---

## プロジェクト概要

- データ取得（J-Quants） → 生データ保存（raw layer） → 整形（processed） → 特徴量作成（feature layer） → シグナル生成（strategy） → バックテスト（backtest）までのパイプラインを含みます。
- 主に以下の機能群を提供：
  - J-Quants API からの株価／財務／市場カレンダー取得（rate limiting / retry / token refresh 対応）
  - RSS ベースのニュース収集（SSRF 防御・正規化・銘柄抽出）
  - DuckDB スキーマ定義と初期化
  - ファクター計算（Momentum / Value / Volatility / Liquidity）
  - 特徴量正規化、features テーブルへの保存
  - シグナル生成ロジック（final_score、Bear レジーム判定、BUY/SELL 生成）
  - バックテストエンジン（擬似約定、ポートフォリオシミュレータ、メトリクス算出）
  - ETL パイプラインでの差分取得・品質チェック（パイプラインの入口実装）

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数の自動ロード（.env / .env.local）と設定取得（必須キーチェック）
- kabusys.data
  - jquants_client: J-Quants API クライアント、保存用ユーティリティ（raw_prices / raw_financials / market_calendar）
  - news_collector: RSS 取得、記事前処理、raw_news/news_symbols 保存
  - schema: DuckDB スキーマ定義 & init_schema()
  - pipeline: ETL ジョブ（差分取得・保存・品質チェックの入り口）
  - stats: 汎用統計関数（Z スコア正規化等）
- kabusys.research
  - factor_research: Momentum/Value/Volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー
- kabusys.strategy
  - feature_engineering.build_features: features テーブルの生成（正規化・フィルタ）
  - signal_generator.generate_signals: features + ai_scores から BUY/SELL シグナル作成
- kabusys.backtest
  - engine.run_backtest: 日次ループに基づくバックテスト実行
  - simulator.PortfolioSimulator: 擬似約定・ポートフォリオ管理
  - metrics.calc_metrics: バックテスト評価指標計算
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- kabusys.data.news_collector / jquants_client: 外部データ収集周りの堅牢性対策（SSRF, gzip bomb, XML 脆弱性, レート制限, retry）

---

## セットアップ手順

前提
- Python >= 3.10（PEP 604 の | 型などを使用）
- DuckDB（Python パッケージ）
- defusedxml（RSS パーシングの安全化）

推奨手順（UNIX 系端末例）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   ※他にロギングや標準ライブラリのみで動作しますが、用途に応じて追加パッケージを導入してください。

3. DuckDB の初期スキーマ作成（例）
   - Python REPL またはスクリプトで：
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()

4. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を置くと、kabusys.config が自動で読み込みます（パッケージインポート時）。
   - 最低限設定すべき環境変数（.env.example を参照して作成してください）：
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - （任意）KABUSYS_ENV = development|paper_trading|live
     - （任意）LOG_LEVEL = DEBUG|INFO|WARNING|ERROR|CRITICAL
     - DUCKDB_PATH（既定: data/kabusys.duckdb）
     - SQLITE_PATH（監視用デフォルト: data/monitoring.db）
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（基本例）

以下は代表的な利用フローの一例です。

1) DuckDB スキーマ初期化
- Python:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()

2) J-Quants からデータ取得 → 保存
- 例（株価を取得して保存）:
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  conn.close()

- get_id_token() が内部で refresh を行うため、JQUANTS_REFRESH_TOKEN を .env に設定してください。

3) ETL（差分取得）を使う（pipeline の run_prices_etl など）
- pipeline.run_prices_etl を呼ぶと差分計算／取得／保存が行えます（詳細は関数ドキュメント参照）。

4) 特徴量（features）作成
- build_features を呼んで指定日分の特徴量を生成し features テーブルへ保存します。
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024,1,31))
  conn.close()

5) シグナル生成
- generate_signals により signals テーブルに BUY/SELL を書き込みます。
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection
  from datetime import date
  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024,1,31))
  conn.close()

6) バックテスト（CLI）
- コマンド例:
  python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
- オプション: --cash / --slippage / --commission / --max-position-pct

7) ニュース収集（RSS）
- run_news_collection を使って RSS を取得し raw_news / news_symbols に保存します。
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
  conn.close()

備考:
- すべての DB 書き込みは基本的に冪等性を考慮して実装されています（ON CONFLICT 等）。
- J-Quants API 呼び出しはレートリミット・リトライ・401 トークンリフレッシュを備えています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント / 保存ロジック
    - news_collector.py          — RSS ニュース収集 / 保存
    - pipeline.py                — ETL パイプライン（差分取得等）
    - schema.py                  — DuckDB スキーマ定義 / init_schema
    - stats.py                   — 統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum/value/volatility）
    - feature_exploration.py     — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py     — features 作成・正規化・ユニバースフィルタ
    - signal_generator.py        — final_score 計算・BUY/SELL 生成
  - backtest/
    - __init__.py
    - engine.py                  — バックテストエンジン
    - simulator.py               — PortfolioSimulator（擬似約定）
    - metrics.py                 — バックテスト指標計算
    - run.py                     — CLI エントリポイント
    - clock.py                   — シミュレーション用時計（将来用途）
  - execution/                    — 発注/約定周り（パッケージ置き場）
  - monitoring/                   — 監視 / メトリクス（将来拡張）

---

## 開発／運用上の注意点

- Python 3.10 以上を想定しています（型記法／標準機能）。
- DuckDB のバージョン互換性に注意（特に Foreign Key / ON DELETE 挙動はコメントに記載）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- ニュース収集は外部ネットワークに依存するため、SSRF 対策やタイムアウト等の挙動を理解してから運用してください。
- AI スコアや実際の発注（kabu ステーション API 等）部分は本実装では抽象化/分離されています。実際の資金投入前にペーパーまたは十分なバックテストを推奨します。

---

## 参考：よく使う関数 / CLI

- DB 初期化:
  - from kabusys.data.schema import init_schema
  - init_schema("data/kabusys.duckdb")

- 特徴量作成:
  - from kabusys.strategy import build_features
  - build_features(conn, target_date)

- シグナル生成:
  - from kabusys.strategy import generate_signals
  - generate_signals(conn, target_date)

- バックテスト実行（CLI）:
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

---

もし README に追加したい内容（例: .env.example、requirements.txt、具体的なサンプルデータの用意方法、CI 設定など）があれば教えてください。必要に応じて追記・整形します。