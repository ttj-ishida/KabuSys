KabuSys — 日本株自動売買システム
================================

本ドキュメントは、提供されたコードベース（kabusys）についての README です。
プロジェクト概要、機能一覧、セットアップ手順、主要な使い方、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
---------------
KabuSys は日本株向けのデータプラットフォームと自動売買（リサーチ・シグナル生成・監査・注文管理）を支援するライブラリ群です。  
主に以下を目的とします：

- J-Quants API からのデータ取得（株価日足・財務データ・マーケットカレンダー）
- DuckDB を用いたデータ保存・ETL パイプライン
- ニュース収集と自然言語処理（OpenAI を用いたセンチメント評価）
- 市場レジーム判定（ETF ベースのテクニカル + マクロニュース LLM）
- ファクター計算・特徴量探索（研究用ユーティリティ）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- データ品質チェック・カレンダー管理等の補助機能

主要設計方針：
- ルックアヘッドバイアス（未来情報参照）を避ける設計
- DuckDB を中心に SQL と軽量 Python 実装で完結
- API 呼び出しはリトライ・レート制御・フェイルセーフあり
- 冪等性（Idempotency）を重視した DB 保存

機能一覧
--------
主なモジュールと提供機能（抜粋）：

- kabusys.config
  - .env ファイル/環境変数の読み込み（自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - アプリ設定の一元化（J-Quants / OpenAI / Slack / DBパス / 監視閾値 等）

- kabusys.data
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン自動更新）
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar など
    - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB 保存・冪等）
  - pipeline: ETL 管理（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策・gzip 対応）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定・next/prev_trading_day・calendar 更新ジョブ
  - audit: 監査ログ用スキーマ初期化（signal_events / order_requests / executions）
  - stats: zscore_normalize 等の統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュースを LLM で銘柄別にセンチメント化して ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA 乖離とマクロニュース LLM を合成して市場レジームを判定

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（研究用統計）

セットアップ手順
----------------
1. Python 環境準備
   - 推奨: Python 3.10+ を使用
   - 仮想環境を作成して有効化する例：
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（代表的なもの）
   - pip install duckdb openai defusedxml
   - 必要に応じて他のパッケージ（logging 等は標準ライブラリ）を追加
   - 実際のプロジェクトでは requirements.txt / pyproject.toml が望ましい

3. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を配置すると自動読み込みされます（kabusys.config が .git または pyproject.toml を基に自動探索）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 必須の主な環境変数（例）：
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（fetch API 用）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector 用）
     - KABU_API_PASSWORD: kabuステーション API パスワード（注文実行系）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知（任意）
   - DB 関連（任意、デフォルト値あり）
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)

   - 例 .env（安全に管理してください）:
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - OPENAI_API_KEY=sk-xxxxx
     - KABU_API_PASSWORD=passwd
     - DUCKDB_PATH=data/kabusys.duckdb
     - LOG_LEVEL=INFO
     - KABUSYS_ENV=development

4. DuckDB データベースの初期化
   - 監査ログ専用 DB を初期化する一例（Python）:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

使い方（主要ユースケース）
------------------------

- DuckDB 接続を作る（例）:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）:
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - # ETLResult オブジェクトから結果を参照できます: result.to_dict(), result.has_errors

- ニュースのスコアリング（OpenAI 必須）:
  - from kabusys.ai.news_nlp import score_news
  - n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None なら OPENAI_API_KEY を参照

- 市場レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査スキーマの初期化（既存 DB に監査テーブルを追加）:
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

- RSS フィードからニュースを取得する（news_collector.fetch_rss）:
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

- カレンダー関連ユーティリティ:
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  - is_trading = is_trading_day(conn, date(2026,3,20))

- 研究用ファクター計算:
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - momentum_records = calc_momentum(conn, target_date=date(2026,3,20))

設定と注意点
--------------
- 環境変数の自動ロード:
  - kabusys.config はプロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を自動ロードします。
  - テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
  - .env.local は .env より優先して上書きされます（ただし OS の環境変数は保護されます）。

- OpenAI 呼び出し:
  - gpt-4o-mini を想定した JSON Mode（response_format={"type":"json_object"}）で実行しています。
  - API エラー時には再試行・フォールバックロジックが入っています（失敗時はスコア 0.0 等で継続）。

- J-Quants API:
  - レート制限（120 req/min）を厳守するため内部で固定間隔のスロットリングを行います。
  - 401 受信時はリフレッシュトークンから ID トークンを再取得して 1 回リトライします。

- DuckDB について:
  - 一部の操作で executemany に空リストを渡せない実装上の制約を考慮しています（空リストはチェックしてスキップ）。

- セキュリティ:
  - RSS の取得は SSRF 対策（プライベートアドレス検査、リダイレクト検査）を行っています。
  - XML 解析は defusedxml を使用して XML Bomb 等の攻撃を防いでいます。

ディレクトリ構成
----------------
（重要ファイルを中心に抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数 / 設定管理
    - ai/
      - __init__.py
      - news_nlp.py        — ニュース NLP（センチメント）
      - regime_detector.py — 市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py       — J-Quants API クライアント & 保存ロジック
      - pipeline.py             — ETL パイプライン（run_daily_etl 等）
      - etl.py                  — ETL 結果クラス公開
      - news_collector.py       — RSS 収集・整形
      - calendar_management.py  — マーケットカレンダー補助
      - quality.py              — データ品質チェック
      - audit.py                — 監査ログスキーマ初期化
      - stats.py                — 統計ユーティリティ（zscore_normalize 等）
    - research/
      - __init__.py
      - factor_research.py      — ファクター計算（momentum/value/volatility）
      - feature_exploration.py  — 将来リターン / IC / 統計サマリー
    - (その他: strategy/ execution/ monitoring の名前空間が __all__ に記載されていますが、ここでは data/ai/research を中心に実装)

補足（開発・拡張のヒント）
--------------------------
- 単体テスト:
  - OpenAI 呼び出しや外部 HTTP は patch / mock を使って差し替え可能な設計になっています（内部 _call_openai_api や _urlopen 等）。
- ログレベル:
  - 環境変数 LOG_LEVEL を使ってログレベルを制御できます（config.settings.log_level）。
- 本番稼働時:
  - KABUSYS_ENV を paper_trading / live に切り替えて挙動を変えることができます（settings.is_live / is_paper）。
- スキーマ初期化:
  - audit.init_audit_db/ init_audit_schema を使って監査DBを初期化してください。

以上が本コードベースの概要と使い方です。具体的な拡張や実運用の統合（ブローカー接続、戦略実装、ジョブスケジューラとの連携など）はこの基盤を参照して実装してください。必要であれば README に追加するサンプル .env.example や簡易の起動スクリプト、依存関係一覧（requirements.txt）も作成できます。ご希望あれば作成します。