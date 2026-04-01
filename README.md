# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買／データプラットフォームのライブラリ群です。
J-Quants からのデータ取得・ETL、ニュースの収集と AI によるセンチメント推定、
リサーチ用ファクター計算、監査ログ（オーディット）や市場カレンダー管理などを
モジュール単位で提供します。

主な設計方針:
- ルックアヘッドバイアス防止（内部で date.today() を不用意に参照しない）
- DuckDB を主要なオンディスク分析 DB として使用
- 外部 API 呼び出しに対して堅牢なリトライ／フェイルセーフ／レート制御
- 冪等性（ETL 保存時は ON CONFLICT / upsert の使用）
- セキュリティ考慮（RSS の SSRF 対策、XML の安全パーシング等）

---

## 機能一覧

- 設定管理
  - 環境変数および .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - Settings オブジェクト経由で設定値にアクセス

- Data（jquants クライアント／ETL）
  - J-Quants API クライアント（認証トークン自動リフレッシュ、レート制御、ページネーション対応）
  - fetch / save 関数: 日次株価、財務データ、上場情報、マーケットカレンダー
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 市場カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS 取得・前処理・SSRF 対策）
  - 監査ログ（audit）テーブルの初期化（init_audit_schema / init_audit_db）

- AI
  - ニュース NLP（score_news）：銘柄別ニュースをまとめて LLM でセンチメント化し ai_scores に書き込み
  - 市場レジーム判定（score_regime）：ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して market_regime に書込

- Research
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns, IC, factor summary, rank）
  - 共通統計ユーティリティ（zscore_normalize）

- ユーティリティ
  - 統計ユーティリティ（zscore 正規化等）
  - ニュース RSS 正規化・前処理

---

## 必要な環境変数

主に Settings クラスで参照される環境変数（.env に設定可能）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI 利用時に必要（score_news / score_regime など）

自動 .env 読み込み:
- パッケージルート（.git または pyproject.toml のあるディレクトリ）から .env, .env.local を順に読み込み
- OS 環境変数が優先され、.env.local は .env を上書きします
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## セットアップ手順（開発環境）

1. リポジトリをクローン／プロジェクトルートへ移動

2. Python 環境を準備（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 主要な使用ライブラリ（例）
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ pyproject.toml / requirements.txt がある場合はそちらを利用してください。

4. プロジェクトを開発モードでインストール（任意）
   - pip install -e .

5. .env を作成
   - .env.example 等を参考に必須値（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）を設定

---

## 使い方（代表的な例）

以下は Python スクリプト内から利用する最小例です。DuckDB 接続を作成して各 API を呼びます。

- ETL 日次実行（株価・財務・カレンダーの差分取得）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントを評価して ai_scores に保存
  - 例:
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
    print(f"wrote {written} scores")

  - score_news は OpenAI API（gpt-4o-mini）を利用します。api_key が渡されない場合は環境変数 OPENAI_API_KEY を参照します。

- 市場レジームを判定して market_regime に保存
  - 例:
    import duckdb
    from datetime import date
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB の初期化
  - 例:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn は監査用テーブルが作成済みの DuckDB 接続

- 市場カレンダーの利用例
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
    conn = duckdb.connect("data/kabusys.duckdb")
    is_td = is_trading_day(conn, date(2026,3,20))
    nxt = next_trading_day(conn, date(2026,3,20))

- リサーチ用ファクター計算
  - from kabusys.research.factor_research import calc_momentum
    records = calc_momentum(conn, date(2026,3,20))

注意:
- API キーやトークンが必要な関数は、引数で明示的に api_key / id_token を渡せます（テスト容易性）。
- OpenAI 呼び出しはリトライ・バックオフを持ちますが、API レスポンスの形式検証に失敗した場合は該当銘柄をスキップするなどフェイルセーフを組み込んでいます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py  (パッケージエントリ、__version__ = "0.1.0")
  - config.py    (環境変数・.env ロード・Settings)
  - ai/
    - __init__.py
    - news_nlp.py         (ニュース NLP / score_news)
    - regime_detector.py  (市場レジーム判定 / score_regime)
  - data/
    - __init__.py
    - jquants_client.py   (J-Quants API クライアント、fetch/save 関数)
    - pipeline.py         (ETL パイプライン / run_daily_etl 等)
    - etl.py              (ETLResult の再エクスポート)
    - calendar_management.py (市場カレンダー管理)
    - quality.py          (データ品質チェック)
    - stats.py            (統計ユーティリティ)
    - news_collector.py   (RSS 収集・前処理)
    - audit.py            (監査ログ/オーディットスキーマ)
  - research/
    - __init__.py
    - factor_research.py  (momentum / volatility / value)
    - feature_exploration.py (forward returns, IC, factor summary, rank)
  - ai, research, data サブパッケージの各種ユーティリティや公開 API

---

## 開発・運用上の注意点

- Look-ahead バイアス対策:
  - ほとんどの関数は target_date を明示的に受け取り、内部で date.today() を不用意に参照しません。バックテスト等での利用に適しています。

- 冪等性:
  - ETL の保存処理は upsert（ON CONFLICT DO UPDATE）で実装されています。

- API レート制御とリトライ:
  - J-Quants では内蔵 RateLimiter によりレートを制御します。API 呼び出しは 3 回リトライ等のロジックを持ちます。

- セキュリティ:
  - RSS 取得は SSRF 対策（リダイレクト検査、プライベート IP ブロック）や defusedxml を用いて安全に実装されています。

- テスト:
  - 外部 API 呼び出しは内部で切り替え可能な関数（_call_openai_api 等）として分離されているため、単体テストではモック置換が容易です。

---

## 参考情報 / よく使う関数（抜粋）

- Settings: kabusys.config.settings
- ETL:
  - kabusys.data.pipeline.run_daily_etl(conn, target_date, id_token=None, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
- J-Quants:
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.save_daily_quotes(conn, records)
- AI:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- Calendar:
  - kabusys.data.calendar_management.is_trading_day(conn, date)
  - next_trading_day, prev_trading_day, get_trading_days
- Audit:
  - kabusys.data.audit.init_audit_db(path)
  - kabusys.data.audit.init_audit_schema(conn, transactional=False)

---

README はここまでです。実際に利用する際は .env の設定、DuckDB のスキーマ（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime などのテーブル）が整っていることを確認してください。必要に応じて追加の初期化 SQL やマイグレーションスクリプトを準備してください。