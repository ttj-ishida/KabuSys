# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データの ETL、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査（オーディット）テーブル初期化などを提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・カレンダー等データの差分取得と DuckDB への保存（ETL）
- RSS によるニュース収集と OpenAI を用いた銘柄別センチメント（ai_score）算出
- マクロニュースと ETF の移動平均乖離を組み合わせた市場レジーム判定（bull/neutral/bear）
- 各種ファクター（モメンタム／ボラティリティ／バリュー等）の計算と解析ユーティリティ
- 監査ログ用スキーマ（signal → order_request → executions）生成ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴：
- DuckDB をデータストアに使用（オフライン解析・高速クエリ向け）
- LLM 呼び出しは OpenAI（gpt-4o-mini 等）を使用、JSON Mode を前提とした堅牢なパーサと再試行ロジック
- Look-ahead bias を避ける設計（内部で date.today()/datetime.today() を不用意に参照しない等）
- 冪等性を意識した保存（ON CONFLICT DO UPDATE / DO NOTHING 等）

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / 環境変数の自動ロード・設定管理
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）

- kabusys.data.jquants_client
  - J-Quants API との安全なやり取り（認証/トークンリフレッシュ / レート制御 / リトライ）
  - fetch/save 用ヘルパ（daily_quotes, financial_statements, market_calendar, listed_info）

- kabusys.data.pipeline / etl
  - 日次 ETL 実行 run_daily_etl（カレンダー → 株価 → 財務 → 品質チェック）
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETLResult データクラス

- kabusys.data.quality
  - データ品質チェック（欠損 / スパイク / 重複 / 日付整合性）と QualityIssue 集約

- kabusys.data.news_collector
  - RSS フィード取得・前処理・raw_news への冪等保存支援（SSRF 対策・gzip 上限等）

- kabusys.ai.news_nlp
  - 銘柄単位に記事を集約して OpenAI に投げ、ai_scores を計算・保存（バッチ化・リトライ・レスポンスバリデーション）

- kabusys.ai.regime_detector
  - ETF (1321) の 200 日 MA 乖離とマクロニュースセンチメントを合成して market_regime を算出・保存

- kabusys.research
  - calc_momentum, calc_volatility, calc_value 等ファクター計算
  - calc_forward_returns, calc_ic, factor_summary, rank 等解析ユーティリティ

- kabusys.data.audit
  - 監査ログ用スキーマ初期化 (signal_events, order_requests, executions)
  - init_audit_db / init_audit_schema 提供

- kabusys.data.calendar_management
  - JPX カレンダーを扱うユーティリティ（営業日判定 / next/prev_trading_day / calendar_update_job）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 演算子等を使用）
- Git 等の開発環境

1. リポジトリをクローンしてパッケージをインストール（開発モード）
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install -e .            # setup.py/pyproject がある前提
   ```

2. 必要パッケージ（明示的に入れる場合）
   ```
   pip install duckdb openai defusedxml
   ```
   ※ プロジェクトの pyproject.toml / requirements.txt があればそちらを使用してください。

3. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動ロードされます（kabusys.config が自動で読み込みます）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の主な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI API キー（ai.score 系で使用。関数引数で注入も可能）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必要時）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用 Slack 設定（必要時）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB など（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース初期化（監査用 DB など）
   - 監査ログ用 DB を初期化する例:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # もしくは: conn = duckdb.connect("data/kabusys.duckdb"); init_audit_schema(conn)
     ```

---

## 使い方（代表的な例）

以下は主要関数の使用例です。各関数は duckdb.DuckDBPyConnection を受け取るため、接続を共有して使用します。

- DuckDB 接続を作成する
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアを計算して ai_scores に書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
  print(f"written codes: {written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査スキーマ初期化（既存接続へ追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- ファクター計算・解析（研究用途）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意:
- OpenAI API の呼び出しは外部ネットワークを伴います。単体テストでは `_call_openai_api` をパッチしてスタブ化する設計になっています（モジュール内でそのように注記あり）。
- ETL は外部 API 呼び出しが失敗した場合でも他のステップは継続する設計です（ログに出力され、ETLResult.errors に蓄積されます）。

---

## ディレクトリ構成（抜粋）

src/kabusys/ 以下の主要ファイルと役割:

- __init__.py
  - パッケージ初期化、バージョン定義

- config.py
  - 環境変数ロード・Settings クラス

- ai/
  - news_nlp.py            : ニュースの LLM ベースセンチメント（ai_scores）
  - regime_detector.py     : 市場レジーム判定（ETF MA + マクロニュース）

- data/
  - jquants_client.py      : J-Quants API クライアント（fetch/save）
  - pipeline.py            : ETL パイプライン / run_daily_etl 等
  - etl.py                 : ETLResult の再エクスポート
  - news_collector.py      : RSS 取得・前処理
  - quality.py             : データ品質チェック
  - stats.py               : zscore_normalize 等汎用統計
  - calendar_management.py : 市場カレンダー操作・更新ジョブ
  - audit.py               : 監査ログスキーマ定義 / 初期化ユーティリティ

- research/
  - factor_research.py     : Momentum / Volatility / Value 計算
  - feature_exploration.py : forward returns, IC, summary, rank 等
  - __init__.py            : 研究用ユーティリティの再エクスポート

（上記以外にも補助的モジュールが存在します。実際のファイル一覧は src/kabusys 配下を参照してください）

---

## 注意事項 / 運用上のヒント

- 環境変数管理
  - プロダクションでは `.env.local` を使い OS 環境変数より優先されるように運用可能。
  - テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動ロードを無効化できます。

- OpenAI の利用
  - API キーは環境変数 OPENAI_API_KEY に設定するか、関数呼び出し時に api_key 引数で注入できます（テストでは注入推奨）。
  - LLM 呼び出しでは JSON Mode を期待しており、既知のバリデーションロジックが存在します。外部呼び出しエラー時はフェイルセーフで 0.0 等にフォールバックする設計です。

- DuckDB
  - バッチ処理や解析で共有接続を使う場合、トランザクション管理に注意してください（init_audit_schema は transactional 引数で制御可能）。
  - executemany に空リストを渡すと DuckDB のバージョンによってはエラーになるため、内部でチェックされています。

- セキュリティ
  - news_collector は SSRF 対策（プライベート IP の排除、リダイレクト検査）や XML の安全パーサ（defusedxml）を使用しています。
  - J-Quants クライアントではレートリミットとトークン自動リフレッシュを実装しています。

---

## ライセンス / 貢献

（この README はコードから自動作成した要約です。リポジトリの LICENSE ファイル / CONTRIBUTING.md を参照してください。）

---

必要であれば README にサンプル .env.example やよくあるトラブルシュート（OpenAI レスポンスパース失敗、J-Quants 401 など）を追記します。どの情報を詳しく載せたいか教えてください。