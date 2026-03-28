# KabuSys

日本株の自動売買／データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（DuckDB）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の目的を持ったモジュール群です。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュースの収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント分析（銘柄別）とマクロセンチメント評価
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- 市場カレンダー管理（営業日判定など）
- 監査ログ（signal → order_request → execution のトレース）用スキーマ初期化ユーティリティ
- データ品質チェック

設計上の特徴：
- DuckDB をメインのローカルデータストアに使用（軽量・高速）
- Look-ahead bias を避ける設計（内部で date.today()/datetime.today() を不用意に参照しない）
- API 呼び出しに対するレート制御・リトライ・フェイルセーフ処理を実装
- RSS の SSRF 対策、XML の安全パース等セキュリティ対策あり

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: fetch_* / save_* 関数
  - 差分取得・ページネーション・トークンリフレッシュ・レート制御・リトライ実装

- ニュース収集 / NLP
  - RSS 取得・前処理・記事ID正規化・保存（kabusys.data.news_collector）
  - 銘柄ごとの記事集約と OpenAI へのバッチ送信（kabusys.ai.news_nlp.score_news）
  - マクロニュースと ETF ma200 を用いた市場レジーム判定（kabusys.ai.regime_detector.score_regime）

- リサーチ / ファクター
  - calc_momentum / calc_volatility / calc_value（kabusys.research.factor_research）
  - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）
  - zscore_normalize（kabusys.data.stats）

- データ品質・カレンダー
  - 品質チェック群（欠損・スパイク・重複・日付不整合）: kabusys.data.quality.run_all_checks
  - market_calendar 管理・営業日判定・next/prev_trading_day（kabusys.data.calendar_management）
  - calendar_update_job による J-Quants からのカレンダー差分更新

- 監査ログ / トレーサビリティ
  - 監査スキーマ初期化（kabusys.data.audit.init_audit_schema / init_audit_db）
  - signal_events / order_requests / executions テーブルとインデックス群を提供

---

## セットアップ手順

前提：
- Python 3.10 以上（typing に | を利用）
- DuckDB が使用可能（Python パッケージとしてインストールされる）

1. ソースをインストール（開発モード推奨）
   - git clone してプロジェクトルートで:
     ```bash
     pip install -e .
     ```
   - 必要な外部ライブラリ（例）
     ```bash
     pip install duckdb openai defusedxml
     ```
     （プロジェクトに requirements.txt があればそちらを使用してください）

2. 環境変数の設定
   - ルートに `.env` / `.env.local` を配置すると自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN=<J-Quants のリフレッシュトークン>
     - OPENAI_API_KEY=<OpenAI API キー>
     - KABU_API_PASSWORD=<kabuステーション API パスワード>
     - SLACK_BOT_TOKEN=<Slack Bot トークン>
     - SLACK_CHANNEL_ID=<Slack チャネル ID>
     - DUCKDB_PATH=data/kabusys.duckdb（省略可、デフォルト）
     - SQLITE_PATH=data/monitoring.db（省略可、デフォルト）
     - KABUSYS_ENV=development|paper_trading|live（省略時 development）
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL（省略時 INFO）

   - サンプル .env（プロジェクトルートに .env を作成）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxxx
     KABU_API_PASSWORD=your_kabu_pass
     SLACK_BOT_TOKEN=xoxb-xxxxx
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=./data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

3. DuckDB データベースの準備
   - `settings.duckdb_path`（default: data/kabusys.duckdb）に接続して必要なスキーマを作成してください（プロジェクトに schema 初期化スクリプトがある場合はそれを使用）。
   - 監査ログ専用 DB の初期化例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（代表的な例）

- DuckDB に接続して日次 ETL を実行する（J-Quants トークンは環境変数または id_token 引数で指定）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントをスコアリングして ai_scores テーブルへ書き込む:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示的に渡すことも可能。None の場合 OPENAI_API_KEY を参照。
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジームを判定して market_regime テーブルへ書き込む:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（例: モメンタム）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  # momentum: list[dict] を受け取り、更に zscore_normalize 等で正規化可能
  ```

- 品質チェックを実行:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for issue in issues:
      print(issue.check_name, issue.severity, issue.detail)
  ```

- 監査スキーマの初期化（既存接続へ適用）:
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意:
- OpenAI 呼び出しは API キー（OPENAI_API_KEY）を環境変数か関数引数で与える必要があります。
- J-Quants 認証は JQUANTS_REFRESH_TOKEN を設定すると自動で ID トークンへ変換します。

---

## 主なモジュール / ディレクトリ構成

（簡易表示 — 実際のファイルは src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py  — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（ETF ma200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（fetch / save）
    - pipeline.py  — ETL パイプライン（run_daily_etl 等）
    - etl.py  — ETLResult 再エクスポート
    - stats.py  — zscore_normalize 等統計ユーティリティ
    - quality.py  — データ品質チェック群
    - news_collector.py  — RSS 収集（SSRF 対策・XML セーフパース）
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - audit.py  — 監査ログスキーマ初期化・init_audit_db
  - research/
    - __init__.py
    - factor_research.py  — Momentum/Value/Volatility 等の計算
    - feature_exploration.py — forward returns / IC / summary / rank
  - ai/、research/、data/ 以下に多数の補助関数・ユーティリティあり

---

## 運用上の注意 / 設計上のポイント

- 環境変数の自動ロード
  - プロジェクトルート（.git または pyproject.toml を探索）にある `.env` および `.env.local` を自動ロードします。
  - テスト等で無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- セキュリティ・堅牢性
  - RSS の取得は SSRF 対策（リダイレクト検査・プライベート IP 検出）を実装しています。
  - defusedxml を使って XML パース攻撃を防ぎます。
  - J-Quants クライアントはレート制御とリトライを持ち、401 時はトークンの自動リフレッシュを試みます。
  - OpenAI 呼び出しはリトライ・バックオフを実装し、失敗時はフェイルセーフ（スコア 0.0）で継続する設計です。

- Look-ahead bias 回避
  - 内部のアルゴリズムは原則として target_date 未満のデータのみ参照する、あるいは引数で日付を与えることでバックテストでのリークを防止しています。

- DuckDB 注意点
  - DuckDB の executemany に空リストを渡すと問題が生じる場合があるため、コード内でチェックを行っています。

---

## 開発者向け補足

- テストしやすくするため、OpenAI 呼び出し等はモジュール内で差し替え可能（unitest.mock.patch を想定している箇所あり）。
- ログレベルは環境変数 LOG_LEVEL で調整できます。
- プロジェクト配布後も .env の自動ロードが期待通りに動作するよう、config._find_project_root() は __file__ を基準に親ディレクトリを探索します。

---

もし README に含めたい追加の情報（例: CI / テスト実行方法、schema 作成 SQL、具体的な運用手順や cron ジョブ設定例）があれば教えてください。必要に応じて追記します。