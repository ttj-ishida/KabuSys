# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。J-Quants / kabuステーション 等の外部 API と連携してデータ取得（ETL）、品質チェック、ニュース NLP（LLM を用いたセンチメント）、市場レジーム判定、監査ログ（発注→約定トレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は以下の用途に適したモジュール群を提供します。

- J-Quants からの株価・財務・上場情報・市場カレンダーの差分取得（ETL）
- DuckDB を用いたデータ保存・スキーマ管理
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- RSS ニュース収集と記事前処理 / 銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）とマクロセンチメント評価
- ETF（1321）200日移動平均とマクロセンチメントを合成した市場レジーム判定
- 研究用のファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量解析
- 監査ログスキーマ（signal → order_request → execution）の初期化ユーティリティ

設計上の特徴：
- ルックアヘッドバイアス回避（日時や DB クエリで将来データを参照しない）
- 冪等性（ETL 保存は ON CONFLICT / DO UPDATE）と堅牢なリトライ・バックオフ
- 外部 API 呼出しのフェイルセーフ：API 失敗時は部分的にスキップして継続

---

## 機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（レート制御・リトライ・トークン自動リフレッシュ）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - ニュース収集: RSS フェッチ、前処理、raw_news への保存ロジック（SSRF 対策等）
  - データ品質チェック: missing_data / spike / duplicates / date_consistency / run_all_checks
  - 監査ログ: init_audit_schema / init_audit_db（DuckDB）
  - 統計ユーティリティ: zscore_normalize
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを取得して ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF 1321 の MA 乖離とマクロニュース LLM を合成して market_regime に書き込み
- research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings クラス: 環境変数から設定値をまとめて取得（自動 .env ロードあり）

---

## セットアップ手順（ローカル開発向け：推奨）

この README では一般的な手順を示します。実際にはプロジェクトの packaging / requirements.txt / pyproject.toml を参照してください。

1. Python（3.10 以上を推奨）仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトの requirements.txt / pyproject.toml がある場合はそちらを使用してください）

3. ソースを配置（本 README は src/kabusys 配下のモジュールを想定）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（優先順: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   最低限必要な環境変数（用途）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token 用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（execution モジュール等で使用）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（監視・アラート）
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）

   任意（デフォルトあり）:
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視等）パス（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABU_API_BASE_URL, LOG_LEVEL, KABUSYS_ENV

   .env の例（プロジェクトルートに .env を作る）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡易例）

以下は Python REPL やスクリプトから呼び出す基本的な例です。

- DuckDB 接続を作成して ETL を実行する（日次パイプライン）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を参照しても良い
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai_scores への書き込み）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"wrote {n_written} scores")
  ```

- 市場レジーム判定を実行:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査ログ DB の初期化（専用 DB を作る）:
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成されます
  ```

- 研究向けファクター計算:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)
  ```

注: 上記の多くの関数は DuckDB の所定テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, prices_daily, market_calendar, など）を前提とします。ETL を先に実行してデータを入れておくのが一般的です。

---

## 主要 API と挙動メモ

- 環境変数自動読み込み
  - プロジェクトルート（.git または pyproject.toml）を自動検出し .env / .env.local を読み込みます。
  - 読み込み順: OS 環境変数 > .env.local（上書き） > .env（未設定キーのみ）
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- J-Quants クライアント
  - レート制御（120 req/min）、リトライ（408/429/5xx 等）、401 時はリフレッシュして再試行を実装。
  - fetch_* 系はページネーション対応。
  - save_* 系は ON CONFLICT DO UPDATE による冪等保存。

- News NLP / Regime Detector（OpenAI）
  - gpt-4o-mini を想定。JSON mode（response_format）で厳密な JSON を期待します。
  - API エラー時はフェイルセーフ（スコア 0.0 等）で継続する設計。
  - テスト容易性のため、内部の API 呼び出し関数をモックできるように実装されています（関数単位で差替え可能）。

- データ品質チェック
  - すべてのチェックは QualityIssue のリストを返す。Fail-Fast ではなく全チェックを実行して問題を収集します。
  - run_all_checks でまとめて実行できます。

- 監査ログ（audit）
  - signal_events / order_requests / executions のテーブル定義とインデックスを提供。
  - init_audit_db で専用 DB を初期化できます（タイムゾーンを UTC に固定）。

---

## ディレクトリ構成

以下は主要モジュールとファイルの概観（src/kabusys 配下）です。実際のリポジトリには追加のテスト・ドキュメント・スクリプトが含まれる場合があります。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント（銘柄別）と関連ユーティリティ
    - regime_detector.py            — ETF MA とマクロ LLM を合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント / save_* / fetch_*
    - pipeline.py                   — ETL パイプライン（run_daily_etl 他）
    - etl.py                        — ETL インターフェース（ETLResult 再エクスポート）
    - calendar_management.py        — マーケットカレンダー管理（営業日判定・update job 等）
    - news_collector.py             — RSS フィード取得・前処理・保存
    - quality.py                    — データ品質チェック群
    - stats.py                      — zscore_normalize 等統計ユーティリティ
    - audit.py                      — 監査ログスキーマ初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py            — モメンタム / ボラティリティ / バリュー系ファクター計算
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー等
  - monitoring/ (参照される可能性のあるフォルダ: 監視関連モジュール等)
  - execution/ (発注関連モジュール: kabuAPI とのインターフェースなど)

---

## 注意事項・推奨運用

- DuckDB スキーマ: 関数は所定のテーブルが存在することを前提にしているため、ETL 実行前にスキーマ初期化やマイグレーションを行ってください（プロジェクトに schema 初期化スクリプトがある想定）。
- OpenAI 利用: API 呼び出しにはコストが発生します。バッチサイズや再試行ポリシーに留意してください。
- API トークン管理: リフレッシュトークン / API キーは秘密情報です。`.env` をリポジトリにコミットしないでください。
- テスト: 内部で外部 API を呼ぶ箇所はモック可能な関数分離が行われているため、ユニットテストでモックして実行することを推奨します。
- ログレベル: LOG_LEVEL 環境変数で調整できます。development / paper_trading / live 環境フラグは Settings.env で制御されます。

---

必要であれば、README に含める具体的なコマンド（pytest 実行例、Dockerfile / docker-compose のサンプル、CI 設定例、SQL スキーマ初期化スクリプトなど）も追記できます。どの追加情報が欲しいか教えてください。