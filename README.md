# KabuSys

KabuSys は日本株向けの自動売買 / 研究プラットフォームです。J-Quants などの外部データソースから市場データを取得して DuckDB に保存し、ファクター計算・特徴量合成、シグナル生成、バックテスト、ニュース収集などの機能を提供します。

主な設計思想：
- ルックアヘッドバイアスの回避（計算は target_date 時点の利用可能データのみ）
- DuckDB を中心としたローカル DB（開発・バックテストを想定）
- 冪等（idempotent）な DB 書き込み
- 外部 API 呼び出しは専用クライアントを通じて制御（レート制限 / リトライ / トークン自動刷新）

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（jquants_client）
  - 株価日足 / 財務データ / 市場カレンダーのフェッチと DuckDB への保存（冪等）
- ETL パイプライン（data.pipeline）
  - 差分取得、バックフィル、品質チェックのためのユーティリティ
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、記事保存、銘柄紐付け
- データスキーマ（data.schema）
  - DuckDB 用のスキーマ定義と初期化（raw / processed / feature / execution 層）
- 統計・ユーティリティ（data.stats）
  - Z スコア正規化など汎用統計処理
- 研究（research）
  - ファクター計算（momentum, volatility, value）
  - 将来リターンや IC（Information Coefficient）等の解析ユーティリティ
- 戦略（strategy）
  - 特徴量作成（feature_engineering.build_features）
  - シグナル生成（signal_generator.generate_signals）
- バックテスト（backtest）
  - ポートフォリオシミュレータ、エンジン、評価指標、CLI 実行
- ニュース・監視・実行層の基礎モジュール（news / execution / monitoring：一部実装・拡張前提）

---

## 必要要件（概略）

- Python 3.10+（コードは型注釈で Python 3.10 以上を想定）
- 主要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API / RSS 取得時）
- J-Quants API トークン等の環境変数

requirements.txt はプロジェクトに含めてください。最低限は次のパッケージをインストールしてください：
```
pip install duckdb defusedxml
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb defusedxml
   # または: pip install -r requirements.txt
   ```

2. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数例（最低限）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - DUCKDB_PATH — DuckDB ファイルパス（省略時: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（省略時: data/monitoring.db）
     - KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")
     - LOG_LEVEL — ログレベル ("DEBUG","INFO",...)
   - .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行います。

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN="your_refresh_token_here"
   KABU_API_PASSWORD="your_kabu_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   DUCKDB_PATH="data/kabusys.duckdb"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマの初期化
   - Python REPL またはスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   - ":memory:" を指定するとインメモリ DB が初期化されます（テストやバックテスト用）。

---

## 使い方（主要ワークフロー）

以下は代表的な操作例です。

1. データ取得 & 保存（J-Quants）
   - jquants_client.fetch_* でデータを取得し、save_* 関数で DuckDB に保存します。
   - 例（株価日足の差分取得・保存は pipeline.run_prices_etl を利用するのが簡単）:
   ```python
   from kabusys.data.pipeline import run_prices_etl
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   res = run_prices_etl(conn, target_date=date.today())
   print(res.to_dict())
   conn.close()
   ```

2. 特徴量作成（features テーブルへの UPSERT）
   ```python
   from kabusys.strategy import build_features
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   count = build_features(conn, target_date=date(2024, 1, 31))
   print(f"features upserted: {count}")
   conn.close()
   ```

3. シグナル生成（signals テーブルへ書き込み）
   ```python
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   num = generate_signals(conn, target_date=date(2024, 1, 31))
   print(f"signals written: {num}")
   conn.close()
   ```

4. バックテスト（CLI / API）
   - CLI:
     ```
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
     ```
   - API:
   ```python
   from kabusys.backtest.engine import run_backtest
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   result = run_backtest(conn, start_date=date(2023,1,4), end_date=date(2023,12,29))
   print(result.metrics)
   conn.close()
   ```

5. ニュース収集
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   # known_codes は銘柄抽出に使う銘柄コード集合（optional）
   stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
   print(stats)
   conn.close()
   ```

---

## 主要モジュールの説明（簡易）

- kabusys.config
  - .env 自動読込み（.env, .env.local）、環境変数ラッパー settings を提供。
  - 必須設定を _require() で検査するため、起動時に欠落があると例外が発生します。

- kabusys.data.jquants_client
  - API リクエストのレート制御、リトライ、トークン自動リフレッシュを実装。
  - fetch_* / save_* 関数でデータ取得→保存を行う。

- kabusys.data.schema
  - DuckDB の全テーブル DDL を定義し、init_schema() で一括作成します。

- kabusys.research.*
  - ファクター計算・解析ユーティリティ（バックテストや特徴量作成に利用）。

- kabusys.strategy.feature_engineering
  - 研究モジュールの生ファクターを取得し、ユニバースフィルタ・正規化・クリップを行い features テーブルへ保存。

- kabusys.strategy.signal_generator
  - features と ai_scores を統合し最終スコアを作成、BUY/SELL シグナルを生成して signals テーブルに保存。

- kabusys.backtest
  - PortfolioSimulator（擬似約定）、run_backtest（全体ループ）、メトリクス計算（CAGR, Sharpe 等）、CLI。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
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
    - __init__.py
  - monitoring/
    - (参照されるが個別実装に依存)

---

## 環境変数と自動ロードについて（補足）

- 自動ロード対象ファイルはプロジェクトルートの `.env` と `.env.local`（`.env.local` は `.env` より優先して上書き）。
- OS 環境変数は既定で保護され、.env による上書きは行われません（ただし .env.local は override=True の挙動で既定値を上書きしますが、OS のキーは protected として保護されます）。
- 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に有用）。

---

## 開発・貢献メモ

- DuckDB のスキーマや SQL 文はデータ整合性を重視してチェック制約（CHECK）や PRIMARY KEY を多用しています。DDL を変更する際は既存データの互換性に注意してください。
- J-Quants クライアントは rate-limit と retry を実装していますが、API の仕様変更やレスポンス形式変更に応じてパーサー側の処理を更新してください。
- ニュース収集は外部 RSS に依存するため、Fetch の失敗は個別ソース単位で扱います（フォールトトレラント設計）。
- テストを書く際は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して環境の副作用を抑制し、jquants_client や network をモックすることを推奨します。

---

必要に応じて README を補足（例: 詳しい .env.example、requirements.txt、CI 設定、デプロイ手順）します。どのセクションを詳しく書けばよいか教えてください。