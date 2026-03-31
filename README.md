# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
主に以下を提供します。

- J-Quants API からのデータ取得と DuckDB への ETL パイプライン
- ニュースの NLP（OpenAI を利用したセンチメント評価）と銘柄ごとのスコアリング
- 市場レジーム判定（ETF の MA とマクロニュースを組み合わせた判定）
- ファクター計算・特徴量解析（リサーチ用ユーティリティ）
- データ品質チェック、マーケットカレンダー管理、監査ログ（監査テーブル初期化）等の各種ユーティリティ

この README ではプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys はバックテスト／研究／運用パイプラインのために設計されたモジュール化ライブラリです。  
主な設計方針：

- Look-ahead バイアスを避ける（date 引数ベースで時間参照）
- DuckDB をデータストアとして使用し、SQL と Python を組み合わせて処理
- 外部 API 呼び出し（J-Quants / OpenAI）にはリトライやレート制御を備える
- ETL と品質チェックは分離し、部分失敗でも処理を継続できるようにする
- 監査ログは冪等で管理しトレーサビリティを確保する

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / .env.local / OS 環境変数から設定を自動読み込み（プロジェクトルート検出）
  - 設定オブジェクト `settings` により各種環境変数を安全に取得

- kabusys.data
  - jquants_client: J-Quants API クライアント（株価、財務、カレンダー取得、保存用ユーティリティ）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: マーケットカレンダー管理と営業日判定（is_trading_day, next_trading_day 等）
  - news_collector: RSS からのニュース収集（SSRF 対策、正規化、前処理）
  - audit: 監査ログテーブルの DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）

- kabusys.ai
  - news_nlp.score_news: raw_news をまとめて LLM（OpenAI）で解析し ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime へ保存

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（特徴量解析）

---

## セットアップ手順

以下は開発・運用環境の一般的なセットアップ例です。

1. Python 仮想環境を作成・有効化（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要なパッケージをインストール  
   （プロジェクトの requirements.txt がある場合はそれを使用してください。例として主要な依存を列挙します）
   ```bash
   pip install duckdb openai defusedxml
   ```
   - duckdb: データストア／SQL 実行
   - openai: LLM 呼び出し（gpt-4o-mini 等）
   - defusedxml: RSS パースの安全化
   - （必要に応じて他ライブラリを追加）

3. 開発インストール（パッケージがパッケージ化されている場合）
   ```bash
   pip install -e .
   ```

4. 環境変数設定  
   プロジェクトルート（.git や pyproject.toml があるディレクトリ）または実行ディレクトリに `.env` / `.env.local` を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。

   サンプル（.env）に含める主なキー：
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=your_slack_token
   SLACK_CHANNEL_ID=your_channel_id
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PID_FILE_PATH=data/execution.pid
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な例）

以下は Python から主要機能を利用する例です。実行前に DuckDB データベースに必要なテーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, prices_daily, market_regime など）が存在することを前提とします。

- DuckDB 接続を作成する例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  # target_date を明示して呼ぶと Look-ahead を防げます
  result = run_daily_etl(conn, target_date=None)  # None なら今日が対象
  print(result.to_dict())
  ```

- ニュースの AI スコアリング（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OpenAI API キーを環境変数 OPENAI_API_KEY に設定しておくか、
  # api_key 引数を直接渡します
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DB を初期化（init_audit_db / init_audit_schema）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで監査テーブル(signal_events, order_requests, executions 等) が作成されます
  ```

- 研究用ファクター計算例
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  # recs は各銘柄ごとの辞書リスト
  ```

注意点（運用上のヒント）
- OpenAI 呼び出しは API エラーや JSON パース失敗時にフェイルセーフとして許容する実装です（多くの場所で失敗時にスコアを 0.0 にフォールバックするなどの保護があります）。ただし API キーは必須です。
- J-Quants API はレート制限やトークン更新を含むため、ID トークンの管理は jquants_client 内部で行われます。`JQUANTS_REFRESH_TOKEN` を .env に設定してください。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）で行われます。テストなどで無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

以下はリポジトリ内の主要ファイル・ディレクトリ構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - ai/__init__.py

主要モジュールの役割：
- config.py: 環境変数の読み込み・検証（settings オブジェクト）
- data/jquants_client.py: J-Quants API 通信・DuckDB 保存ロジック
- data/pipeline.py: ETL の統合エントリポイント（run_daily_etl 等）
- data/quality.py: データ品質チェック（run_all_checks）
- ai/news_nlp.py: ニュースの LLM 解析と ai_scores への書き込み
- ai/regime_detector.py: 市場レジームのスコアリング
- research/*: ファクター・特徴量解析用ユーティリティ

---

## 追加情報 / 注意事項

- セキュリティ:
  - news_collector は SSRF 対策・応答サイズ制限・XML パーサの安全化を行っていますが、運用環境ではさらにネットワーク制御（プロキシや IP フィルタ）を行うことを推奨します。
- テスト:
  - OpenAI 呼び出しやネットワーク IO 部分は、ユニットテストでモックしやすいように内部関数が分離されています（例: _call_openai_api の差し替えなど）。
- ログ:
  - settings.log_level でログレベルを制御できます。環境変数 `LOG_LEVEL` を設定してください。
- DuckDB:
  - デフォルトの DB パスは settings.duckdb_path により `data/kabusys.duckdb`（相対パス）です。必要に応じて .env で上書きしてください。

---

必要であれば README を実際のセットアップ手順に合わせて調整（依存関係の正確な記載、具体的な起動スクリプト例、CI 設定の追加等）します。どの部分を追加・詳述したいか教えてください。