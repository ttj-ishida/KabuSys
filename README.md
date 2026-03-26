# KabuSys

日本株向けの自動売買・リサーチ基盤ライブラリ。  
データ取得（J-Quants／RSS）、ファクター計算、特徴量作成、シグナル生成、ポートフォリオ構築、バックテストまでを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、以下の機能を段階的に実装することで「データ取得 → ファクター構築 → シグナル生成 → 注文サイジング → 約定（シミュレーション／実取引）」を実現するためのライブラリです。DuckDB を主なオンディスク DB として想定し、研究用途（research）と運用用途（engine/backtest）双方で利用できる設計になっています。

設計上のポイント:
- Look-ahead bias を避けるため、各処理は target_date 時点のデータのみを参照するようになっています。
- DuckDB を用いた ETL / 日次テーブル管理を前提とします。
- API クライアントはレート制限・リトライ・トークンリフレッシュ等を備えています。
- バックテストはメモリ上のシミュレータで再現性のあるロジックを実行します。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価日足・財務データ・上場銘柄情報・市場カレンダー）
  - RSS ニュース収集（記事前処理・銘柄抽出・DB保存）
- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - ファクター探索ユーティリティ（将来リターン計算・IC・統計サマリー）
- 特徴量・シグナル
  - 特徴量正規化・features テーブルへの保存（feature_engineering）
  - final_score に基づく BUY / SELL シグナル生成（signal_generator）
- ポートフォリオ構築
  - 候補選定、等重／スコア加重の重み計算、リスクベースのポジションサイズ算出
  - セクター集中制限・レジーム乗数適用
- バックテスト
  - 日次ループでの疑似約定（スリッページ・手数料モデル）・履歴記録
  - バックテスト用の in-memory DuckDB コピー / run_backtest の公開 API
  - メトリクス算出（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
- その他ユーティリティ
  - 環境変数管理（.env の自動読み込み、必須チェック）
  - News 抽出・前処理、SSRF 対策、XML 処理安全化

---

## セットアップ手順

必要条件
- Python 3.10 以上（PEP 604 の型合成表記 `X | Y` を使用）
- DuckDB を使うためネイティブ拡張が入る環境（pip でインストール可能）

推奨インストール手順（開発環境）:

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（例）
   requirements.txt がある場合:
   ```bash
   pip install -r requirements.txt
   ```
   代表的な依存:
   - duckdb
   - defusedxml

   あるいは開発モードでインストール:
   ```bash
   pip install -e .
   ```

4. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置できます。モジュール起動時に自動で読み込まれます（テストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   
   必須の環境変数（例）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
   - SLACK_CHANNEL_ID — Slack チャネル ID（必須）

   任意／デフォルト付き:
   - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env 読み込みを無効化
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

   例: `.env`
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DB スキーマ初期化（ヘルパー関数が提供されている想定）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   ※ schema 初期化関数は別ファイルに実装されている前提です（このコードベース内で参照されています）。

---

## 使い方（主要なユースケース）

以下は主要な操作のサンプルです。実行には DuckDB 接続（init_schema の戻り値）を用意してください。

- J-Quants から日足を取得して保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  saved = save_daily_quotes(conn, records)
  conn.close()
  ```

- RSS ニュース収集
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  conn.close()
  ```

- 特徴量構築（features テーブルへの書き込み）
  ```python
  from kabusys.strategy.feature_engineering import build_features
  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024,3,31))
  conn.close()
  ```

- シグナル生成（signals テーブルへの書き込み）
  ```python
  from kabusys.strategy.signal_generator import generate_signals
  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024,3,31), threshold=0.6)
  conn.close()
  ```

- バックテスト（CLI）
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --db data/kabusys.duckdb \
    --cash 10000000 \
    --allocation-method risk_based \
    --lot-size 100
  ```

- バックテスト（プログラム呼び出し）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  print(result.metrics)
  conn.close()
  ```

- 研究モジュール（例: IC 計算）
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_ic
  # DuckDB 接続を渡して calc_momentum 等で factor レコードを取得 -> calc_forward_returns と合わせて IC を算出
  ```

---

## 環境変数（要点）

必須 env:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション／設定:
- KABUSYS_ENV ∈ {development, paper_trading, live}（デフォルト development）
- LOG_LEVEL ∈ {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト INFO）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env 読み込みを抑止）

設定は .env / .env.local に記述可能。プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を自動検出して読み込みます。

---

## ディレクトリ構成（主なファイル群）

（パッケージルート: src/kabusys）

- __init__.py
- config.py — 環境変数管理・自動 .env 読み込み
- data/
  - jquants_client.py — J-Quants API クライアント、取得・保存ユーティリティ
  - news_collector.py — RSS 収集、記事前処理、DB 保存、銘柄抽出
  - (schema.py, calendar_management.py, stats.py などが想定され依存)
- research/
  - factor_research.py — momentum / volatility / value のファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- strategy/
  - feature_engineering.py — raw ファクターの正規化と features への保存
  - signal_generator.py — final_score 計算と signals への書き込み（BUY/SELL）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算（risk_based / equal / score）
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- backtest/
  - engine.py — バックテスト全体のループ、run_backtest の実装
  - simulator.py — 擬似約定・ポートフォリオ状態管理
  - metrics.py — バックテスト評価指標計算
  - run.py — CLI エントリポイント
  - clock.py — 将来用の模擬時計クラス
- portfolio/ __init__.py, strategy/ __init__.py, research/ __init__.py, backtest/ __init__.py — 主要 API のエクスポート

※ 上記はコードベースに含まれる主要モジュールを抜粋したものです。実際のリポジトリには追加ヘルパーや DB スキーマ定義ファイルが存在する想定です。

---

## 開発上の注意事項 / 補足

- 型注釈やコードから想定される Python バージョンは 3.10 以上です（X | Y の記法を使用）。
- DuckDB を利用するため、データ量に応じたメモリ設定やファイル管理を検討してください。
- J-Quants API はレート制限があるため、ETL ジョブではスロットリング・リトライ挙動が組み込まれています。大量取得時は注意してください。
- バックテストは「データの時間軸（fetched_at / report_date 等）」によるリークに注意してデータを準備してください（Look-ahead 対策が設計に反映されていますが、ETL 段階の運用ミスで未来データを混入させると結果が歪みます）。
- news_collector は RSS の XML パースで defusedxml を用いて安全性を確保しています。SSRF 対策・レスポンスサイズ上限などの防御を実装しています。

---

もし README に追加したい具体的な実行例（特定コマンド、CI の設定、schema.sql など）があれば教えてください。README をそれに合わせて拡張します。