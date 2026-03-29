# KabuSys

日本株向け自動売買／データプラットフォームコンポーネント群（ライブラリ）

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）
- 目的: J-Quants / RSS / OpenAI 等を組み合わせたデータ収集、品質チェック、AIベースのニュース評価、ファクター計算、監査ログ等を提供する日本株向け基盤ライブラリ

---

## プロジェクト概要

KabuSys は次のような責務を持つ Python ライブラリ群です。

- データ収集（J-Quants API）と ETL（DuckDB 保存、差分取得、バックフィル）
- 市場カレンダー管理（JPX カレンダーの取得と営業日判定）
- ニュース収集（RSS）と前処理（SSRF 対策・トラッキング除去）
- ニュース NLP（OpenAI を用いた銘柄別センチメント算出）
- 市場レジーム判定（ETF MA とマクロニュースの LLM スコアを合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ／トレーサビリティ（signal → order_request → execution の追跡用スキーマ）

設計上の特徴:
- ルックアヘッドバイアス防止（API 呼び出しや日付取得で現在時刻を直接参照しない等）
- 冪等性（DB 保存は ON CONFLICT / upsert を使用）
- フェイルセーフ（外部 API 異常時は全体を壊さず継続する設計）
- リトライ・レート制御（J-Quants/ OpenAI 呼び出しでリトライやスロットリングを実装）

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API から日次株価/財務/カレンダーを取得（ページネーション対応）
  - DuckDB への保存（save_daily_quotes, save_financial_statements, save_market_calendar）
  - get_id_token（refresh token から id_token 取得）
  - RateLimiter、リトライ、401 自動リフレッシュ対応

- data.pipeline
  - run_daily_etl: カレンダー→価格→財務→品質チェックを順に実行する日次 ETL
  - 個別 ETL ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult dataclass（実行結果の集約）

- data.news_collector
  - RSS フィード取得・パース・前処理・raw_news への冪等保存（SSRF、gzip、XML デフューズ対策）

- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks（品質チェックの一括実行）

- data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job

- data.audit
  - 監査ログ用テーブル作成（signal_events / order_requests / executions）
  - init_audit_schema / init_audit_db（監査DBの初期化）

- ai.news_nlp
  - score_news: 銘柄ごとにニュースをまとめて LLM でセンチメントを算出し ai_scores に保存
  - calc_news_window: ニュース対象ウィンドウ計算（JST 前日15:00〜当日08:30）

- ai.regime_detector
  - score_regime: ETF (1321) の 200 日 MA 乖離とマクロニュースの LLM スコアを合成して market_regime に保存

- research
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank（研究用ユーティリティ）
  - zscore_normalize（data.stats から）

---

## セットアップ手順（開発環境）

1. Python（推奨: 3.10 以上）を用意してください。

2. リポジトリをクローンし、パッケージとしてインストール（編集可能な開発インストール）:
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install -e ".[dev]"    # プロジェクトに合わせて extras を用意している場合
   ```
   ※ requirements が別にある場合は `pip install -r requirements.txt` を利用してください。

3. 必要な主要依存パッケージ（代表例）
   - duckdb
   - openai
   - defusedxml
   - typing-extensions（古い Python を使う場合）
   例:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定
   - 環境変数は .env または .env.local をプロジェクトルートに置くことで自動ロードされます（src/kabusys/config.py）。
   - 自動ロードはプロジェクトルートの判定に .git または pyproject.toml を使います。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数（examples）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     # 任意（デフォルト値あり）
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_DISABLE_AUTO_ENV_LOAD=  # 1 を設定すると自動読み込みを無効化
     ```
   - 例として .env ファイルの雛形:
     ```
     JQUANTS_REFRESH_TOKEN=REPLACE_ME
     KABU_API_PASSWORD=REPLACE_ME
     SLACK_BOT_TOKEN=REPLACE_ME
     SLACK_CHANNEL_ID=REPLACE_ME
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（簡単な呼び出し例）

以下は Python REPL やスクリプトからの簡単な使い方例です。DuckDB ファイルはデフォルト `data/kabusys.duckdb` を想定します。

- DuckDB 接続を作成:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL の実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコアリング（score_news）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API キーは環境変数 OPENAI_API_KEY に設定するか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written: {n_written}")
  ```

- 市場レジーム判定（score_regime）:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ DB の初期化:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_db はテーブル作成済みの DuckDB 接続を返す
  ```

- J-Quants の id_token を明示的に取得:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用
  ```

- カレンダー関係のヘルパー:
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  is_trade = is_trading_day(conn, date(2026, 3, 20))
  nxt = next_trading_day(conn, date(2026, 3, 20))
  ```

注意点:
- 各関数は外部 API 呼び出し時に例外を投げる場合があります。実運用ではログや再試行・通知を組み合わせてください。
- OpenAI 呼び出しでは JSON Mode を想定したレスポンスのバリデーションを行っています。レスポンスの形式が違うとスキップされる場合があります。

---

## ディレクトリ構成（主要ファイル）

以下はこのコードベースの主要ファイルと役割（src/kabusys 以下）です。

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数自動ロード・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             # ニュースの LLM スコアリング（score_news 等）
    - regime_detector.py      # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - etl.py                  # ETL インタフェース再エクスポート
    - news_collector.py       # RSS 収集と raw_news 保存
    - calendar_management.py  # 市場カレンダー管理（営業日判定 等）
    - quality.py              # データ品質チェック
    - stats.py                # 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                # 監査ログスキーマ初期化・DB 初期化
  - research/
    - __init__.py
    - factor_research.py      # ファクター計算（momentum / volatility / value）
    - feature_exploration.py  # 将来リターン・IC・統計サマリー
  - monitoring/ (コードベースには明示的ファイルなしが想定される)
  - strategy/ (外部戦略モジュールの想定)
  - execution/ (取引執行モジュールの想定)

---

## 注意事項・設計ノート

- 日付取り扱い:
  - 多くの処理（score_news, score_regime, run_daily_etl 等）は内部で datetime.today()/date.today() を直接参照せず、target_date を引数で受け取る設計です。バックテストにおけるルックアヘッドバイアスを抑えるためです。
- 環境変数の自動ロード:
  - config.py はプロジェクトルート（.git か pyproject.toml）を起点に .env と .env.local を読みます。既存 OS 環境変数は保護されます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを止められます。
- 外部 API:
  - J-Quants: レート制限（120 req/min）に合わせたスロットリングを実装しています。401 時の refresh token からの id_token 更新をサポートします。
  - OpenAI: gpt-4o-mini を標準で利用する設計（response_format=JSON mode 想定）。API エラーやパースエラー発生時はフォールバック動作（0.0 など）により処理を継続します。
- セキュリティ:
  - RSS 取得（news_collector）には SSRF 対策、XML インジェクション対策（defusedxml）、レスポンスサイズ制限が実装されています。
- DB 保全:
  - DuckDB への書き込みは可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）を採用しています。
- テスト:
  - 実行環境や API キーが必要な箇所があるため、ユニットテストでは外部呼び出し（OpenAI / J-Quants / urllib）をモックする想定です。コード内にモック可能なヘルパー関数が用意されています。

---

## 貢献

- バグ報告や提案は issue を立ててください。
- コードスタイル・設計に関するドキュメント（StrategyModel.md, DataPlatform.md など）に合わせて実装を行っています。新しい機能追加時はドキュメントを更新してください。

---

この README はコードベースから主要機能・使い方を抜粋して記載しています。より詳細な実行例やデプロイ手順、CI 設定、運用ルールなどはプロジェクトの上流ドキュメント（Design doc / Ops runbook）を参照してください。