# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリセットです。  
ETL・ニュース収集・NLP（LLM）によるニュースセンチメント、ファクター計算、監査ログ（発注トレース）など、システム構築に必要な主要機能をモジュール化しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象としたデータパイプラインとリサーチ／オートメーションコンポーネント群です。主な目的は次のとおりです。

- J-Quants API からの株価・財務・カレンダー取得（ETL）
- RSS によるニュース収集と前処理（SSRF 対策等を組み込んだ堅牢な収集）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント・マーケットレジーム判定
- ファクター計算（Momentum / Value / Volatility など）と研究用ユーティリティ
- DuckDB を用いた永続化、品質チェック、監査ログ（発注→約定のトレーサビリティ）

設計方針として「ルックアヘッドバイアスを防止する」「冪等性」「フェイルセーフ」を重視しています。

---

## 機能一覧

- data
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得・保存関数）
  - market calendar 管理（営業日判定、next/prev_trading_day など）
  - ニュース収集（RSS、前処理、SSRF 対策）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ（signal_events, order_requests, executions）と初期化ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: マーケットレジーム（bull/neutral/bear）判定と market_regime 書き込み
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量解析ユーティリティ（calc_forward_returns / calc_ic / factor_summary / rank）
- 設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルートの .env / .env.local を読取）
  - settings オブジェクト経由で環境変数アクセス

---

## セットアップ手順

1. Python（推奨 3.10+）を用意します。

2. 依存パッケージをインストールします（例）:

   ```bash
   pip install duckdb openai defusedxml
   ```

   実際のプロジェクトでは requirements.txt / pyproject.toml を用意して pip / Poetry で管理してください。上記は最低限の主要依存です。

3. リポジトリのルートに `.env` を作成してください。主要な環境変数:

   - 必須:
     - JQUANTS_REFRESH_TOKEN（J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD（kabu ステーション API パスワード）
     - SLACK_BOT_TOKEN（Slack 通知を使う場合）
     - SLACK_CHANNEL_ID（Slack 通知先チャネル）
   - 任意 / デフォルトあり:
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まない（テスト用）

   例（.env.example を参考に作成してください）:

   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

4. データベースディレクトリを作成（必要に応じて）:

   ```bash
   mkdir -p data
   ```

---

## 使い方（コード例）

以下は主要ユーティリティの簡単な使い方例です。実行には DuckDB と必要な環境変数が設定されていることが前提です。

- 共通準備:

  ```python
  import duckdb
  from kabusys.config import settings

  # settings.duckdb_path は Path オブジェクト
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）:

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 27))
  print(result.to_dict())  # ETL のサマリ情報
  ```

- ニュースのセンチメント・スコア算出（ai_scores テーブルへ書き込み）:

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026,3,27), api_key=None)
  print(f"written: {n_written}")
  ```

- マーケットレジーム判定（market_regime テーブルへ書き込み）:

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,27), api_key=None)
  ```

- 監査ログ（監査 DB）の初期化:

  ```python
  from pathlib import Path
  from kabusys.data.audit import init_audit_db

  audit_db_path = Path("data/audit.duckdb")
  audit_conn = init_audit_db(audit_db_path)
  ```

- ファクター計算例:

  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026,3,27))
  # records は {"date","code","mom_1m","mom_3m","mom_6m","ma200_dev"} の dict リスト
  ```

注意:
- OpenAI の呼び出しは retry / fail-safe を組み込んでいますが、APIキーと利用上限に注意してください。
- J-Quants API の呼び出しでは get_id_token / fetch_* 関数があり、自動的にトークンをリフレッシュします。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py (ETLResult 型再エクスポートあり)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
    - (その他のリサーチユーティリティ)
  - research/__init__.py
  - data/__init__.py

主要モジュールの役割:
- config.py: .env / 環境変数の読み込みと settings オブジェクトを提供
- data/jquants_client.py: J-Quants API との通信と DuckDB への保存
- data/pipeline.py: ETL のオーケストレーション（run_daily_etl 等）
- data/news_collector.py: RSS 取得と raw_news 保存
- ai/news_nlp.py: ニュースを LLM で評価して ai_scores へ書き込み
- ai/regime_detector.py: 市場レジームスコアの計算と market_regime 書き込み
- research/*: ファクター計算や統計解析

---

## その他（運用・開発メモ）

- 自動 .env 読み込みはプロジェクトルート（.git 又は pyproject.toml があるディレクトリ）から行われます。テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- DuckDB への複数件挿入（executemany）で空配列を渡すとエラーとなる部分があるため、パラメータが空でないことを明示的にチェックしています（既知の DuckDB 仕様への対応）。
- OpenAI 呼び出しは JSON mode を利用し、厳密な JSON を期待しています。レスポンスパースに失敗した場合はフォールバックして処理を継続します。
- RSS 取得は SSRF / Gzip Bomb 等の対策（ホスト検査・最大バイト数・defusedxml）を実装しています。

---

もし README に追記したい使い方（CLI、例データの投入スクリプト、テストの実行方法など）があれば教えてください。必要に応じてサンプル .env.example やサンプルスクリプトも作成します。