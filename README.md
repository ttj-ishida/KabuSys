# KabuSys

日本株自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダ取得）、ニュース収集・NLP スコアリング、研究用ファクター算出、監査ログ（オーダートレーサビリティ）などを含むモジュール群を提供します。

---

## 主要なポイント（概要）

- DuckDB ベースのローカルデータベースに対して ETL・品質チェック・監査ログを行うことを目的とした内部ライブラリです。
- J-Quants API からの差分取得・保存、RSS ニュース収集、OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価と市場レジーム判定、研究用ファクター計算（Momentum / Value / Volatility 等）を備えています。
- 自動環境変数読み込み、API リトライ・レート制御、Look-ahead バイアス回避設計などを考慮して実装されています。

---

## 機能一覧

- data:
  - ETL パイプライン（run_daily_etl）: 市場カレンダー、株価（raw_prices）、財務データの差分取得・保存
  - J-Quants API クライアント（取得・保存関数、レート制御、認証リフレッシュ）
  - カレンダー管理（営業日判定・next/prev / get_trading_days、calendar_update_job）
  - ニュース収集（RSS → raw_news, news_symbols）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events / order_requests / executions のスキーマ作成と初期化）
  - 統計ユーティリティ（zscore 正規化）
- ai:
  - ニュース NLP（score_news）: 銘柄ごとのニュースを LLM で批評して ai_scores に書き込む
  - 市場レジーム判定（score_regime）: ETF (1321) の MA200 とマクロニュースセンチメントを合成して日次レジームを判定
- research:
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config:
  - 環境変数管理（.env/.env.local の自動読み込み、必須チェック等）

---

## 要件

- Python >= 3.10
- 主要ランタイム依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API / OpenAI / RSS 取得 など）

（プロジェクトの実際の requirements ファイル / pyproject.toml があればそちらを使用してください）

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化
   - ex:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 例（最低限）:
     - pip install duckdb openai defusedxml

   - 開発用にパッケージを編集して使う場合:
     - pip install -e .

3. 環境変数の準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置いてください。
   - 自動読み込み:
     - .env はプロジェクトルート（.git または pyproject.toml を基準）から自動的に読み込まれます。
     - 自動ロードを無効化する場合:
       - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - SLACK_BOT_TOKEN (必須)
     - SLACK_CHANNEL_ID (必須)
   - 任意・デフォルトあり:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）

4. データベース用ディレクトリ作成
   - 例:
     - mkdir -p data

---

## 使い方（主要例）

※ 各 API は duckdb.DuckDBPyConnection を受け取る設計です。まず接続を作成してください。

- DuckDB 接続例:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL 実行（株価・財務・カレンダー + 品質チェック）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニューススコア付与（OpenAI を使用）
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    # api_key を省略すると環境変数 OPENAI_API_KEY を参照
    n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
    print(f"scored {n_written} codes")

- 市場レジーム判定（MA200 + マクロニュース）
  - from datetime import date
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    # api_key を省略すると環境変数 OPENAI_API_KEY を参照
    score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # または既存接続にスキーマ追加:
    # from kabusys.data.audit import init_audit_schema
    # init_audit_schema(conn)

- 研究用関数（例: モメンタム）
  - from datetime import date
    from kabusys.research.factor_research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    records = calc_momentum(conn, target_date=date(2026, 3, 20))
    # records は [{ "date": ..., "code": "...", "mom_1m": ..., ...}, ...]

---

## 環境変数（主要一覧）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（省略可）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector に使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment (development / paper_trading / live)
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを抑止する（値を設定すると抑止）

.env のフォーマットや `.env.local` の優先順は、kabusys.config モジュールを参照してください（OS環境 > .env.local > .env）。

---

## 実装上の留意点 / 設計方針（抜粋）

- Look-ahead バイアス防止: ETL / AI スコアリング関数はいずれも内部で datetime.today() を直接参照しないなどの配慮があり、target_date を明示して実行することを想定しています。
- 冪等性: DuckDB への保存は多くが ON CONFLICT DO UPDATE（冪等）で行われます。ETL は差分取得／バックフィルを行います。
- API 耐性: J-Quants、OpenAI 呼び出しはリトライ・バックオフやレート制御が組み込まれています。API エラー時はフォールバック動作（例: macro_sentiment = 0.0）を行う箇所が設計されています。
- セキュリティ: ニュース収集は SSRF 対策、XML パースは defusedxml を使用、RSS リクエストの最大バイト数制限などを実施しています。

---

## ディレクトリ構成（抜粋）

以下はソースコードの主なディレクトリとファイル構成（抜粋）です:

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
    - pipeline.py (ETLResult 再エクスポート)
    - etl.py (ETL interface)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py

（実際のツリーはリポジトリ内の src/kabusys 以下をご確認ください）

---

## テスト・開発ヒント

- 自動環境読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（ユニットテスト等で .env の影響を避けたい場合に有用）。
- OpenAI 呼び出しは内部で _call_openai_api を経由しているため、ユニットテストでは該当関数をモックして API 呼び出しを差し替えることができます（news_nlp/_call_openai_api、regime_detector/_call_openai_api を patch）。
- DuckDB の executemany に空リストを与えると問題になるバージョンがあるため、モジュール内で空チェックが行われています。テスト環境も同様の制約を意識してください。

---

この README はコードベースの主要機能・利用方法をまとめたものです。細かい API の引数や挙動は各モジュール（特に kabusys.data.jquants_client, kabusys.data.pipeline, kabusys.ai.news_nlp, kabusys.ai.regime_detector 等）のドキュメント文字列を参照してください。必要であれば各関数の使い方サンプルや運用手順（cron/ジョブ設計、監視）についても追加で作成します。