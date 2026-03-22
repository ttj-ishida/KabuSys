# KabuSys

日本株向けの自動売買システム（ライブラリ）です。データ収集（J-Quants / RSS）、ETL、特徴量生成、シグナル生成、バックテスト、および発注/実行レイヤーの骨組みを提供します。

主な設計方針は以下です。
- ルックアヘッドバイアスを避ける（target_date 時点の情報のみを使用）
- DuckDB を中心としたデータレイヤ（冪等保存・トランザクション）
- 外部 API 呼び出しに対してレート制御・リトライ・トークン自動更新を実装
- 研究（research）コードと本番ロジックを分離

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足 / 財務 / 市場カレンダー）
  - RSS ベースのニュース収集（XML パースの保護、SSRF 対策、トラッキング除去）
  - DuckDB への冪等保存（ON CONFLICT を使用）
  - データ品質チェック用のパイプライン（ETL の差分取得・バックフィル）

- データスキーマ管理
  - DuckDB のスキーマ初期化 `kabusys.data.schema.init_schema`

- 研究・特徴量
  - ファクター計算: momentum / volatility / value など（research/factor_research）
  - クロスセクション Z スコア正規化等（data.stats）
  - 特徴量合成と features テーブルへの保存（strategy/feature_engineering）

- シグナル生成
  - features と ai_scores を統合して final_score を算出し BUY/SELL シグナル生成（strategy/signal_generator）
  - Bear レジーム判定、ストップロス等のエグジット判定を実装

- バックテストフレームワーク
  - PortfolioSimulator（擬似約定、スリッページ、手数料）
  - run_backtest: 本番 DB をコピーして日次ループでシミュレーション
  - バックテストメトリクス（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio）

- ニュース処理
  - RSS 取得・前処理・raw_news 保存・銘柄抽出・news_symbols 保存

- 構成・設定
  - 環境変数読み込み（.env / .env.local 自動読み込み、プロジェクトルート検出）
  - settings オブジェクト経由で設定参照（kabusys.config.settings）

---

## セットアップ手順（開発環境）

以下はローカルで動かすための最低限の手順例です。

1. リポジトリをクローン / 取得
2. Python 仮想環境を作成・有効化
   - 例（Unix/macOS）:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
3. 依存パッケージをインストール
   - 必須: duckdb, defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - （プロジェクトに requirements.txt がある場合はそちらを利用してください）

4. 環境変数を設定（.env）
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（※CWD ではなくソースファイルの位置からプロジェクトルートを探索）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
     - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
     - SLACK_BOT_TOKEN (必須) — Slack 通知用（使用する場合）
     - SLACK_CHANNEL_ID (必須) — Slack 通知用
     - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH (任意) — デフォルト: data/monitoring.db
     - KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - 自動読み込みを無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - メモリ DB を使う場合は `":memory:"` を指定できます。

---

## 使い方（代表的コマンド / API）

- バックテスト CLI
  - モジュール実行でバックテストが可能です（DB は事前にデータを準備してください）。
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 \
    --db data/kabusys.duckdb
  ```
  - 出力に CAGR、Sharpe、Max Drawdown、勝率、ペイオフレシオなどが表示されます。

- スキーマ初期化（スクリプト）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # 必要に応じて conn を使った処理...
  conn.close()
  ```

- データETL（株価差分取得の例）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_prices_etl

  conn = init_schema("data/kabusys.duckdb")  # 既に初期化済みなら get_connection
  # run_prices_etl の戻り値は (fetched_count, saved_count)
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  conn.close()
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  conn.close()
  ```

- 特徴量構築 / シグナル生成（DuckDB 接続を渡して実行）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features, generate_signals

  conn = init_schema("data/kabusys.duckdb")
  d = date(2024, 1, 31)
  n = build_features(conn, d)            # features テーブルに書き込む
  s = generate_signals(conn, d)          # signals テーブルに書き込む
  conn.close()
  ```

- バックテストを Python API から呼ぶ
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("data/kabusys.duckdb")
  res = run_backtest(conn, start_date=date(2023,1,4), end_date=date(2023,12,29))
  conn.close()
  # res.history / res.trades / res.metrics を参照
  ```

---

## .env の書き方（例）

プロジェクトルートに `.env.example` を置き、必要なキーを設定して `.env` を作成してください（下は例）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

- 値にスペースや特殊文字が含まれる場合はクォート可能です。
- .env.local は .env の上書き（override=True）としてロードされます。
- OS 環境変数は保護され、.env によって上書きされません（原則）。

---

## ディレクトリ構成

これはリポジトリ上の主要なモジュール構造（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント
    - news_collector.py      — RSS ニュース収集
    - pipeline.py            — ETL パイプライン
    - schema.py              — DuckDB スキーマ定義・初期化
    - stats.py               — 統計ユーティリティ（zscore 等）
  - research/
    - __init__.py
    - factor_research.py     — momentum/volatility/value 等の算出
    - feature_exploration.py — IC・forward return・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成・正規化
    - signal_generator.py    — final_score 計算・シグナル生成
  - backtest/
    - __init__.py
    - engine.py              — run_backtest の実装
    - simulator.py           — PortfolioSimulator（擬似約定）
    - metrics.py             — 評価指標計算
    - run.py                 — CLI エントリポイント
    - clock.py
  - execution/                — 発注/実行関連（パッケージ初期化のみ）
  - monitoring/               — 監視系モジュール（未実装/拡張箇所）

---

## 注意事項・運用上のヒント

- データの「ルックアヘッド」を防ぐため、すべての計算は target_date 時点の情報のみを使う設計になっています。ETL 時や外部API取得のタイムスタンプ（fetched_at）も管理しています。
- J-Quants API に対してはレート制御（120 req/min）・指数バックオフ・トークン自動更新を実装しています。大量取得時は間隔やページネーションに注意してください。
- DuckDB スキーマの初期化は冪等です。production DB に適用する場合はバックアップを推奨します。
- このリポジトリは発注周り（実際のブローカー接続）を安全に運用するための追加実装（認証・鍵管理・エラー処理・ロギング等）が別途必要です。live モードでの実行は十分なレビューと監査の後に行ってください。
- テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にすると .env 自動ロードを無効化できます。

---

もし README に追加したいトピック（セットアップの自動化、CI、コンテナ化、具体的な ETL スケジュール例、サンプル .env.example ファイルなど）があれば教えてください。必要に応じて追記やテンプレート作成を行います。