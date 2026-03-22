# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、ETL、ファクター計算、特徴量エンジニアリング、シグナル生成、バックテスト、ニュース収集、実行レイヤーの基礎機能を提供します。

---

## 主な目的（概要）

- J-Quants API 等から市場データ・財務データ・カレンダー・ニュースを取得して DuckDB に保存
- 研究環境（research）で計算した生ファクターを標準化し feature を作成
- 正規化済みファクターと AI スコアを統合して売買シグナルを生成
- シグナルに基づく擬似約定（バックテスト）とポートフォリオ評価
- RSS ベースのニュース収集・銘柄紐付け（raw_news / news_symbols）
- 冪等な DB 書き込み、レート制御・リトライ（API クライアント）、SSRF/サイズ制限などのセキュリティ対策

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（認証、自動リフレッシュ、ページネーション、レート制御、保存関数）
  - pipeline: 差分 ETL（バックフィル考慮）、品質チェック呼び出し用の仕組み
  - news_collector: RSS 取得・前処理・raw_news への冪等保存・銘柄抽出
  - schema: DuckDB のスキーマ初期化（init_schema）、接続取得
  - stats: z-score 正規化などの統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- strategy/
  - feature_engineering: 生ファクターを統合して features テーブルに保存（Zスコア正規化、ユニバースフィルタ）
  - signal_generator: features と ai_scores を使って final_score を算出し signals を生成（BUY/SELL）
- backtest/
  - engine: run_backtest（インメモリ DB にコピー→日次ループ→シミュレーション）
  - simulator: PortfolioSimulator（擬似約定、マーク・トゥ・マーケット、トレード記録）
  - metrics: バックテスト評価指標（CAGR、Sharpe、MaxDD、勝率等）
  - run: CLI エントリポイント（python -m kabusys.backtest.run ...）
- execution/: 発注/実行関連（骨格）
- config.py: .env の自動読み込み、必須環境変数チェック（settings オブジェクト）

---

## 必要条件 / 依存関係

- Python 3.10 以上（型注釈で | 演算子等を使用）
- パッケージ依存（抜粋）:
  - duckdb
  - defusedxml
- （ネットワークアクセスを行うため適切なネットワーク・認証設定が必要）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 開発インストール（プロジェクトに setup を用意している場合）
pip install -e .
```

---

## 環境変数（主な必須項目）

config.Settings で参照される主な環境変数：

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD（必須）: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN（必須）: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID（必須）: Slack チャンネル ID
- KABUSYS_ENV（任意）: "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL（任意）: "DEBUG","INFO",...（デフォルト: INFO）
- DUCKDB_PATH（任意）: デフォルトは data/kabusys.duckdb
- SQLITE_PATH（任意）: デフォルトは data/monitoring.db

自動で .env / .env.local をプロジェクトルートから読み込みます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローンしてワークツリーに移動
2. Python 仮想環境を作成・有効化して依存パッケージをインストール（上記参照）
3. .env を作成して必須環境変数を設定（.env.example を参考に作成）
4. DuckDB スキーマを初期化
   - Python REPL / スクリプト例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - またはインメモリでテスト:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema(":memory:")
     ```

---

## 使い方（代表的な操作例）

- バックテスト（CLI）
  DuckDB ファイルが初期化され、prices_daily / features / ai_scores / market_regime / market_calendar 等が準備済みである前提。
  ```bash
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --db data/kabusys.duckdb \
    --cash 10000000
  ```
  出力にバックテストの主要メトリクスが表示されます。

- DuckDB にスキーマを作成してバックテストを Python から呼ぶ例
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("data/kabusys.duckdb")  # 既に初期化済みなら get_connection でも可
  result = run_backtest(conn, start_date=date(2023,1,4), end_date=date(2023,12,29))
  print(result.metrics)
  conn.close()
  ```

- 特徴量構築（features 作成）
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024,1,10))
  print(f"upserted {n} features")
  conn.close()
  ```

- シグナル生成
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  count = generate_signals(conn, target_date=date(2024,1,10))
  print(f"signals generated: {count}")
  conn.close()
  ```

- ニュース収集（RSS）と保存
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes があれば銘柄抽出される（例: set of '7203','6758',...）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
  print(results)
  conn.close()
  ```

- J-Quants からのデータ取得（クライアント）
  - トークンは環境変数 JQUANTS_REFRESH_TOKEN から自動取得されます。
  - fetch / save 関数を組み合わせて差分 ETL を実行できます（pipeline モジュール参照）。

---

## 注意点 / 設計上のポイント

- ルックアヘッドバイアス防止: ファクター計算・シグナル生成は target_date 時点のデータのみを使用する方針です。
- 冪等性: raw / processed レイヤーへの保存は ON CONFLICT / DO UPDATE / DO NOTHING 等を利用して冪等性を担保しています。
- API クライアント: レート制御（120 req/min）とリトライ、401 時の自動トークンリフレッシュを実装しています。
- ニュース収集: SSRF 対策、受信サイズ制限、XML の安全パーサ使用（defusedxml）を行っています。
- DuckDB のスキーマは init_schema で一括作成できます。既に存在するテーブルはスキップされます。
- tests や CI 用の環境変数として KABUSYS_DISABLE_AUTO_ENV_LOAD を使うことで self auto-load を止められます。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
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
    - clock.py
    - run.py
  - execution/  (発注・実行層のモジュールが入る想定)
  - monitoring/ (監視・メトリクス用のモジュールが入る想定)
  - その他ユーティリティ・モジュール

各モジュールは README 内の「機能一覧」で説明した責務ごとに分離されています。

---

## 開発者向けメモ

- 型ヒントとロギングを多用しており、静的解析（mypy等）やログ確認がデバッグに有用です。
- DuckDB を使うためデータ I/O は比較的高速にローカルで完結します。大規模な ETL を行う際はメモリ使用とクエリ範囲に注意してください。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装で、軽量に保たれています。必要に応じて研究用ノートブック側で pandas 化して可視化する運用を推奨します。

---

この README はコードベースの主要機能と基本的な使い方をまとめたものです。より詳細な設計・仕様（StrategyModel.md、DataPlatform.md、BacktestFramework.md 等）が別途あれば合わせて参照してください。