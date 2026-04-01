KabuSys
=======

概要
----
KabuSys は日本株向けのデータパイプライン・リサーチ・AI支援・監査ログを備えた自動売買基盤のライブラリ群です。本コードベースは主に以下を提供します。

- J-Quants API からの株価・財務・上場情報・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- ニュース収集（RSS）とニュースに対する LLM（OpenAI）を用いたセンチメント評価（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロセンチメントの合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索（将来リターン、IC、統計サマリー）
- データ品質チェック・カレンダー管理・監査ログ（発注／約定のトレース用スキーマ）
- 設定管理（.env ファイルの自動読み込み、環境変数経由の設定取得）

主な機能一覧
--------------
- data/jquants_client.py
  - J-Quants API 呼び出し（認証・ページネーション・リトライ・レート制御）
  - save_*/fetch_* 系関数（raw_prices, raw_financials, market_calendar など）※DuckDB へ冪等保存
- data/pipeline.py, data/etl.py
  - 日次 ETL パイプライン（run_daily_etl）と個別 ETL ジョブ（prices / financials / calendar）
  - ETL 結果を ETLResult オブジェクトで返却
- data/news_collector.py
  - RSS 取得・正規化・前処理・raw_news への保存（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
- ai/news_nlp.py
  - 銘柄ごとのニュース結合と OpenAI（gpt-4o-mini）での JSON モードによるセンチメント評価（バッチ処理・リトライ・検証）
- ai/regime_detector.py
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して日次で market_regime テーブルへ書き込み
- research/*
  - ファクター計算（calc_momentum, calc_value, calc_volatility）や特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- data/quality.py
  - 欠損・スパイク・重複・日付不整合などの品質チェックをまとめて実行（run_all_checks）
- data/audit.py
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化（init_audit_schema / init_audit_db）
- config.py
  - .env ファイル（.env, .env.local）または環境変数から設定読み込み（自動読み込みはプロジェクトルート検出に基づく）

セットアップ手順
---------------
前提
- Python 3.10 以上（PEP 604 の型記法や一部記法を利用）
- DuckDB（Python パッケージとしてインストール）
- OpenAI Python SDK（コードは OpenAI の Chat Completions を利用）
- defusedxml（RSS パースでのセキュリティ）
- （任意）その他依存パッケージ（logging 等は標準ライブラリ）

例: 仮想環境作成と依存インストール
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

3. このパッケージを開発モードでインストール（任意）
   - pip install -e .

環境変数（主な設定）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須とするコード箇所あり）
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出し時に使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: sqlite 用パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化可能

.env の自動読み込み
- プロジェクトルート（.git または pyproject.toml を基準）に置いた .env/.env.local を自動で読み込みます。
- .env.local は .env をオーバーライドします（OS 環境変数は保護されます）。

使い方（簡単な例）
-----------------

1) DuckDB 接続を作成して ETL を実行する
- Python REPL またはスクリプト内で:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")  # ファイルがなければ作成
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

2) ニュースセンチメント（AI）で銘柄スコアを生成する

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")  # OpenAI API key 指定可
  print(f"written scores: {written}")

3) 市場レジーム判定を実行する

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

4) 監査ログスキーマの初期化（監査専用 DB）

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit_duckdb.db")
  # テーブルが作成され、UTC タイムゾーンが設定される

注意点 / テスト時の差し替え
- OpenAI 呼び出しは内部で _call_openai_api に集約されており、ユニットテストでは unittest.mock.patch で差し替え可能です（news_nlp と regime_detector は独自実装で分離されています）。
- news_collector はネットワークアクセスや DNS 解決を行うため、テスト時は fetch_rss/_urlopen をモックすることを推奨します。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テストで環境を制御したい場合に便利）。

ディレクトリ構成
----------------
（主要ファイルのみを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数 / .env 管理
  - ai/
    - __init__.py
    - news_nlp.py                  # ニュースセンチメント（銘柄別）
    - regime_detector.py           # 市場レジーム判定（1321 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント + 保存ロジック
    - pipeline.py                  # ETL パイプラインの実装（run_daily_etl 等）
    - etl.py                       # ETL 結果の再エクスポート（ETLResult）
    - news_collector.py            # RSS 収集・前処理
    - calendar_management.py       # 市場カレンダー管理（営業日判定 etc.）
    - stats.py                     # 統計ユーティリティ（zscore_normalize）
    - quality.py                   # データ品質チェック
    - audit.py                     # 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py           # Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py       # 将来リターン / IC / summary / rank
  - research/...                    # 研究用ユーティリティ群

補足 / 設計思想
----------------
- Look-ahead bias を避けるため、関数は内部で date.today() を参照しない設計を優先（target_date を明示して呼ぶことを想定）。
- DuckDB を中心に SQL + Python のハイブリッドで分析処理を実装し、データ量が増えても効率的に処理できる設計。
- 外部 API 呼び出しにはレート制御・リトライ・フォールバックを実装し、ETL の堅牢性を確保。
- LLM 呼び出しは JSON Mode を使い、応答のバリデーションとフォールバック（失敗時は中立値）を行う。

ライセンス / 貢献
-----------------
本リポジトリの README がテンプレートで提供されている場合は LICENSE ファイルに従ってください。貢献や issue 提出は Pull Request ベースで行ってください（詳細はプロジェクトの CONTRIBUTING.md を参照）。

以上。必要であれば、README に含めるコマンド例（systemd サービス定義、CRON ジョブ、Slack 通知の実装例など）や .env.example のサンプルを追記します。どの情報を追加しますか？