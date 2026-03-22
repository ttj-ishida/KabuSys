# KabuSys

日本株向けの自動売買 / データパイプライン / バックテスト基盤ライブラリです。  
このリポジトリはデータ取得（J‑Quants）、ETL、特徴量生成、シグナル生成、バックテストシミュレータまで一貫して扱えるよう設計されています。

主な設計方針：
- ルックアヘッドバイアス防止（時点ベースでのデータ使用、fetched_at の記録）
- 冪等性（DB への書き込みは ON CONFLICT 等で安全に）
- DuckDB を中心としたローカル分析／バックテスト環境
- 外部 API 呼び出しはクライアントモジュールに限定、実行層と研究層は分離

---

## 機能一覧

- データ取得
  - J‑Quants API クライアント（株価日足、財務データ、JPX カレンダー）
  - RSS ベースのニュース収集（SSRF 対策・gzip 制限・トラッキング除去）
- ETL パイプライン
  - 差分取得 / バックフィル / 品質チェック（差分ロジック、バックフィル設定）
- データ層（DuckDB）
  - 生データ（raw_*） → 整形済み（prices_daily, fundamentals） → feature / execution 層のスキーマ定義および初期化
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC・統計サマリ等のユーティリティ
- 戦略（strategy）
  - 特徴量エンジニアリング（build_features）
  - シグナル生成（generate_signals）: ファクター + AIスコア統合、BUY/SELL の判定ロジック
- バックテスト（backtest）
  - ポートフォリオシミュレータ（スリッページ・手数料モデルを実装）
  - バックテスト実行エンジン（run_backtest）
  - 評価メトリクス計算（CAGR, Sharpe, MaxDD, 勝率等）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- その他
  - 設定管理（環境変数読み込み・.env 自動読み込み）
  - ロギング設定に基づく挙動制御

---

## 要求環境 / 依存

- Python 3.10+
- 必須パッケージ（一例）
  - duckdb
  - defusedxml
- 標準ライブラリで多くを実装しているため、追加パッケージは限定的です。

（実際のパッケージはプロジェクトの pyproject.toml / requirements.txt を参照してください。）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repository-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 最低限：
     ```
     pip install duckdb defusedxml
     ```
   - 開発インストール（パッケージとして扱う場合）:
     ```
     pip install -e .
     ```

4. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を作成します。自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 最低限設定すべき環境変数（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 必須の環境変数はコード内 Settings プロパティで _require によりチェックされます（不足時は ValueError）。

5. DuckDB スキーマの初期化
   - Python REPL かスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # :memory: も可
     conn.close()
     ```

---

## 使い方（主要なワークフロー例）

以下は代表的な操作の使い方例です。各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取る設計です。

- J‑Quants からデータを取得して保存する（概念例）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # 取得
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  # 保存（冪等）
  saved = jq.save_daily_quotes(conn, records)
  conn.close()
  ```

- ETL（差分）ジョブの実行
  - パイプラインの個別関数（run_prices_etl など）を呼び出して差分取得 / 保存 / 品質チェックを実行できます。
  - 例（簡略）:
    ```python
    from kabusys.data.pipeline import run_prices_etl
    conn = init_schema("data/kabusys.duckdb")
    fetched, saved = run_prices_etl(conn, target_date=date.today())
    ```

- 特徴量作成（features テーブルの構築）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))
  ```

- シグナル生成（signals テーブルへ書き込み）
  ```python
  from kabusys.strategy import generate_signals
  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  ```

- バックテスト実行（CLI）
  - モジュールとして実行可能:
    ```
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2024-12-31 \
      --cash 10000000 \
      --db data/kabusys.duckdb
    ```
  - または Python API:
    ```python
    from kabusys.data.schema import init_schema
    from kabusys.backtest.engine import run_backtest

    conn = init_schema("data/kabusys.duckdb")
    result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
    # result.history / result.trades / result.metrics を確認
    ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
  ```

---

## 環境変数と自動読み込み

- 自動読み込み順序:
  1. OS 環境変数
  2. .env.local（存在すれば上書き）
  3. .env（存在すれば設定。ただし OS 環境変数は保護）
- 自動読み込みはプロジェクトルート（.git または pyproject.toml を検出）から行われます。
- 自動読み込みを無効化する:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 主要な設定キー（Settings クラスで参照）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN（必須）
  - SLACK_CHANNEL_ID（必須）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - KABUSYS_ENV ∈ {development, paper_trading, live}（デフォルト: development）
  - LOG_LEVEL ∈ {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J‑Quants API クライアント（取得・保存）
    - news_collector.py        — RSS ニュース収集 / 保存
    - pipeline.py              — ETL 差分処理のオーケストレーション
    - schema.py                — DuckDB スキーマ定義 / init_schema
    - stats.py                 — Zスコア等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py       — momentum / volatility / value の計算
    - feature_exploration.py   — 将来リターン / IC / サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py   — build_features（正規化・ユニバースフィルタ等）
    - signal_generator.py      — generate_signals（final_score 計算、BUY/SELL）
  - backtest/
    - __init__.py
    - engine.py                — run_backtest（バックテスト制御ループ）
    - simulator.py             — PortfolioSimulator（約定・時価評価）
    - metrics.py               — バックテスト評価指標計算
    - run.py                   — CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py                 — 将来拡張用の模擬時計
  - execution/                  — 発注 / execution 層（未実装ファイル群を含む可能性あり）
  - monitoring/                 — 監視/アラート関連（将来的なモジュール）
- pyproject.toml / setup.cfg 等（パッケージ管理）

---

## 開発メモ / 注意点

- DuckDB のスキーマは init_schema() で冪等に作成されます。既存 DB に対しては schema 初期化の影響を注意して実行してください。
- J‑Quants API はレート制限に注意（120 req/min）。クライアントは内部で RateLimiter とリトライを実装しています。
- ニュース収集は外部ネットワーク接続を伴うため、環境に応じたタイムアウトやリトライの制御を行ってください。
- シグナル生成・特徴量生成は target_date における時点データのみを使用する設計です（ルックアヘッド防止）。
- 本リポジトリのコードは研究用途と運用用途でモジュールを分離しているため、本番での発注（ライブ実行）は別途十分な検証とオペレーション制御が必要です。

---

## 貢献 / ライセンス

- 貢献の流れやライセンスは本リポジトリのルートにある CONTRIBUTING.md / LICENSE を参照してください（なければリポジトリ管理者へ問い合わせ）。

---

README は簡易ドキュメントです。モジュール単位の詳細な仕様（StrategyModel.md, DataPlatform.md, BacktestFramework.md 等）が別途ある想定ですので、実装や運用に際してはそれらの設計文書も参照してください。