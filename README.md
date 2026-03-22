# KabuSys

日本株向けの自動売買システム用ライブラリ（研究・データプラットフォーム・戦略・バックテストを含む）

このリポジトリは、J-Quants 等からの市場データ収集、特徴量生成、シグナル生成、バックテストおよびニュース収集までを含む一連のコンポーネントを提供します。実運用（kabuステーション API）や Slack 通知等と連携することを想定した設計になっています。

---

## 概要

主な目的は以下です。

- J-Quants API から株価・財務・市場カレンダー等を取得し DuckDB に保存する（ETL）
- 研究（research）で計算したファクタを正規化・合成して特徴量（features）を作成
- 特徴量と AI スコアなどを統合して売買シグナル（signals）を生成
- 日次シミュレーションによるバックテストを実行（擬似約定・スリッページ・手数料をモデル化）
- RSS からニュースを収集し銘柄紐付けを行う
- DuckDB スキーマ定義およびユーティリティ関数群を提供

設計上の特徴：
- ルックアヘッドバイアスに配慮（target_date 時点のデータのみ使用）
- DuckDB を主な永続化層として利用、スキーマ初期化は idempotent
- 冪等性（ON CONFLICT / トランザクション）を重視
- ネットワークリトライ / レート制限 / SSRF 対策などの実運用考慮

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・トークンリフレッシュ・レート制御・保存ユーティリティ）
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出（SSRF対策・gzip/サイズ制限）
  - pipeline: ETL パイプライン（差分取得・バックフィル・品質チェック）
  - schema: DuckDB スキーマ定義と init_schema(db_path)
  - stats: Z スコア正規化等の統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算 / IC（Spearman）計算 / ファクター統計サマリー
- strategy/
  - feature_engineering: 生ファクターの正規化・ユニバースフィルタ・features テーブルへの UPSERT
  - signal_generator: features と ai_scores を統合して final_score を算出し signals を作成（BUY/SELL）
- backtest/
  - engine: 日次ループでのバックテスト実行（データコピー→シミュレーション→シグナル生成）
  - simulator: PortfolioSimulator（擬似約定・スリッページ・手数料モデル）・DailySnapshot・TradeRecord
  - metrics: バックテスト評価指標（CAGR、Sharpe、MaxDrawdown、勝率、Payoff など）
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- execution/, monitoring/: （パッケージ公開用に __all__ 等が定義されています。実装は分割されている可能性があります）

---

## セットアップ手順

前提
- Python 3.10+（typing の | 型表記やその他構文を使用）
- Git クローン済みのプロジェクトルート（.git または pyproject.toml があると .env 自動ロードが有効になります）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-dir>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - pip install duckdb defusedxml
   - もしパッケージ化されていれば（pyproject / setup がある場合）:
     - pip install -e .

   （補足）実運用で Slack 等を使う場合は対応するクライアントを追加してください。

4. データベース初期化
   - Python REPL またはスクリプトで：
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()

   - メモリ DB を使う場合：
     conn = init_schema(":memory:")

5. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。
   - 必須の環境変数（Settings クラスによる）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード（execution 層利用時）
     - SLACK_BOT_TOKEN — Slack ボットトークン（通知利用時）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（通知利用時）
   - 任意（デフォルトあり）:
     - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
     - LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視等で使う SQLite パス（デフォルト: data/monitoring.db）

   例 `.env`（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方

以下は主要なユースケースの実行例です。

1) DuckDB スキーマの初期化（既に存在する場合はスキップされます）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

2) J-Quants からデータを差分取得して保存（ETL）
   - pipeline モジュールの関数を呼び出して差分取得を行います（例: run_prices_etl）
   - 例（概念）:
     ```python
     from datetime import date
     import duckdb
     from kabusys.data.schema import init_schema
     from kabusys.data.pipeline import run_prices_etl

     conn = init_schema("data/kabusys.duckdb")
     fetched, saved = run_prices_etl(conn, target_date=date.today())
     conn.close()
     ```

   注意: run_prices_etl は id_token 注入や date_from/backfill_days を指定できます。J-Quants のトークンは環境変数から取得されます。

3) 特徴量構築（features テーブルへの保存）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.strategy import build_features

   conn = init_schema("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2024, 1, 31))
   print("upserted features:", n)
   conn.close()
   ```

4) シグナル生成（signals テーブルへの書き込み）
   ```python
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.strategy import generate_signals

   conn = init_schema("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2024, 1, 31))
   print("signals written:", total)
   conn.close()
   ```

5) バックテスト（CLI 例）
   - 付属の CLI で簡単にバックテストが可能です（DuckDB に事前に prices_daily 等のデータが必要）。
   ```
   python -m kabusys.backtest.run \
     --start 2023-01-01 --end 2024-12-31 \
     --cash 10000000 --db data/kabusys.duckdb
   ```
   - オプション:
     - --slippage, --commission, --max-position-pct 等を指定可能

6) バックテストを Python API から呼び出す
   ```python
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.backtest.engine import run_backtest

   conn = init_schema("data/kabusys.duckdb")
   result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
   print(result.metrics)
   conn.close()
   ```

7) ニュース収集
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = init_schema("data/kabusys.duckdb")
   known_codes = {"7203", "6758", ...}  # 有効銘柄コードセット（抽出用）
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(res)
   conn.close()
   ```

補足:
- 多くの関数は DuckDB 接続を受け取り、target_date ベースで計算を行います。テストやバックテストでは ":memory:" を使ったインメモリ DB を利用できます。
- generate_signals / build_features は日付単位の置換（削除→挿入）で冪等性を保っています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント & 保存ユーティリティ
    - news_collector.py        — RSS 取得・前処理・DB保存・銘柄抽出
    - pipeline.py              — ETL パイプライン（差分、バックフィル、品質チェック）
    - schema.py                — DuckDB スキーマ定義 / init_schema / get_connection
    - stats.py                 — zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py       — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py   — features テーブル構築（正規化・ユニバースフィルタ）
    - signal_generator.py      — final_score 計算と signals 作成
  - backtest/
    - __init__.py
    - engine.py                — run_backtest（データコピー＋日次ループ）
    - simulator.py             — PortfolioSimulator（約定モデル・履歴記録）
    - metrics.py               — バックテスト評価指標
    - run.py                   — CLI エントリポイント
    - clock.py                 — SimulatedClock（将来拡張向け）
  - execution/                 — 発注・実行層（パッケージエクスポート用）
  - monitoring/                — 監視・通知（パッケージエクスポート用）

---

## 設計上の注意点 / 運用上のヒント

- 環境変数の自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動読み込みします。
  - test や CI で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB スキーマは init_schema() で初期化してください。既存スキーマがある場合は安全にスキップします。
- J-Quants API のレート制限（120 req/min）やリトライ挙動は jquants_client に組み込まれています。大量取得時は間隔に留意してください。
- ニュース取得は外部 RSS に依存するため、SSRF 対策・サイズ制限等を実装済みです。known_codes を用意して銘柄抽出を行うことを推奨します。
- 本リポジトリは研究およびペーパー取引から実運用（live）まで想定しています。KABUSYS_ENV を切り替えてログレベルや実行ポリシーを変える仕組みがあります。

---

## よくある質問（FAQ）

Q: Python の推奨バージョンは？
A: 3.10 以上を推奨します（コードで | 型表記や一部標準ライブラリ機能を使用）。

Q: どのテーブルが必須ですか？
A: バックテストや戦略生成には最低限 prices_daily、features、ai_scores、market_regime、market_calendar が必要です。schema.init_schema() で全テーブルを作成できます。

Q: 実際に発注できますか？
A: 現状は execution 層のインターフェースが分離されており、kabuステーション API 等の実装（認証・送信・レスポンス処理）を組み合わせて運用する必要があります。KABU_API_PASSWORD 等の設定は config で管理されます。

---

この README はコードベース（src/kabusys 以下）から抽出した情報を元に作成しています。詳細な挙動やパラメータ、設計仕様書（StrategyModel.md、DataPlatform.md、BacktestFramework.md 等）がリポジトリに含まれている場合はそちらも参照してください。必要に応じてサンプルスクリプトや CLI 拡張、requirements.txt の整備を追加することをおすすめします。