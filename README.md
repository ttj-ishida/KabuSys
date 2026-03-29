KabuSys
======

日本株の自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）・ニュース収集・LLM による記事スコアリング・市場レジーム判定・リサーチ（ファクター計算）・監査ログ（オーディット）等を提供します。

主な設計方針（要点）
- DuckDB を中心としたローカルデータプラットフォーム（raw_prices / raw_financials / raw_news / market_calendar 等）。
- J-Quants API から差分 ETL（ページネーション・レート制限・トークンリフレッシュ対応）。
- ニュースは RSS 収集→前処理→raw_news に保存、銘柄紐付けしてから LLM（OpenAI）で銘柄別センチメントを算出。
- 市場レジーム判定は ETF（1321）の MA とマクロニュースの LLM センチメントを合成。
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を直接参照しないよう設計）。
- 冪等性（DB 保存は ON CONFLICT / トランザクション制御等を利用）。

主な機能一覧
- データ ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）：取得・保存関数
- データ品質チェック（kabusys.data.quality）
- ニュースの収集・前処理（kabusys.data.news_collector）
- ニュースの LLM スコアリング（kabusys.ai.news_nlp）
  - 銘柄ごとの ai_score を ai_scores テーブルに書き込む
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成し market_regime に保存
- リサーチ用ユーティリティ（kabusys.research）
  - ファクター計算（momentum/value/volatility）
  - forward returns / IC / 統計サマリー 等
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル + 初期化ユーティリティ
- 設定管理（kabusys.config）
  - .env または環境変数から設定を自動ロード（プロジェクトルートの検出ロジックあり）
  - settings オブジェクト経由でアクセス

必須環境変数（代表）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必須。関数引数で渡すことも可）
- KABU_API_PASSWORD: kabu ステーション API パスワード
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に使用
- DUCKDB_PATH（任意）: デフォルト data/kabusys.duckdb
- SQLITE_PATH（任意）: デフォルト data/monitoring.db
- KABUSYS_ENV（任意）: development / paper_trading / live（デフォルト development）
- LOG_LEVEL（任意）: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

自動 .env 読み込みについて
- パッケージが読み込まれる際、プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動で読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で有用）。

セットアップ手順（ローカル開発）
1. Python バージョン
   - Python 3.10+ を推奨（PEP604 型記法等を利用）。

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール（プロジェクトルートに setup/pyproject がある前提）
   - pip install --upgrade pip
   - pip install -e .    # 開発インストール（src 配下のパッケージを editable インストール）
   - 必要な主要依存（明示的な requirements.txt がない場合は個別に）
     - pip install duckdb openai defusedxml

4. 環境変数 / .env の準備
   - プロジェクトルートに .env を作り、必要な値を設定してください。
   - 例 (.env)
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

使い方（簡単な例）
- DuckDB 接続を作成して ETL を実行する例
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（指定日）の実行（OpenAI API キーは環境変数 OPENAI_API_KEY、もしくは api_key 引数で指定）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  # market_regime テーブルに保存される（関数は冪等に日付で DELETE→INSERT を行う）

- 監査ログ DB の初期化（専用 DB）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 必要なら conn を使ってアクセス

設計上の注意点 / 実運用の留意点
- LLM 呼び出し（OpenAI）は API エラー・レート制限に対してリトライを備えていますが、コストやレイテンシを意識してください。テスト時は API 呼び出し関数をモックできます（モジュール内で _call_openai_api をパッチ）。
- ETL は差分＋バックフィル方式です。初回ロード時は J-Quants の全データを取得します（最小日付は _MIN_DATA_DATE）。
- データ品質チェック（kabusys.data.quality）を ETL 後に実行し、発見された問題（QualityIssue）に基づき運用側でアクションを取ってください。
- DuckDB executemany の挙動（空リスト不可など）に配慮した実装がされていますが、DuckDB のバージョンにより振る舞いが異なる可能性があります。
- 自動 .env 読み込みはプロジェクトルート探索に依存します。パッケージ配布後やテスト実行時に不要な読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース LLM スコアリング
    - regime_detector.py      — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント / DuckDB 保存
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の公開
    - news_collector.py       — RSS 収集 / 前処理
    - calendar_management.py  — 市場カレンダー管理・営業日ロジック
    - quality.py              — データ品質チェック
    - stats.py                — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログテーブル定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — forward returns / IC / rank / summary
  - ai/, data/, research/ はそれぞれの公開 API を __all__ で制御

ライセンス / コントリビューション
- （ここではライセンスファイルが示されていません。実プロジェクトでは LICENSE を必ず設置してください）
- プルリクエスト・バグ報告・改善提案はリポジトリの CONTRIBUTING ポリシーに従ってください。

最後に
- この README はコードベースの主要機能・使い方をまとめたものです。実運用ではログ設定、監視、例外ハンドリング、セキュリティ（API キーの取り扱い）を十分に整備してください。質問や具体的な利用例があれば補足します。