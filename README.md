KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買（研究 → シグナル → 発注）を支援するライブラリ群です。  
主な目的は以下です：

- J-Quants API を使った株価・財務・カレンダーの差分 ETL と DuckDB への保存
- RSS によるニュース収集と OpenAI（gpt-4o-mini）を使ったニュース NLP／市場レジーム判定
- リサーチ用のファクター計算、将来リターン／IC 計算など
- 監査（トレーサビリティ）用の監査テーブル生成と初期化
- データ品質チェック・マーケットカレンダー管理・ニュース収集のユーティリティ

このリポジトリは src/kabusys パッケージとして実装されています。

主な機能一覧
--------------
- data（データプラットフォーム）
  - J-Quants API クライアント（fetch/save, ページネーション、トークンリフレッシュ、レートリミット、リトライ）
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 市場カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
  - ニュース収集: RSS 取得・前処理・raw_news への保存補助（SSRF/サイズ制限/トラッキング除去）
  - データ品質チェック: 欠損・スパイク・重複・日付不整合検出
  - 監査ログ初期化: init_audit_schema / init_audit_db（監査テーブル群とインデックスを作成）
  - 汎用統計: zscore_normalize
- ai（NLP / レジーム検知）
  - news_nlp.score_news: ニュース記事を銘柄ごとに集約し OpenAI に投げて ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime を更新
  - OpenAI 呼び出しはリトライ・バックオフ・JSON モード対応（フェイルセーフでスコアを 0 にフォールバック）
- research（研究用ユーティリティ）
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - .env 自動ロード、必須設定取得ユーティリティ（Settings）

セットアップ手順
----------------
1. リポジトリをクローン（例）
   - git clone <repo-url>
2. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - 必須（主な依存）: duckdb, openai, defusedxml
   - 例: pip install duckdb openai defusedxml
   - 開発用にパッケージ化されている場合: pip install -e .
4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. 必須環境変数（一例）
   - JQUANTS_REFRESH_TOKEN  (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD      (必須) — kabuステーション API のパスワード
   - SLACK_BOT_TOKEN        (必須) — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID       (必須) — 通知先チャンネル ID
   - OPENAI_API_KEY         (推奨) — OpenAI 呼び出しに使用（score_news/score_regime で省略可能）
   - DUCKDB_PATH            (任意, default: data/kabusys.duckdb)
   - SQLITE_PATH            (任意, default: data/monitoring.db)
   - KABUSYS_ENV            (任意, default: development) — 有効値: development, paper_trading, live
   - LOG_LEVEL              (任意, default: INFO) — DEBUG/INFO/WARNING/ERROR/CRITICAL

使い方（簡易例）
----------------

- 基本的な ETL（日次 ETL）の実行例

  - Python セッション内で（DuckDB への接続は duckdb.connect で取得）:

    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")  # または ":memory:"
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())

  - run_daily_etl は市場カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック の順で実行し、ETLResult を返します。

- ニュースを使った AI スコアリング

    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    # OPENAI_API_KEY は環境変数か api_key 引数で指定
    n_written = score_news(conn, target_date=date(2026,3,20))
    print("書込銘柄数:", n_written)

- 市場レジーム判定（MA200 + マクロニュース）

    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20))  # market_regime テーブルを更新

- 監査ログ初期化（監査専用 DB）

    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成
    # conn を使って監査テーブルにアクセス可能

- 市場カレンダーの判定ユーティリティ

    from kabusys.data.calendar_management import is_trading_day, next_trading_day
    import duckdb
    from datetime import date

    conn = duckdb.connect("data/kabusys.duckdb")
    d = date(2026,3,20)
    print(is_trading_day(conn, d))
    print(next_trading_day(conn, d))

設定・自動 .env 読み込みの挙動
------------------------------
- ロード優先順位: OS 環境変数 > .env.local > .env
- パッケージ起点で .env を自動探索して読み込み（プロジェクトルート判定ロジックは .git または pyproject.toml を基準）
- テストや特殊用途で自動ロードを抑止したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

注意点 / 設計上の重要事項
------------------------
- Look-ahead バイアス回避:
  - AI モジュール・ETL・リサーチ関数は内部で date.today() / datetime.today() を直接参照しないよう設計されています。必ず target_date を渡すか、公開 API のデフォルト（多くは「今日」）を理解して使用してください。
- OpenAI 呼び出し:
  - OpenAI API（gpt-4o-mini）を JSON Mode で使い、レスポンスのバリデーションとリトライを行います。API 失敗時はフェイルセーフでゼロ（中立値）を使う設計です。
  - OPENAI_API_KEY は env にセットするか、score_news/score_regime の api_key 引数で与えてください。
- J-Quants API:
  - rate limit（120 req/min）を守るために内部で RateLimiter を実装しています。get_id_token（リフレッシュ）とリトライ処理を備えています。
- DuckDB 互換性:
  - 一部 executemany やクエリは DuckDB のバージョン差分を考慮しています（例: 空リストの executemany 回避など）。

ディレクトリ構成
----------------
（主要ファイルとモジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLU（score_news 等）
    - regime_detector.py              — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（fetch/save 等）
    - pipeline.py                     — ETL パイプライン（run_daily_etl など）
    - etl.py                          — ETL の公開インターフェース（ETLResult）
    - news_collector.py               — RSS 収集 / 前処理
    - calendar_management.py          — 市場カレンダー管理
    - quality.py                      — データ品質チェック
    - stats.py                        — zscore_normalize 等
    - audit.py                        — 監査テーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py              — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py          — calc_forward_returns / calc_ic / factor_summary / rank
  - research/*.py (その他の研究ユーティリティ)
  - その他モジュール（strategy, execution, monitoring 等は __all__ に列挙）

補足（開発者向け）
-----------------
- ログレベルは環境変数 LOG_LEVEL で調整できます（DEBUG/INFO/...）
- KABUSYS_ENV によって本番/ペーパー/開発設定の分岐が可能です（Settings.is_live / is_paper / is_dev を利用）
- テスト時は外部 API 呼び出し関数をモックする設計（内部で _call_openai_api や _urlopen を差し替えられるように実装）になっています

サンプル .env（例）
-------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

最後に
------
この README はコードベースの主要機能と使い方の概要をまとめたものです。個別の関数やクラスの詳細な使い方は該当モジュール内の docstring を参照してください。質問や補足が必要であれば教えてください。