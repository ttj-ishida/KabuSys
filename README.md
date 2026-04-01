KabuSys — 日本株自動売買プラットフォーム (README)
================================

概要
----
KabuSys は日本株向けのデータETL、ニュースNLP、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ管理などを備えたライブラリ群です。  
主に以下用途を想定しています。

- J-Quants からの株価／財務／カレンダーの差分ETL
- RSS ニュース収集と銘柄ごとの LLM（OpenAI）によるセンチメント評価
- マクロニュースとETF（1321）MA200乖離による市場レジーム判定
- ファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）用の DuckDB スキーマ初期化

機能一覧
--------
主な機能（モジュール別）

- kabusys.config
  - .env または環境変数から設定読み込み（自動ロード、無効化可）
  - アプリ設定（J-Quants トークン、OpenAI、DBパス、監視閾値など）

- kabusys.data
  - jquants_client: J-Quants API クライアント（差分取得・保存・ページネーション・リトライ・レート制御）
  - pipeline: 日次ETL run_daily_etl（カレンダー → 株価 → 財務 → 品質チェック）
  - calendar_management: JPX カレンダー管理と営業日ユーティリティ（is_trading_day 等）
  - news_collector: RSS 収集（SSRF 対策・URL 正規化・トラッキング除去・前処理）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: 監査ログ（signal_events/order_requests/executions）スキーマ初期化・DB作成
  - stats: Zスコア正規化など汎用統計

- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime に保存

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility（prices_daily / raw_financials を使用）
  - feature_exploration: 将来リターン計算、IC、統計サマリー、ランク化ユーティリティ

セットアップ手順
----------------

前提
- Python 3.10 以上（型注釈で PEP 604 の `|` を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最小）
   - pip install duckdb openai defusedxml

   （プロジェクトで追加のライブラリが必要なら requirements.txt を用意して pip install -r requirements.txt）

3. 開発インストール（任意）
   - プロジェクトルートに pyproject.toml があれば:
     - pip install -e .

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（必須: ETL・jquants_client に使用）
- OPENAI_API_KEY
  - OpenAI API キー（news_nlp / regime_detector に使用）
- KABU_API_PASSWORD
  - kabuステーション API パスワード（発注系を統合する場合）
- KABU_API_BASE_URL
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - Slack 通知に使用
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
  - 監視閾値（デフォルトは config 内に定義）
- KABUSYS_ENV
  - 環境 ("development" | "paper_trading" | "live")（デフォルト development）
- LOG_LEVEL
  - ログレベル ("DEBUG","INFO",...、デフォルト INFO)

.env の自動読み込み
- プロジェクトルート（.git または pyproject.toml 基準）に .env / .env.local を置くと自動で読み込まれます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（よく使う例）
-------------------

以下は簡単な利用例。スクリプトやジョブ内で呼び出して使用します。

- DuckDB 接続の取得例
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（pipeline.run_daily_etl）
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=date(2026,3,20))
  - print(result.to_dict())

- ニュースセンチメントのスコア付け
  - from datetime import date
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(str(settings.duckdb_path))
  - count = score_news(conn, target_date=date(2026,3,20))
  - print(f"scored {count} codes")

- 市場レジーム判定
  - from datetime import date
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - score_regime(conn, target_date=date(2026,3,20))

- 監査DB（audit）初期化
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")
  - # 以後 conn を使って監査テーブルへアクセス

- RSS フィード取得（news_collector.fetch_rss）
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

注意点 / ヒント
- AI（OpenAI）を使う機能には OPENAI_API_KEY が必須です。無い場合は ValueError が発生します。
- J-Quants からのデータ取得には JQUANTS_REFRESH_TOKEN が必要です。get_id_token() を内部で使います。
- ETL / AI 呼び出し関数はルックアヘッドバイアスを避ける設計（内部で date.today() に依存しない）になっています。target_date を明示的に渡して使うことを推奨します。
- news_collector は SSRF 対策、トラッキング除去、最大レスポンスサイズ制限等の防衛処理があります。
- DuckDB executemany に対する空リスト取り扱いなど、バージョン差異に注意（コード内で互換性対策済み）。

ディレクトリ構成（主なファイル）
------------------------------

src/kabusys/
- __init__.py
- config.py                 — 環境変数/設定管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py             — ニュースNLP（score_news）
  - regime_detector.py      — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（fetch/save）
  - pipeline.py             — ETL パイプライン（run_daily_etl 他）
  - etl.py                  — ETLResult 再エクスポート
  - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
  - news_collector.py       — RSS ニュース収集
  - quality.py              — データ品質チェック
  - stats.py                — 統計ユーティリティ（zscore_normalize）
  - audit.py                — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py      — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py  — calc_forward_returns / calc_ic / factor_summary / rank

補足（依存関係・開発）
---------------------
- 主要依存: duckdb, openai, defusedxml（その他標準ライブラリ）
- Python 3.10 以上を推奨
- パッケージは src レイアウトです。pyproject.toml/requirements.txt がプロジェクトにあればそれに従ってください。

問い合わせ / 貢献
-----------------
バグ報告や機能提案はリポジトリの issue にお願いします。プルリク歓迎です。コードベースには十分なログ出力とフェイルセーフ処理が組み込まれているため、変更時はユニットテストと動作ログを確認してください。

以上。必要なら README へ追記するサンプル .env.example や具体的なスクリプト例（systemd ジョブ、 cron、Airflow の DAG 例など）を作成します。どれを追加しましょうか？