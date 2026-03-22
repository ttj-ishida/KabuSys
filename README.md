# KabuSys

日本株向けの自動売買（データ基盤・研究・戦略・バックテスト）ライブラリセットです。  
本リポジトリはデータ取得（J-Quants）、ETL、ファクター計算、特徴量作成、シグナル生成、バックテストシミュレータまでを含む一連の機能を提供します。

## 概要（Project overview）
- J-Quants API から株価・財務・カレンダーを取得して DuckDB に保存する ETL 基盤。
- 研究（research）モジュールでファクターを計算し、strategy 層で特徴量作成・シグナル生成を行う。
- news_collector による RSS ベースのニュース収集と銘柄抽出機能。
- バックテストエンジン（日次）とポートフォリオシミュレータ、評価指標計算を備える。
- 設計上の特徴：冪等性（ON CONFLICT）、ルックアヘッドバイアス対策（時間情報の管理）、API レート制御、SSRF 対策など。

## 主な機能（Features）
- データ取得
  - J-Quants から日足（OHLCV）、財務データ、取引カレンダーを取得・保存（rate limiter / retry）。
- ETL パイプライン
  - 差分更新、バックフィル、品質チェックを想定した ETL ユーティリティ。
- データベーススキーマ
  - DuckDB 用のスキーマ定義と初期化（raw / processed / feature / execution 層）。
- ニュース収集
  - RSS 取得、前処理、記事保存、銘柄コード抽出（SSRF対策、トラッキングパラメータ除去）。
- 研究・ファクター計算
  - Momentum / Volatility / Value 等のファクター計算、フォワードリターン・IC 計算、統計サマリ。
- 特徴量エンジニアリング
  - ファクターの統合、ユニバースフィルタ、Z スコア正規化、features テーブルへの保存。
- シグナル生成
  - features + ai_scores を統合して final_score を計算、BUY/SELL シグナル生成、Bear レジーム抑制、signals へ保存。
- バックテスト
  - インメモリ DuckDB にデータをコピーして日次ループでシミュレーション（スリッページ・手数料モデル）、結果と評価指標を出力。

## 動作環境（Requirements）
- Python 3.10 以上（型注釈に | を使用）
- 必要な外部パッケージ（例）
  - duckdb
  - defusedxml
- その他、ネットワークアクセス（J-Quants / RSS）が必要

※ 実際の requirements はプロジェクトの packaging/setup に合わせて調整してください。

## セットアップ手順（Setup）
1. Python 環境の用意（推奨: 仮想環境）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合は pip install -e .）

3. DuckDB スキーマ初期化（例: データディレクトリに DB を作る）
   - Python REPL やスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - もしくは :memory: でインメモリ DB を作成してテスト可能:
     ```python
     conn = init_schema(":memory:")
     ```

## 環境変数 / .env
このプロジェクトは .env ファイル（プロジェクトルート）または OS 環境変数を読み込みます。自動ロードはデフォルトで有効です（ルートに .git または pyproject.toml がある場合）。無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な環境変数（Settings）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（任意、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（監視用、デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）

例 .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## 使い方（Usage）
以下は代表的なワークフロー例です。

1) DB 初期化
- 既出: schema.init_schema() を呼び出して DuckDB スキーマを作成します。

2) データ取得（ETL）
- ETL パイプラインを利用して J-Quants からデータを取得し保存します（run_prices_etl 等）。
- 例（Python から）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_prices_etl

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  conn.close()
  ```

3) ニュース収集
- RSS を収集して raw_news に保存できます。
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 既知銘柄セット（任意）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  conn.close()
  ```

4) 特徴量作成
- DuckDB 接続と対象日を渡して features を作成します。
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  conn.close()
  ```

5) シグナル生成
- features と ai_scores を元に signals テーブルへ書き出します。
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  conn.close()
  ```

6) バックテスト実行（CLI）
- provided CLI entry point:
  ```
  python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2024-12-31 \
      --cash 10000000 --db data/kabusys.duckdb
  ```
- もしくは Python API:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()

  print(result.metrics)
  ```

注意:
- run_backtest() は本番 DB からバックテストに必要なテーブルを一部コピーしてインメモリ DB を作成します（本番テーブルは汚染しません）。
- シミュレーションは日次オープンで約定、終値で評価する設計です。

## 実装上の留意点（Design notes）
- 冪等性: DB への挿入は ON CONFLICT で重複更新を行う箇所が多く、再実行に対して安全性を高めています。
- ルックアヘッド対策: データには fetched_at / datetime を付与して、「いつデータが利用可能になったか」を追跡可能にしています。
- API リトライ/レート制御: J-Quants クライアントはレート制限とリトライ・トークンリフレッシュを実装。
- セキュリティ: RSS 取得は SSRF 対策（プライベートIP遮断/リダイレクト検査）を実装しています。
- research / data.stats は外部ライブラリを使わずに標準ライブラリで実装されているため、テストや移植性が高いです。

## ディレクトリ構成（Directory structure）
以下は主要ファイル・モジュールの一覧（src/kabusys 以下）と簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数管理、.env 自動ロード、Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（rate limiter, retry, save_* 関数）
    - news_collector.py
      - RSS 取得・前処理・DB 保存、銘柄抽出
    - pipeline.py
      - ETL ワークフローとユーティリティ（差分取得・バックフィル等）
    - schema.py
      - DuckDB スキーマ定義と init_schema()
    - stats.py
      - zscore_normalize などの統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value のファクター計算（prices_daily, raw_financials 使用）
    - feature_exploration.py
      - フォワードリターン計算、IC、統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features の構築（正規化、ユニバースフィルタ）
    - signal_generator.py
      - final_score 計算、BUY/SELL シグナル生成、signals へ保存
  - backtest/
    - __init__.py
    - engine.py
      - run_backtest（全体制御）
    - simulator.py
      - PortfolioSimulator（擬似約定・履歴管理）
    - metrics.py
      - バックテスト評価指標計算（CAGR, Sharpe, MaxDD, etc.）
    - run.py
      - CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py
      - SimulatedClock（将来拡張用）
  - execution/
    - __init__.py
    - （発注・kabu ステーション連携は別実装想定）

## その他
- ログ設定: 各モジュールは標準 logging を使用します。実行スクリプト側で logging.basicConfig を設定してください。
- テスト: ユニットテスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env ロードを抑制できます。
- 拡張: AI スコアや execution 層はインターフェースを想定した設計になっており、外部モデルやブローカー連携を実装できます。

---

この README はコードベースの主要点をまとめたものです。運用前に .env の設定や J-Quants の API 利用制限、kabu ステーションの接続要件、実際の取引に関する法的・リスク面の確認を必ず行ってください。必要であれば各モジュールごとの詳細なドキュメント（StrategyModel.md / DataPlatform.md 等）を別途作成してください。