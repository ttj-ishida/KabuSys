KabuSys — 日本株自動売買プラットフォーム（README 日本語版）
================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・AIスコアリング・監査ログ・ETL を備えた
自動売買／研究用ライブラリ群です。J-Quants API を用いた株価・財務・カレンダーの差分取得、
ニュース収集と LLM によるニュース／マクロ評価、ファクター計算・特徴量探索、監査ログ（約定追跡）
などをモジュール化して提供します。

主な設計方針
- ルックアヘッドバイアス対策（内部で date.today()/datetime.today() を直接参照しない等）
- DuckDB をデータストアに想定した SQL + Python 実装
- 冪等性（ON CONFLICT / UUID ベースのキー等）
- フェイルセーフ（外部API失敗時のフォールバック）
- テスト容易性（API 呼び出しの差し替えポイントを確保）

機能一覧
--------
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）
  - 必須環境変数の取得ラッパー、実行環境 (development/paper_trading/live) チェック
- データ ETL (kabusys.data.pipeline, jquants_client)
  - J-Quants API からの株価/財務/カレンダー取得（ページネーション・レート制御・リトライ）
  - DuckDB への冪等保存（raw_prices, raw_financials, market_calendar 等）
  - run_daily_etl による日次パイプライン（カレンダー→株価→財務→品質チェック）
- データ品質チェック (kabusys.data.quality)
  - 欠損、スパイク、重複、日付不整合などを検出して QualityIssue を返却
- ニュース収集 (kabusys.data.news_collector)
  - RSS 取得、URL 正規化、SSRF 保護、記事前処理、記事ID生成
- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - signal_events / order_requests / executions テーブル定義、初期化ユーティリティ
  - init_audit_db で専用 DuckDB を初期化
- 研究・ファクター (kabusys.research)
  - momentum / value / volatility 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - zscore 正規化ユーティリティ
- AI スコアリング (kabusys.ai)
  - score_news: ニュースを銘柄ごとに LLM でセンチメント化して ai_scores に保存
  - score_regime: ETF（1321）の MA200 乖離 + マクロ記事の LLMセンチメントで市場レジーム判定
  - OpenAI API 呼び出しは gpt-4o-mini（JSON mode）を想定、リトライ／フェイルセーフ実装
- その他ユーティリティ
  - カレンダー管理（営業日判定／next/prev/get_trading_days）
  - 統計ユーティリティ（zscore_normalize）

セットアップ手順
---------------
前提
- Python 3.10 以上（ソースの型ヒントで | 演算子を使用）
- DuckDB を使用（pip パッケージ duckdb）
- OpenAI SDK（openai）を AI 機能で使用
- defusedxml（ニュースパーシングで推奨）

推奨インストール手順（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. 開発インストール（ソースルートで）
   - pip install -e .

環境変数 / .env
- 推奨はプロジェクトルートに .env を配置すること（config モジュールが自動ロードします）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要な環境変数
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: 通知先チャンネル ID（必須）
- DUCKDB_PATH: デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: 実行環境（development, paper_trading, live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で参照）

使い方（コードスニペット）
-----------------------

1) DuckDB 接続を作成して日次 ETL を実行
- 例:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

2) ニュースの AI スコアリングを実行（score_news）
- OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、api_key 引数で渡す
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  score_count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {score_count} codes")

3) 市場レジーム評価を実行（score_regime）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))

4) 監査ログ DB を初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

5) ニュース RSS を取得（保存ロジックを組み合わせて利用）
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])

注意点
- score_news / score_regime: OPENAI_API_KEY が未設定だと ValueError が発生します。
- J-Quants 関連関数（fetch_* / save_*）は settings.jquants_refresh_token を参照します。
- run_daily_etl は内部でカレンダーを先に取得し、営業日調整を行います。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため
  関数内で空チェックを行っています（ユーザ側での意識は不要）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                    — ニュース NLP スコアリング（score_news）
  - regime_detector.py             — 市場レジーム判定（score_regime）
- research/
  - __init__.py
  - factor_research.py             — モメンタム/バリュー/ボラティリティ等
  - feature_exploration.py         — 将来リターン、IC、統計サマリー
- data/
  - __init__.py
  - calendar_management.py         — 市場カレンダー管理（営業日判定等）
  - etl.py                         — ETLResult 再エクスポート
  - pipeline.py                    — 日次 ETL パイプライン（run_daily_etl 等）
  - stats.py                       — zscore_normalize など
  - quality.py                     — データ品質チェック
  - audit.py                       — 監査ログテーブル定義・初期化
  - jquants_client.py              — J-Quants API クライアント & 保存関数
  - news_collector.py              — RSS 取得・前処理・安全対策

追加の注意・運用上のヒント
------------------------
- ローカル開発では .env と .env.local をプロジェクトルートに置くことで設定を管理できます。
  自動ロードは config モジュールで行われ、OS 環境変数が優先されます。
- 本番稼働（live）では KABUSYS_ENV=live を設定して安全チェックを有効にしてください。
- OpenAI のコストとレート制限に留意してください（score_news はバッチ化、チャンク処理あり）。
- J-Quants API はレート制限・トークン期限があるため、設定トークンとログを運用で監視してください。

貢献・開発
----------
- バグ修正・機能追加、テストの追加は歓迎します。PR を送る際はコードの目的・再現手順を明記してください。
- 外部 API 呼び出し箇所には差し替え可能なラッパーがあるため、テスト時はモックを使ってください（例: kabusys.ai.news_nlp._call_openai_api を patch）。

ライセンス
---------
- 本リポジトリのライセンス情報はリポジトリルートの LICENSE を参照してください（ここでは明示されていません）。

お問い合わせ
------------
- 実装や使い方で不明点があれば、この README に記載の関数やモジュールを参照の上、ご質問ください。

以上。README の初期案として必要があれば、実行例のスクリプト（systemd タイマー / cron 用）や .env.example のテンプレート、requirements.txt の自動生成案も作成します。必要であれば教えてください。