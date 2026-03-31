kabusys — 日本株自動売買プラットフォーム（ライブラリ）
================================

概要
----
kabusys は日本株のデータ収集（J-Quants）、データ品質チェック、特徴量計算、ニュースNLP、
市場レジーム判定、監査ログなど「自動売買システム／リサーチ基盤」に必要な共通処理群を
提供する Python パッケージです。  
DuckDB をデータストアとして利用し、OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価、
J-Quants API との安全な連携、RSS ベースのニュース収集、ETL パイプライン等の機能を持ちます。

主な機能一覧
-------------
- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）と必須値チェック（kabusys.config）
- データ取得 / ETL（J-Quants API）
  - 日次株価（OHLCV）取得・保存（差分取得・ページネーション・id_token 自動更新）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存（差分・バックフィル）
  - ETL の統合実行（run_daily_etl）と結果集約（ETLResult）
  - API レート制御・リトライ（指数バックオフ）
- データ品質チェック（data.quality）
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue）
- カレンダー管理（data.calendar_management）
  - 営業日判定 / 前後営業日取得 / 期間内営業日列挙 / SQ判定
- ニュース収集（data.news_collector）
  - RSS 取得、URL 正規化（utm 等除去）、SSRF 対策、Gzip／サイズ上限対策
- AI（ニュース NLP / レジーム判定）
  - 銘柄別ニュースセンチメント算出（ai.news_nlp.score_news）
  - マクロセンチメント + MA200 乖離から市場レジーム判定（ai.regime_detector.score_regime）
  - OpenAI 呼び出しはリトライ・JSON Mode を利用し安全にパース
- リサーチ / ファクター計算（research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Zスコア正規化
- 監査ログ（data.audit）
  - シグナル → 発注 → 約定までトレースする監査スキーマの初期化・DB作成（冪等）
- ユーティリティ
  - 汎用統計関数、データ型変換ユーティリティ 等

セットアップ手順
----------------
前提
- Python 3.10+（型注釈に union 型等を利用）
- DuckDB、openai SDK 等の依存パッケージが必要

1. リポジトリをクローン（またはパッケージを取得）
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) / .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   - pip install -e .    # setup.py / pyproject がある前提で編集インストール
   - または必要なパッケージを個別に:
     - pip install duckdb openai defusedxml

4. 環境変数の準備
   - プロジェクトルートに .env を置くと自動読み込みされます（kabusys.config が .env/.env.local を読みます）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
     - OPENAI_API_KEY=あなたの_openai_api_key
     - KABU_API_PASSWORD=（kabuステーション連携が必要なら）
     - SLACK_BOT_TOKEN=（Slack 通知利用時）
     - SLACK_CHANNEL_ID=（Slack 通知利用時）
   - 任意の設定
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO
   - 自動 .env 読み込みを無効化したい場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例: .env の最小例
    JQUANTS_REFRESH_TOKEN=xxxxx
    OPENAI_API_KEY=sk-xxxxx
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=DEBUG

使い方（主要なユースケース）
---------------------------

1) DuckDB 接続の確保
- 基本的に duckdb.connect(settings.duckdb_path) を使います。

    from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
    from kabusys.data.pipeline import run_daily_etl
    from datetime import date
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())

- run_daily_etl は ETLResult を返し、取得/保存件数・品質問題・エラー情報を含みます。

3) ニュースセンチメントを算出して ai_scores テーブルへ保存
    from kabusys.ai.news_nlp import score_news
    from datetime import date
    n = score_news(conn, target_date=date(2026,3,20))
    print(f"書き込み銘柄数: {n}")

- score_news は前日 15:00 JST ～ 当日 08:30 JST に該当するニュースを対象にします（内部で UTC に変換）。
- OPENAI_API_KEY を環境変数で指定するか、api_key 引数で明示できます。

4) 市場レジーム判定（MA200乖離 + マクロセンチメント）
    from kabusys.ai.regime_detector import score_regime
    from datetime import date
    score_regime(conn, target_date=date(2026,3,20))

- OpenAI API キーは環境変数 OPENAI_API_KEY、または api_key 引数で指定。
- レジームは 'bull' / 'neutral' / 'bear' ラベルで market_regime テーブルに保存されます。

5) 監査ログスキーマ初期化
    from kabusys.data.audit import init_audit_db, init_audit_schema
    conn_audit = init_audit_db("data/audit.duckdb")
    # 既存の接続に追加する場合
    init_audit_schema(conn, transactional=True)

- init_audit_db はディレクトリを自動作成し、UTC タイムゾーンでテーブルを初期化します。

6) ファクター計算・解析（Research 用）
    from kabusys.research import calc_momentum, calc_value, calc_volatility
    from datetime import date
    momentum = calc_momentum(conn, date(2026,3,20))
    # z-score 正規化
    from kabusys.data.stats import zscore_normalize
    normed = zscore_normalize(momentum, ["mom_1m", "mom_3m"])

設計上の重要点（実運用で知っておくこと）
-------------------------------------
- Look-ahead バイアス防止
  - 内部関数は基本的に datetime.today() を直接参照せず、呼び出し側が target_date を渡す設計です。
- J-Quants API
  - id_token は自動取得・キャッシュ・401 で自動リフレッシュします。
  - レート制御（120 req/min）と指数バックオフによるリトライを備えています。
- OpenAI 呼び出し
  - gpt-4o-mini を利用し JSON Mode（response_format）で厳密にパースする想定。
  - 429 / ネットワーク断 / タイムアウト / 5xx はリトライ、パース失敗時はフェイルセーフでスコア 0 を利用する箇所があります。
- ニュース収集の安全対策
  - URL 正規化・トラッキングパラメータ除去、SSRF 対策（プライベートアドレス拒否）、受信サイズ制限、defusedxml による XML 攻撃対策
- ETL は部分失敗に配慮
  - 保存処理は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）で安全に行います。
  - 品質チェックは Fail-Fast ではなく全件収集して呼び出し元に報告します。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py                — パッケージ初期化（バージョン等）
- config.py                  — 環境変数 / .env 自動読み込み / Settings
- ai/
  - __init__.py
  - news_nlp.py              — ニュースセンチメント（score_news）
  - regime_detector.py       — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（fetch/save 関数）
  - pipeline.py              — ETL パイプライン（run_daily_etl 他）
  - etl.py                   — ETL 結果クラス再エクスポート
  - news_collector.py        — RSS ニュース収集
  - calendar_management.py   — 市場カレンダー管理（営業日判定等）
  - quality.py               — データ品質チェック
  - stats.py                 — 統計ユーティリティ（zscore_normalize）
  - audit.py                 — 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py       — Momentum / Value / Volatility 等
  - feature_exploration.py   — 将来リターン, IC, 統計サマリー 等

開発・テストのヒント
-------------------
- 自動 .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（ユニットテストで .env を汚したくない場合に有用）。
- OpenAI / ネットワーク呼び出しはモックしやすいように内部呼び出し（_call_openai_api 等）を分離しています。ユニットテストでは patch を使用して外部依存を置き換えてください。
- DuckDB に対する executemany の空リストは一部バージョンで問題となるため、コードは空時に呼ばない実装になっています。

ライセンス・貢献
----------------
（ここにプロジェクトのライセンス表記や貢献ガイドラインを記載してください）

最後に
------
この README はコードベースから導出した概要・使い方をまとめたものです。実行前に .env の必須値や DuckDB スキーマ（raw_prices/raw_financials/raw_news/ai_scores/market_regime/market_calendar など）が正しく作成されていることを確認してください。サンプルスクリプトや CLI を追加することで運用が容易になります。必要であれば README にサンプルスクリプトを追加しますのでお知らせください。