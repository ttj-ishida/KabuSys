KabuSys — 日本株自動売買プラットフォーム（README）
============================================

概要
----
KabuSys は日本株向けのデータパイプライン、リサーチ、AI ベースのニュース分析、監査ログ基盤、および市場レジーム判定などを備えた自動売買支援ライブラリです。  
主に DuckDB をデータストアとして利用し、J-Quants API からのデータ取得、RSS ニュース収集、OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価、ファクター計算・特徴量解析を行うためのユーティリティ群を提供します。

バージョン
---------
現在のバージョン: 0.1.0（src/kabusys/__init__.py）

主な機能
--------
- データ取得 / ETL
  - J-Quants API からの株価日足、財務データ、JPX カレンダーの差分取得（pagination、リトライ、レート制御対応）
  - ETL 実行用の高レベル API（run_daily_etl 等）と結果を格納する ETLResult
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出と QualityIssue レポート
- ニュース収集
  - RSS フィード収集（SSRF 対策、URL 正規化、トラッキング除去、XML安全パース）
  - raw_news / news_symbols への冪等保存設計
- ニュース NLP（AI スコアリング）
  - OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（ai_scores）を取得・保存する score_news
  - マクロ記事を用いた市場レジーム判定（score_regime） — ETF 1321 の MA200 とマクロセンチメントを合成
  - API 呼び出しのリトライ・フェイルセーフ（失敗時はスコアを 0 として継続）
- 研究用ユーティリティ（Research）
  - Momentum / Value / Volatility 等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Z スコア正規化
- 監査ログ（Audit）
  - signal_events, order_requests, executions を含む監査スキーマの初期化・管理（冪等）
  - 監査DB初期化ユーティリティ（init_audit_db）
- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）、必須環境変数チェック

動作環境・依存
---------------
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI API）を行います。

※ 実際のインストール時は pyproject.toml / requirements.txt を参照してください。

セットアップ手順
---------------
1. リポジトリをクローン・配置
   - 例: git clone ... && cd kabusys

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （パッケージ構成に合わせて追加の依存をインストールしてください）

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）に .env または .env.local を配置すると自動読み込みされます。
   - 自動ロードを無効化する場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主要な環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須、ETL/jquants_client で使用）
     - OPENAI_API_KEY        : OpenAI API キー（AI モジュールで使用）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（発注関連）
     - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite（デフォルト data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH など（監視・実行制御）
   - .env のパースルール:
     - export KEY=val 形式に対応。クォートやコメントの扱いはモジュール内ロジックに従います。

使い方（代表的な例）
-------------------

Python から直接呼び出す基本例を示します。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取る設計です。

1) DuckDB に接続して ETL を日次実行
- 例:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())

2) ニュースセンチメントを生成（score_news）
- 必要: OPENAI_API_KEY を環境変数で設定（または api_key 引数で注入）
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")

- 備考: API 呼び出しに失敗した銘柄はスキップされる設計です。chunk サイズや最大リトライはモジュール内定数で制御。

3) 市場レジーム判定（score_regime）
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

4) 監査DB を初期化する
- 例:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events, order_requests, executions テーブル等が作成されます

5) RSS フィード取得（ニュース収集の一部）
- 例:
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

注意事項
- OpenAI / J-Quants の API キー・トークンが必須な処理があります（未設定時は ValueError を投げます）。
- AI モジュールは API 呼び出しに対して堅牢化（リトライ・フォールバック）を組み込んでいますが、コストやレート制限に注意してください。
- research モジュールはバックテスト・解析用であり、発注や本番アカウントにはアクセスしません（安全設計）。
- .env 自動ロードはプロジェクトルートを .git または pyproject.toml から探索します。配布後も CWD に依存しない実装です。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下の主要モジュール）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py            — 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py     — マクロ + MA200 で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & DuckDB 保存関数
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）・ETLResult
    - etl.py                 — ETLResult を再エクスポート
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py      — RSS 収集と前処理
    - quality.py             — データ品質チェック（QualityIssue）
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - audit.py               — 監査スキーマ作成・初期化
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/ (上記)
  - その他（strategy / execution / monitoring 等のパッケージを __all__ で提供予定）

設計上のポイント（抜粋）
-----------------------
- ルックアヘッドバイアス対策: 各モジュールは date 引数ベースで動作し、datetime.today()/date.today() を直接参照しない箇所が多い（バックテスト対応）。
- 冪等性: DB への保存は ON CONFLICT / INSERT … DO UPDATE の形で設計されている（重複防止）。
- フェイルセーフ: AI / API 呼び出しの失敗は基本的に例外を伝播させず、安全なデフォルト値（0.0 など）で継続する方針。
- セキュリティ: RSS 取得における SSRF 防止、XML の安全パーサ（defusedxml）を使用等の対策あり。

開発・貢献
----------
- 開発環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして .env の自動読み込みを抑制できます（テスト等）。
- ユニットテストや CI は別途整備してください（本リポジトリの README に含まれていません）。

付録: よく使う環境変数（まとめ）
------------------------------
- JQUANTS_REFRESH_TOKEN (必須 for ETL)
- OPENAI_API_KEY (必須 for AI モジュール; score_news / score_regime)
- KABU_API_PASSWORD, KABU_API_BASE_URL
- DUCKDB_PATH (例: data/kabusys.duckdb)
- SQLITE_PATH (監視用)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

最後に
------
この README はコードベースに基づく概要と利用上のポイントを簡潔にまとめたものです。実運用・本番運用する際は API キーの管理、ログ監視、レート・コストの観点から十分な運用設計を行ってください。さらに具体的な使い方や CLI、デプロイ手順は別途ドキュメント化することを推奨します。