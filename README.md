# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（ライブラリ実装の抜粋）。  
このリポジトリはデータ取得・ETL、ファクター計算、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ定義などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の責務を分離したモジュール群で構成される日本株自動売買基盤です。

- Data 層（J-Quants API クライアント、ニュース収集、DuckDB スキーマ、ETL パイプライン）
- Research 層（ファクター計算、特徴量探索・統計）
- Strategy 層（特徴量正規化、シグナル生成）
- Execution 層（発注・約定・ポジション管理用テーブル等の定義、発注ロジックは別途実装）

設計上のポイント：
- DuckDB を永続 DB として使用（in-memory も可能）
- J-Quants API のレート制御・リトライ・トークン自動更新を考慮
- ETL は差分更新・バックフィルを行い、DB への保存は冪等（ON CONFLICT）で実装
- ルックアヘッドバイアスを防ぐため、各処理は target_date 時点の情報のみを使用

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（ページネーション、リトライ、トークンリフレッシュ、保存ユーティリティ）
  - save_daily_quotes / save_financial_statements / save_market_calendar 等の DuckDB への保存関数
- data/schema.py
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）の初期化（init_schema）
- data/pipeline.py
  - 日次 ETL（run_daily_etl）／個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- data/news_collector.py
  - RSS フィード収集・前処理・raw_news への保存・銘柄抽出・紐付け
  - SSRF 対策・gzipサイズチェック・XML パース安全化（defusedxml）等を実装
- data/calendar_management.py
  - 市場カレンダー管理・営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
- research/factor_research.py
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
- research/feature_exploration.py
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー等
- strategy/feature_engineering.py
  - raw ファクターを統合・正規化して features テーブルへ UPSERT（冪等）
- strategy/signal_generator.py
  - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを signals テーブルへ保存

その他ユーティリティ：
- data/stats.py: クロスセクション Z スコア正規化
- config.py: 環境変数読み込み・設定管理（.env 自動読み込み機能を持つ）

---

## セットアップ手順

前提：
- Python 3.10+（typing 機能を利用）
- DuckDB を利用（パッケージとしてインストール）

1. リポジトリをクローンして Python 仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要な依存パッケージをインストールします（例）。

   requirements.txt がない場合は最低限以下を入れてください：

   ```bash
   pip install duckdb defusedxml
   ```

   （実装では標準ライブラリを多用していますが、DuckDB および defusedxml は明示的に必要です。）

3. パッケージを editable インストール（任意）：

   ```bash
   pip install -e .
   ```

   pyproject.toml / setup.py があれば上記でローカル開発インストールできます。ない場合は import パスを通すか PYTHONPATH に src を追加してください：

   ```bash
   export PYTHONPATH=$(pwd)/src
   ```

4. 環境変数を設定します。プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（起動中に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすれば無効化可能）。

   必須環境変数（モジュールで _require() されるもの）：
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意（デフォルト値があるもの）：
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db

   .env の例（簡潔）:

   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（主要な操作例）

以下のコードは Python REPL やスクリプトから実行できます。必要に応じて logging.basicConfig(...) でログ出力を有効にしてください。

1. DuckDB スキーマの初期化

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" を指定するとインメモリ DB
   ```

2. 日次 ETL を実行（J-Quants から差分取得して保存）

   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定しなければ今日
   print(result.to_dict())
   ```

3. 特徴量（features）を構築（strategy 層）

   ```python
   from datetime import date
   from kabusys.strategy import build_features
   cnt = build_features(conn, target_date=date(2025, 1, 31))
   print(f"upserted features: {cnt}")
   ```

4. シグナル生成

   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   total_signals = generate_signals(conn, target_date=date(2025, 1, 31))
   print(f"signals generated: {total_signals}")
   ```

   重みや閾値をカスタマイズすることも可能です：

   ```python
   weights = {"momentum": 0.5, "value": 0.2, "volatility": 0.1, "liquidity": 0.1, "news": 0.1}
   total = generate_signals(conn, date(2025,1,31), threshold=0.65, weights=weights)
   ```

5. ニュース収集ジョブを走らせる（RSS 収集 → raw_news 保存 → 銘柄紐付け）

   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   known_codes = {"7203", "6758", "6502"}  # 既知の銘柄コードセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)  # {source_name: saved_count}
   ```

6. J-Quants から日次株価を直接取得して保存する（低レベル）

   ```python
   from kabusys.data import jquants_client as jq
   records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
   saved = jq.save_daily_quotes(conn, records)
   print(saved)
   ```

---

## 環境変数の自動読み込みについて

- config.py はプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` と `.env.local` を順に読み込みます。
- OS 環境変数 > .env.local > .env の優先順位で適用されます。
- 自動読み込みを無効にするには、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

（主なファイルだけ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      - 環境変数・設定管理（.env 自動読み込み）
    - data/
      - __init__.py
      - jquants_client.py             - J-Quants API クライアント & 保存ユーティリティ
      - news_collector.py             - RSS 収集・前処理・DB 保存
      - schema.py                     - DuckDB スキーマ定義・初期化 (init_schema)
      - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
      - stats.py                      - 統計ユーティリティ（zscore_normalize）
      - features.py                   - data 層向け feature 再エクスポート
      - calendar_management.py        - 市場カレンダー管理（営業日判定等）
      - audit.py                      - 監査ログ（signal_events / order_requests / executions 等）
    - research/
      - __init__.py
      - factor_research.py            - ファクター計算（momentum/volatility/value）
      - feature_exploration.py        - 将来リターン・IC・ファクターサマリ
    - strategy/
      - __init__.py
      - feature_engineering.py        - raw ファクター統合・Z スコア正規化 → features へ
      - signal_generator.py           - final_score 計算・BUY/SELL シグナル生成
    - execution/                       - 発注/実行層（パッケージプレースホルダ）
    - monitoring/                      - 監視・モニタリング関連（パッケージプレースホルダ）

---

## 実運用での注意点 / 推奨事項

- 機密情報（API トークン等）は .env ファイルや環境変数で管理し、リポジトリにコミットしないでください。
- J-Quants のレート制限・トークンポリシーを遵守してください（jquants_client にレート制御実装あり）。
- DuckDB ファイルはバックアップとアクセス制御を行ってください（データが重要な場合）。
- 本コードは発注レイヤ（実際の証券会社 API 送信）を含まないため、実発注を行う際はリスク管理・冪等性を十分に検討してください。
- KABUSYS_ENV を `paper_trading` にするなど、運用モードを分けてテスト／ペーパー／ライブを切り替えてください。

---

この README はコードベースの主要機能と利用方法の概要を示します。詳しい設計仕様はソースコード内の docstring（各モジュールの冒頭コメント）や同梱の設計ドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。