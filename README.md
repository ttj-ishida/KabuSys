KabuSys
=======

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。  
ETL／データ品質チェック／ニュース収集／AIベースのニュースセンチメント評価／市場レジーム判定／研究用ファクター計算や監査ログ機能を提供します。

要点
----
- パッケージ名: kabusys
- 目的: J-Quants / JPX 等からデータを取得して DuckDB に保存し、品質チェック、NLP・LLM によるニュース評価、ファクター計算や自動売買監査ログを行う。
- 設計方針の例: ルックアヘッドバイアス回避、冪等性（ON CONFLICT / idempotent 保存）、フェイルセーフな API リトライ、外部 API 呼び出しの分離（テスト支援）。

主な機能
--------
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - settings オブジェクトで設定値を取得（例: settings.jquants_refresh_token）
- データ取得・ETL（kabusys.data）
  - J-Quants API クライアント（jquants_client）
    - 株価（日足）、財務データ、JPXカレンダー、上場銘柄一覧の取得
    - トークン自動リフレッシュ、レートリミット管理、指数バックオフ
    - DuckDB への冪等保存関数（save_daily_quotes 等）
  - ETL パイプライン（pipeline）
    - run_daily_etl: カレンダー・株価・財務の差分取得 → 保存 → 品質チェック
    - 各種個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - データ品質チェック（quality）
    - 欠損・スパイク・重複・日付整合性チェック
    - QualityIssue オブジェクトで問題を集約
  - マーケットカレンダー管理（calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - ニュース収集（news_collector）
    - RSS 取得・前処理・SSRF 保護・トラッキング除去・raw_news への冪等保存
  - 監査ログ（audit）
    - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（stats）
    - zscore_normalize 等
- AI モジュール（kabusys.ai）
  - ニュース NLP（news_nlp.score_news）
    - 指定ウィンドウ内のニュースを銘柄ごとに集約し OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores に保存
    - バッチ・トリミング・リトライ・レスポンスバリデーションあり
  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュースセンチメント（30%）を合成して日次レジームを market_regime に保存
    - API エラー時はフェイルセーフ
- 研究用（kabusys.research）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン、IC（Information Coefficient）、統計サマリー、ランク処理など

セットアップ
-----------

1. Python バージョン
   - Python 3.10+ を推奨（型ヒントに | を使用しているため）

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   代表的な依存（最小）
   - duckdb
   - openai
   - defusedxml

   （プロジェクト配布時は requirements.txt / pyproject.toml を参照してください）

4. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 必須環境変数（settings で参照されるもの）
     - JQUANTS_REFRESH_TOKEN  (J-Quants のリフレッシュトークン)
     - KABU_API_PASSWORD       (kabu API 用パスワード)
     - SLACK_BOT_TOKEN         (通知用 Slack Bot Token)
     - SLACK_CHANNEL_ID        (通知先 Slack チャンネルID)
   - 任意 / 既定値
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (例: data/monitoring.db)
   - サンプル (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_pwd
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABUSYS_ENV=development

使い方（簡単なコード例）
---------------------

- DuckDB 接続と日次 ETL の実行

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュース NLP スコアリング（特定日）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")  # api_key を省略すると OPENAI_API_KEY を参照
  print(f"書き込んだ銘柄数: {written}")

- 市場レジーム判定

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査ログ DB 初期化（監査専用 DB）

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査テーブルに書き込みが可能

- settings の利用

  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.is_live)

注意点 / 実運用上のヒント
-----------------------
- OpenAI 呼び出し、J-Quants 呼び出しは API キー・レートリミット管理・リトライロジックがありますが、実運用では API コスト・レートに注意してください。
- ETL 実行時は .env に JQUANTS_REFRESH_TOKEN を設定するか、get_id_token に明示的な引数で渡してください。
- news_nlp や regime_detector は LLM に依存するため、レスポンス仕様が変わるとパースに影響します。テスト用に _call_openai_api をモックする設計になっています。
- DuckDB への executemany に関する注意（空リスト不可）やトランザクション取り扱い（init_audit_schema の transactional フラグ）など、コード内コメントを参照してください。

ディレクトリ構成（主要ファイル）
-----------------------------

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュース NLP スコアリング
    - regime_detector.py             -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント + 保存ロジック
    - pipeline.py                    -- ETL パイプライン / run_daily_etl
    - etl.py                         -- ETLResult 再エクスポート
    - quality.py                      -- データ品質チェック
    - calendar_management.py         -- マーケットカレンダー管理
    - news_collector.py              -- RSS ニュース収集
    - audit.py                       -- 監査ログスキーマ / init
    - stats.py                       -- 汎用統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py             -- momentum/value/volatility 計算
    - feature_exploration.py         -- 将来リターン / IC / summary / rank
  - ai、data、research 以下にさらに詳細な実装ファイルあり

ライセンス・貢献
----------------
- この README の配布版にライセンスは含まれていません。実際の配布リポジトリで LICENSE を確認してください。
- 貢献: バグ修正・テスト・ドキュメント改善・新しい ETL コネクタや戦略モジュールの追加を歓迎します。Pull Request 前に issue を立ててください。

さらに詳しく
-------------
- 各モジュールの docstring に設計思想・処理フロー・注意点が詳述されています。実装を利用・拡張する場合は該当モジュールの docstring を参照してください。
- テストを書く際は .env の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を検討してください（テスト環境での副作用を避けるため）。

---
この README はコードベースの主要機能と利用方法をまとめたものです。必要であれば、利用シナリオ別の詳細チュートリアル（初期 ETL 実行、ニュース収集運用、戦略→発注の監査トレース例 など）を追加します。どのトピックを詳しく載せますか？