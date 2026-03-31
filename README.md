KabuSys
======

日本株向けのデータプラットフォーム／リサーチ／自動売買基盤のモジュール群です。
このリポジトリは ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI を使用したセンチメント解析）、
研究用ファクター計算、監査ログ（発注→約定トレース）などを提供します。

主な目的
- J-Quants API からの差分 ETL と DuckDB への保存（株価・財務・カレンダー）
- RSS ニュース収集と LLM による銘柄別センチメント算出
- 市場レジーム判定（ETF + マクロニュースの組合せ）
- 研究用ファクター計算・特徴量探索（バックテスト準備）
- 発注〜約定までを追跡する監査ログ（audit テーブル群）
- データ品質チェック（欠損・重複・スパイク・日付整合性）

機能一覧
- データ取得 / 保存
  - J-Quants クライアント（fetch/save：日足、財務、カレンダー、上場銘柄情報）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- ニュース処理 / NLP
  - RSS 収集（SSRF 対策、gzip/サイズ制限、URL 正規化）
  - OpenAI を使ったニュースセンチメント（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 研究（research）
  - モメンタム / ボラティリティ / バリューファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - z-score 正規化ユーティリティ（kabusys.data.stats.zscore_normalize）
- データ品質（data.quality）
  - 欠損、重複、スパイク、日付不整合チェック（run_all_checks）
- カレンダー管理（data.calendar_management）
  - 営業日判定、次/前営業日取得、カレンダー更新バッチ
- 監査ログ（data.audit）
  - signal_events / order_requests / executions テーブルの初期化（init_audit_schema / init_audit_db）
- 設定管理（config）
  - .env（.env.local）と OS 環境変数のロード、自動読み込み（無効化フラグあり）

前提 / 必要なソフトウェア
- Python 3.10+
- 必要パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml

セットアップ手順（ローカル開発用）
1. Python 仮想環境を用意
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （パッケージ管理に setup.py / pyproject.toml があれば pip install -e . を推奨）

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env または .env.local を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必須（利用する機能に応じて）
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - SLACK_BOT_TOKEN=<your_slack_token>           （Slack 通知を使う場合）
   - SLACK_CHANNEL_ID=<your_slack_channel_id>     （同上）
   - KABU_API_PASSWORD=<password>                  （kabuステーション API を使う場合）
   - OPENAI_API_KEY=<your_openai_api_key>          （AI スコアリングを使う場合）

   推奨 / 任意
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|WARNING|ERROR|CRITICAL
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi

   サンプル .env（例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxx
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

使い方（簡単なコード例）
- DuckDB 接続の作成
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（J-Quants から差分取得して保存）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（OpenAI 必須）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # score_news は ai_scores テーブルへ書き込みます
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("written:", n_written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 + マクロニュース）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査 DB の初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn に対して発注/約定ログを記録する想定
  ```

- 研究用関数例
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  ```

設定（注意点）
- config.Settings は .env/.env.local と OS 環境変数を自動でロードします（プロジェクトルート検出: .git または pyproject.toml が基準）。
- 自動ロードを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- settings.jquants_refresh_token などの必須値が未設定の場合は ValueError を投げます。
- AI 系関数は OPENAI_API_KEY を使用します（引数で明示的に渡すこともできます）。
- DuckDB のパスは settings.duckdb_path（デフォルト data/kabusys.duckdb）です。

テスト / モック
- OpenAI 呼び出し部分は内部で _call_openai_api を使っており、ユニットテストでは patch により差し替え可能です（kabusys.ai.news_nlp._call_openai_api など）。
- RSS 取得は _urlopen をモックすることでネットワーク依存を切り離せます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント算出（score_news）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 他）
    - etl.py                         — ETL インターフェース（ETLResult re-export）
    - news_collector.py              — RSS 収集・前処理
    - calendar_management.py         — 市場カレンダー管理
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - quality.py                     — データ品質チェック（run_all_checks 等）
    - audit.py                       — 監査テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py             — momentum/value/volatility 等
    - feature_exploration.py         — forward returns / IC / summary

ログ / モード
- KABUSYS_ENV にて動作モード（development / paper_trading / live）を切替可能。
- LOG_LEVEL 環境変数でログレベルを変更できます（デフォルト INFO）。

ライセンス / 貢献
- この README はコードベースの説明を目的としたドキュメントです。実運用への導入前に必ず十分な検証と安全対策（特に発注ロジック・監査周りのテスト）を実施してください。

お問い合わせ
- 実装の詳細や拡張（ブローカー接続、Slack 通知、UI、CI/CD 等）についてはコード内のドキュメント（各モジュールの docstring）を参照してください。README に無い項目の説明や追加サンプルが必要であれば教えてください。