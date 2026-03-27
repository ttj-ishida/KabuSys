KabuSys — 日本株自動売買基盤（README）
=================================

概要
----
KabuSys は日本株向けのデータプラットフォームとリサーチ / 自動売買の基盤コード群です。  
主に以下領域をカバーします。

- J-Quants からの株価・財務・カレンダー等データの差分 ETL
- ニュース収集（RSS）と LLM を用いたニュースセンチメント（銘柄別 ai_score）
- 市場レジーム判定（ETF の MA とマクロニュースを合成）
- リサーチ用のファクター計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック、マーケットカレンダー管理、監査ログ（発注／約定トレース）

機能一覧
--------
主な機能（モジュール別概観）：

- kabusys.config
  - .env ファイルや環境変数の自動ロード（プロジェクトルート検出）
  - 必須設定のラッパー（settings オブジェクト）
- kabusys.data
  - ETL パイプライン（pipeline.run_daily_etl / run_prices_etl / ...）
  - J-Quants API クライアント（jquants_client）: 取得／保存（DuckDB）・認証・リトライ・レート制御
  - ニュース収集（news_collector）: RSS 取得、前処理、raw_news への保存（SSRF/Bomb 対策含む）
  - マーケットカレンダー管理（calendar_management）
  - 品質チェック（quality）: 欠損/スパイク/重複/日付不整合チェック
  - 監査ログ初期化（audit.init_audit_db / init_audit_schema）
  - 汎用統計ユーティリティ（stats.zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM（gpt-4o-mini）でスコアリングして ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースを組み合わせて market_regime に保存
  - API 呼び出しは堅牢なリトライ／フォールバック実装
- kabusys.research
  - ファクター計算（momentum/value/volatility）
  - 将来リターン、IC 計算、統計サマリー等の探索ツール

セットアップ手順
----------------

前提
- Python 3.10 以上（モジュールで | 型ヒントを使用）
- DuckDB（Python パッケージ duckdb）
- OpenAI SDK（openai）を使用する LLM 呼び出し
- defusedxml（RSS パースの安全化）

推奨インストール手順（UNIX 系の例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール（プロジェクトに requirements.txt が無い場合の一例）
   - pip install duckdb openai defusedxml

3. プロジェクトルートに .env ファイルを配置（下記「環境変数」参照）。パッケージ起動時に config が自動で .env をロードします。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須（代表的）環境変数
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知対象チャンネルID
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注等で使用）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）

任意 / デフォルト設定
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env 読み込みを無効化
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルトローカル）

.example .env（参考）
- .env.example を作る際の例:
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=sk-...
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  KABU_API_PASSWORD=your_kabu_password
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

使い方（コード例）
------------------

（1）DuckDB に接続して日次 ETL を実行（データ取得・保存・品質チェック）
- 例:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- run_daily_etl は内部でカレンダー ETL → 株価 ETL → 財務 ETL → 品質チェックを順に実行します。ETLResult が返ります。

（2）ニュースセンチメントスコア（LLM）を生成して ai_scores に保存
- 例:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は環境変数で設定済みであること
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")

（3）市場レジーム判定を実行
- 例:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

（4）監査ログ用 DB 初期化
- 例:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで監査用テーブルが作成されます

運用上のポイント / 注意点
- Look-ahead バイアス防止のため、本コードは内部で date.today() を不用意に参照しない設計になっています。ETL / スコア関数には明示的な target_date を渡すことが望ましいです。
- OpenAI 呼び出しは API 失敗時にフォールバック（0.0 等）する実装がされており、致命的な例外を避けるようにしていますが、API キーやクォータの管理は運用側で行ってください。
- settings は .env または環境変数から読み込みます。プロジェクトルート（.git または pyproject.toml）を起点に自動で .env/.env.local を読み込みます。テスト時に自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants API はレート制限（120 req/min）を内部で遵守する実装です。大量バッチ処理の際はモジュールの RateLimiter に留意してください。

ディレクトリ構成
----------------
（リポジトリの主要ファイル／ディレクトリ）
- src/kabusys/
  - __init__.py
  - config.py                       : 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    : ニュースセンチメント（銘柄別 ai_scores）
    - regime_detector.py             : 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              : J-Quants API クライアント & DuckDB 保存
    - pipeline.py                    : ETL パイプライン（run_daily_etl 等）
    - etl.py                         : ETLResult の再エクスポート
    - news_collector.py              : RSS 収集・前処理
    - calendar_management.py         : マーケットカレンダー管理
    - quality.py                     : データ品質チェック
    - stats.py                       : 統計ユーティリティ（zscore など）
    - audit.py                       : 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py             : ファクター計算（momentum/value/volatility）
    - feature_exploration.py         : 将来リターン / IC / 統計サマリー
  - research/... (その他のリサーチユーティリティ)
  - (そのほか: execution, strategy, monitoring などのパッケージが __all__ に示唆されています)

テスト・開発メモ
----------------
- AI 呼び出し部分は unit test でモックしやすいように設計されています（_call_openai_api の差し替え等）。
- news_collector は SSRF / XML Bomb 等を意識した実装（defusedxml / サイズチェック / プライベートIPチェック）になっています。実ネットでの RSS 収集時は環境のネットワーク設定に注意してください。
- DuckDB の executemany に関する挙動（空リスト不可）を考慮した分岐が実装されています（pipeline/news_nlp 等）。

連絡先・貢献
-------------
この README はコードベースの概要と主要な使い方をまとめたものです。実際の導入・運用では各モジュール内の docstring とログを参照し、必要に応じて環境変数や DB スキーマの初期化（監査 DB 等）を行ってください。バグ報告や機能提案はリポジトリの Issue へお願いします。

---  
以上。必要であれば README.md の英語版、具体的な .env.example ファイル、あるいは requirements.txt を生成します。どれを優先しますか？