# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
DuckDB を用いたデータパイプライン（ETL）、ニュース・NLP（OpenAI）連携、リサーチ用ファクター計算、監査ログ（発注／約定トレーサビリティ）などのユーティリティを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株に関する次の機能群を提供する Python パッケージです。

- J-Quants API と連携した差分 ETL（株価日足 / 財務 / マーケットカレンダー）
- RSS ベースのニュース収集と OpenAI を用いたニュースセンチメント解析（銘柄毎）
- マクロニュース + ETF（1321）200日移動平均乖離を用いた市場レジーム判定
- リサーチ向けファクター計算（モメンタム／ボラティリティ／バリュー等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）用スキーマ生成と初期化ユーティリティ
- 環境設定を .env / 環境変数から自動読み込みする設定管理

設計上の注力点：
- Look-ahead bias を避ける（内部処理で現在時刻に依存しない）
- 冪等性（DB への保存は ON CONFLICT / UPSERT で上書き）
- フェイルセーフ：外部 API 失敗時は部分的にフォールバックして継続する設計

---

## 主な機能一覧

- data:
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save / 認証トークン取得）
  - カレンダー管理（営業日判定, next/prev_trading_day, calendar_update_job）
  - ニュース収集（RSS fetch_rss, 前処理）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai:
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) MA200 とマクロニュースセンチメントを合成して market_regime に書き込む
- research:
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - 機能探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config:
  - .env 自動ロード（プロジェクトルート検出、.env → .env.local 優先度）
  - Settings クラスを通して環境変数にアクセス

---

## 前提（必須環境／依存）

- Python 3.9+（型ヒントに union 型が使われているため比較的新しい Python を想定）
- パッケージ依存（例）:
  - duckdb
  - openai（OpenAI Python SDK）
  - defusedxml
  - そのほか標準ライブラリ

（実プロジェクトでは pyproject.toml / requirements.txt を用意して pip install -r requirements.txt などでインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... && cd ...

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install -e .           # パッケージとして開発インストール（セットアップが用意されている場合）
   - または
   - pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` と `.env.local` を配置できます。
   - 自動ロードの順序: OS 環境変数 ＞ .env.local ＞ .env
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

   - 主に必要なキー（最低限）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API のパスワード（発注等を行う場合）
     - SLACK_BOT_TOKEN       : Slack 通知を使う場合
     - SLACK_CHANNEL_ID      : Slack 通知先チャネル
     - OPENAI_API_KEY        : OpenAI API を利用する機能（news_nlp / regime_detector）のために必要
   - データベースパス（任意; デフォルトは data/ 以下）:
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (監視用 DB 等)

   例 .env（サンプル）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB / 監査 DB の初期化（必要に応じて）
   - 監査ログ専用 DB を作る例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - または既存の DuckDB 接続でスキーマを追加:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn)
     ```

---

## 使い方（代表的な API / 実行例）

- DuckDB 接続を使う共通例:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定しないと今日が対象（内部で営業日に調整される）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に書き込む:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API キーは環境変数 OPENAI_API_KEY を使うか api_key 引数で指定
  n_written = score_news(conn, date(2026, 3, 20), api_key=None)
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定を実行する:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, date(2026, 3, 20), api_key=None)
  ```

- ファクター計算（例: モメンタム）:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, date(2026, 3, 20))
  # records は [{ "date": ..., "code": "...", "mom_1m": ..., ...}, ...]
  ```

- データ品質チェックを実行:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

注意:
- OpenAI 呼び出しを行う機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。api_key 引数で明示的に渡すことも可能です。
- J-Quants API 呼び出しは JQUANTS_REFRESH_TOKEN を利用して id_token を取得します。

---

## 設定・挙動の留意点

- .env のパースは POSIX シェル風に実装されており、クォートやエスケープ、コメント処理に対応しています。
- 自動読み込みの順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env.local の override は可能ですが OS 環境変数は上書きされません。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- Settings クラスで以下を取得できます:
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.slack_channel_id, settings.duckdb_path, settings.sqlite_path, settings.env, settings.log_level, settings.is_live / is_paper / is_dev
- KABUSYS_ENV の有効値: development, paper_trading, live
- LOG_LEVEL の有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

---

## ディレクトリ構成（主なファイルと説明）

src/kabusys/
- __init__.py — パッケージ初期化（バージョン・公開 API）
- config.py — 環境変数 / .env 自動読み込み、Settings クラス

src/kabusys/ai/
- __init__.py — ai パッケージ公開関数
- news_nlp.py — ニュースを銘柄別に集約し OpenAI でセンチメント評価、ai_scores に書き込み
- regime_detector.py — ETF(1321) MA200 とマクロニュース（LLM）を合成して market_regime に記録

src/kabusys/data/
- __init__.py
- jquants_client.py — J-Quants API クライアント（認証、fetch / save / rate limiting / retry）
- pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
- etl.py — ETLResult の公開再エクスポート
- news_collector.py — RSS フィード取得・前処理・SSRF 対策・raw_news 保存補助
- calendar_management.py — マーケットカレンダー管理、営業日判定、calendar_update_job
- stats.py — 汎用統計ユーティリティ（zscore_normalize）
- quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
- audit.py — 監査ログ（signal / order_request / executions）DDL と初期化ユーティリティ

src/kabusys/research/
- __init__.py — research パッケージ公開関数
- factor_research.py — モメンタム / ボラティリティ / バリュー 等の計算
- feature_exploration.py — 将来リターン計算、IC（Spearman）計算、統計サマリ、ランク関数

---

## 運用上の注意点

- Look-ahead bias 回避のため、関数は target_date を外部から与える設計です。内部で date.today()／datetime.today() に依存しないよう留意されていますが、run_daily_etl 等はデフォルトで今日を使います（明示的に target_date を渡すことで過去の日での再実行やバックテストに安全に利用できます）。
- 外部 API（J-Quants / OpenAI）の呼び出しはレート制御・リトライを実装しています。API キーやネットワークエラー時のフォールバック動作に注意してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、空チェックが入っています。DuckDB バージョン互換性に留意してください。
- ニュース収集では SSRF 対策、レスポンスサイズ制限、gzip 解凍チェックなどの安全機構を備えています。

---

## 貢献 / 開発メモ

- テストや CI を追加する際は、環境変数の自動読み込みを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）してテスト固有の環境を用意してください。
- OpenAI 呼び出し箇所は内部で切り替えやモックしやすいように抽象化されています（テストで _call_openai_api をパッチすることを想定）。
- ETL の品質チェックは Fail-Fast ではなく全件収集する設計です。呼び出し元で result.has_quality_errors / result.has_errors を評価して運用判断を行ってください。

---

README に不足している点や、実行時の具体的なエラー対応、CI 設定などが必要であれば教えてください。必要に応じて実運用向けの手順（cron / Airflow での ETL スケジュール化、監視 Slack 通知の組み込みなど）も作成します。