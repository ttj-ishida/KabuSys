KabuSys — 日本株自動売買プラットフォーム（README）
=================================================

概要
----
KabuSys は日本株を対象としたデータパイプライン・リサーチ・AI/NLP・監査・発注周りのユーティリティをまとめたライブラリです。
主に以下の役割を持ちます：

- J-Quants API からの株価 / 財務 / カレンダー取得（差分 ETL）
- RSS ベースのニュース収集と前処理
- OpenAI を用いたニュースセンチメント（銘柄単位）とマクロセンチメントの評価
- 市場レジーム判定（MA200 とマクロセンチメントの合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order → execution トレース）用スキーマ初期化ユーティリティ

バージョン: 0.1.0

主な機能一覧
-------------
- data.jquants_client
  - J-Quants API への安全な問い合わせ（レートリミット・リトライ・トークン自動リフレッシュ）
  - fetch / save 関数: 日足、財務、上場情報、カレンダー
- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー・株価・財務の差分取得と品質チェックを一括実行
  - 個別 ETL ヘルパー（run_prices_etl / run_financials_etl / run_calendar_etl）
- data.news_collector
  - RSS 取得・前処理・SSRF 対策・トラッキングパラメータ除去
- data.quality
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue を返す）
- data.calendar_management
  - market_calendar に基づく営業日判定、next/prev_trading_day、get_trading_days 等
- data.audit
  - 監査ログ用の DDL と初期化関数（init_audit_schema / init_audit_db）
- ai.news_nlp
  - ニュース集合を銘柄単位で LLM に投げて ai_scores テーブルに書き込む（score_news）
- ai.regime_detector
  - ETF 1321 の MA200 乖離とマクロセンチメントを合成して日次の市場レジームを算出（score_regime）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility 等）
  - 特徴量解析（forward returns, IC, factor summary, rank）
- config
  - .env 自動読み込み（プロジェクトルート判定）と環境設定ラッパ（settings）

セットアップ手順
----------------

前提
- Python 3.10+（PEP 604 の型構文などを使用しているため）
- DuckDB、OpenAI SDK、defusedxml など外部ライブラリ

1) リポジトリ/パッケージをインストール
   - 開発環境であればプロジェクトルートで:
     - pip install -e .
     - または必要パッケージを個別にインストール:
       - pip install duckdb openai defusedxml

2) 環境変数 / .env
   - ルート（.git または pyproject.toml のあるディレクトリ）に置かれた .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須（少なくとも ETL / AI を動かす場合）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注周りに必要）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知用（必要に応じて）
     - OPENAI_API_KEY — OpenAI を使う処理に必須（news_nlp / regime_detector）
   - オプション:
     - KABUSYS_ENV: development / paper_trading / live（既定: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（既定: INFO）
     - DUCKDB_PATH（既定: data/kabusys.duckdb）
     - SQLITE_PATH（既定: data/monitoring.db）

3) データベース
   - 監査ログ用の DB はコードから初期化可能:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / prices_daily / market_regime 等のスキーマは本 README に含まれていません。ETL を実行するには対応するスキーマを事前に DB に作成しておく必要があります（プロジェクトの DataPlatform ドキュメントにスキーマ定義がある想定）。

使い方（簡単な例）
-----------------

- 日次 ETL を実行する（DuckDB 接続を渡す）
  - from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントを生成して ai_scores に書き込む
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026, 3, 20))
    print("scored:", count)

- 市場レジームをスコアリングして market_regime に保存
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))

- 監査スキーマを初期化（監査用 DB）
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn を使って監査テーブルへ書き込み/読み出しが可能

- 研究用ユーティリティ
  - from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
    # DuckDB 接続と target_date を渡して呼び出す

主要 API のポイント
- OpenAI 呼び出しには環境変数 OPENAI_API_KEY を使用（関数引数で上書き可能）。
- ETL や AI モジュールは「ルックアヘッドバイアス」を防ぐ設計:
  - 内部で datetime.today()/date.today() を直接参照しない（引数で target_date を渡す）。
- J-Quants クライアントはレートリミット・リトライ・401 リフレッシュ対応済み。
- news_collector は SSRF 対策・XML の安全パース・トラッキングパラメータ除去などを実装。

重要な挙動 / 設定
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を読み込みます。
  - 読み込みを停止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings（kabusys.config.settings）経由で主要設定へアクセスできます（例: settings.jquants_refresh_token）。
- DuckDB 側の一部処理は executemany に対する空リストを避けるなど DuckDB の挙動に配慮しています。

ディレクトリ構成
----------------
（主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP スコアリング（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult の再エクスポート
    - news_collector.py            — RSS ニュース収集
    - calendar_management.py       — マーケットカレンダー管理
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum / value / volatility）
    - feature_exploration.py       — 将来リターン / IC / summary / rank

補足 / 注意事項
---------------
- 本 README はコードベースの実装を元に概要をまとめたものです。実運用で動かすには、DB スキーマ（raw_prices 等）や外部サービス（J-Quants / OpenAI / kabuステーション）のアクセス情報を正しく整備してください。
- ETL・発注・AI 周りは実際の資金が動く処理を含むため、live 環境では十分なテストとログ監視・エラーハンドリングを行ってください（KABUSYS_ENV=live で運用モード判定）。
- 監査ログは削除しない前提で設計されています。トレーサビリティを保つため必ず監査テーブルを運用してください。

ライセンス・貢献
----------------
- ライセンス情報や貢献ルールはプロジェクトルートのファイル（LICENSE / CONTRIBUTING.md 等）を参照してください（このリポジトリに含まれる想定）。

お問い合わせ
------------
- 実装に関する質問や不具合報告はリポジトリの Issue にお願いします。