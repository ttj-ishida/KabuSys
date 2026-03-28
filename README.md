# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
データ収集（J-Quants）, ETL、データ品質チェック、ニュース収集／NLP（OpenAI 連携）、ファクター計算、監査ログ（発注→約定トレーサビリティ）などを提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（内部で date.today()/datetime.today() を安易に参照しない）
- DuckDB を中心としたローカルデータプラットフォーム
- API 呼び出しはリトライ・バックオフ・レート制御あり
- ETL / 保存は冪等（ON CONFLICT / DELETE→INSERT など）で安全に
- OpenAI 呼び出しは JSON Mode を利用し、パース失敗時はフェイルセーフで継続

---

## 機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルート検出、.env.local が .env を上書き）
  - 必須変数チェック（settings オブジェクト）

- データ収集 / ETL
  - J-Quants からの株価日足、財務データ、上場銘柄情報、JPX カレンダー取得（jquants_client）
  - 差分取得・バックフィル対応・ページネーション
  - run_daily_etl で日次ETL（calendar→prices→financials→品質チェック）

- データ品質チェック（quality）
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue オブジェクトで報告

- ニュース収集（news_collector）
  - RSS フィード取得（SSRF対策、gzip制限、トラッキング除去）
  - raw_news / news_symbols に冪等保存

- ニュースNLP / レジーム判定（ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）で評価し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA 乖離とマクロニュースセンチメントを合成して市場レジームを判定し market_regime に保存
  - API のリトライ・フェイルセーフ（失敗時は中立スコア等で継続）

- リサーチ / ファクター（research）
  - calc_momentum, calc_value, calc_volatility：prices_daily / raw_financials から各種ファクターを算出
  - feature_exploration: 将来リターン計算、IC（Spearman）、統計サマリー、rank、zscore_normalize（data.stats）

- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義、インデックス、初期化ユーティリティ
  - init_audit_db / init_audit_schema で DuckDB に監査スキーマを作成

- その他ユーティリティ
  - calendar_management：営業日判定・次/前営業日・calendar_update_job
  - data.stats：zscore_normalize 等

---

## セットアップ手順（開発 / 実行用）

前提
- Python 3.10+（typing 機能を利用）
- pip が使えること

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール  
   本リポジトリには requirements.txt が付属していない場合があります。最低限必要なもの：
   ```
   pip install duckdb openai defusedxml
   ```
   （実運用では HTTP クライアントやロギング周りの依存もプロジェクトに合わせて追加してください）

4. 環境変数（.env）を用意  
   プロジェクトルート（.git または pyproject.toml のある場所）に `.env` または `.env.local` を置くと自動でロードされます（自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必要な環境変数（代表例）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...
   - OPENAI_API_KEY=sk-...

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な例）

以下は Python からモジュールを呼ぶ例です。DuckDB 接続は duckdb.connect(...) を使用します。

- 設定を参照する
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- 日次 ETL を実行（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーが必要）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print("書き込み件数:", n_written)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター算出 / リサーチ
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  print(len(momentum))
  ```

注意点：
- OpenAI 呼び出しは外部 API のため、API キー必須・料金発生の可能性あり。API 呼び出しはリトライ・フェイルセーフ実装がされていますが、キーやレート制限に注意してください。
- settings の必須環境変数は _require 関数でチェックされ、未設定だと ValueError が上がります。

---

## 主要ディレクトリ構成（src/kabusys）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py (score_news エクスポート)
    - news_nlp.py (ニュースセンチメント -> ai_scores)
    - regime_detector.py (市場レジーム判定 -> market_regime)
  - data/
    - __init__.py
    - calendar_management.py (市場カレンダー、営業日判定)
    - pipeline.py (ETL 実行 run_daily_etl 等)
    - etl.py (ETLResult 再エクスポート)
    - jquants_client.py (J-Quants API クライアント、save_*/fetch_* 実装)
    - news_collector.py (RSS 収集・正規化・SSRF対策)
    - quality.py (データ品質チェック)
    - stats.py (zscore_normalize 等)
    - audit.py (監査ログスキーマ・初期化)
  - research/
    - __init__.py
    - factor_research.py (calc_momentum/calc_value/calc_volatility)
    - feature_exploration.py (calc_forward_returns, calc_ic, factor_summary, rank)
  - ai/regime_detector.py, ai/news_nlp.py と連携してマクロセンチメントや銘柄センチメントを算出

（ファイル名は一例。リポジトリ内の完全なファイルツリーに従ってください。）

---

## 実運用に関する補足・注意

- .env の自動ロードはプロジェクトルート検出に基づきます。テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- jquants_client は API レート制限（120 req/min）を意識した実装になっています。大量のページネーションや一斉フェッチ時は実行時間に注意してください。
- ETL・データ保存は冪等設計ですが、DB バージョン差異（DuckDB の特性）により SQL 文の挙動が変わる場合があります。DuckDB のバージョンは固定して運用することを推奨します。
- OpenAI 等外部 API の呼び出しは使用量・コストに直結します。バッチサイズやリトライ設定は設定定数で調整可能です。
- 監査ログは削除しない前提です（トレーサビリティ保持）。ディスク管理には注意してください。

---

## 開発・拡張ポイント

- news_collector に RSS ソースを追加してニュース収集を拡張可能
- jquants_client の保存先（DuckDB スキーマ）をプロジェクト要件に合わせて拡張可能
- strategy / execution / monitoring といったモジュールはパッケージ化済み（__all__ に含まれる）ため、独自戦略実装を追加してください

---

この README はコードベース（src/kabusys）を元に主要部分を抜粋・整理したものです。実行前に .env（または環境変数）を正しく設定し、DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, ai_scores, market_regime, など）を初期化してから使用してください。必要に応じてサンプルスキーマや migration スクリプトを用意してください。