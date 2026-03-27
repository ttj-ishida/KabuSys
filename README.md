# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群（部分実装）。  
本リポジトリは、データ収集（J-Quants）、ETL パイプライン、データ品質チェック、ニュース NLP（LLM を用いたセンチメント）、市場レジーム判定、監査ログ用スキーマなどのユーティリティを提供します。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（例）
- 環境変数
- ディレクトリ構成
- 設計上の注意点

プロジェクト概要
- 日本市場向けのデータ取得・整形・解析基盤と、AI を使ったニュースセンチメント／市場レジーム判定、監査ログスキーマ等をまとめたライブラリ群です。
- DuckDB をデータレイクとして利用し、J-Quants API からの差分取得・保存、ニュース RSS 収集、品質チェック、各種ファクター計算、AI スコアリングなどを行います。
- バックテストや自動売買システムの上位コンポーネントとして利用できるように、冪等性や Look-ahead バイアス対策を考慮した実装になっています。

主な機能一覧
- 環境変数/設定の読み込みと管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可能）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足、財務データ、JPX カレンダー、上場銘柄情報の取得
  - レート制御・リトライ・トークン自動リフレッシュ・冪等保存機能
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）、個別 ETL（run_prices_etl など）
  - 品質チェック連携・結果集計（ETLResult）
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付整合性のチェックを実装
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、テキスト前処理、SSRF や Gzip/サイズ制限等の安全対策
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions のテーブル定義と初期化
  - init_audit_db による DB 初期化ユーティリティ
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI 関連（kabusys.ai）
  - news_nlp.score_news: ニュースを銘柄ごとに LLM でスコアリングして ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）MA200 とマクロ記事の LLM センチメントを合成して市場レジーム判定
- 汎用統計ユーティリティ（kabusys.data.stats）
  - z-score 正規化など

セットアップ手順
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 以下は主要な依存例（実際の requirements.txt に合わせてください）
     - pip install duckdb openai defusedxml
   - 開発用: pip install -e .
4. 環境変数 (.env) を作成
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要環境変数は下記「環境変数」節を参照してください。
5. データベース用ディレクトリ作成（必要に応じて）
   - デフォルトでは data/kabusys.duckdb（DuckDB）や data/monitoring.db（SQLite）等を参照します。必要に応じて作成またはパスを .env で指定してください。

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI スコアリングに利用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）

（例 .env）
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（簡単な例）
- DuckDB に接続して日次 ETL を実行する
  - Python スクリプト例:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニューススコアリング（LLM を用いる）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
    print(f"scored {count} codes")

- 市場レジーム判定
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")

- 監査ログ DB の初期化
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn を使って order_requests 等にアクセス可能

- 設定値参照
  - from kabusys.config import settings
    token = settings.jquants_refresh_token
    is_live = settings.is_live

設計上の注意点 / 実装上のポイント
- Look-ahead バイアス対策:
  - AI 評価や ETL の内部実装は target_date を明示して過去データのみを参照するよう設計されています（datetime.today()/date.today() を直接参照せず、関数引数で日付を渡す）。
- 冪等性:
  - 保存関数（save_*）は ON CONFLICT DO UPDATE 等で重複を排除し、ETL は部分的に失敗しても既存データを不必要に上書きしないよう工夫されています。
- フェイルセーフ:
  - LLM/API の一時障害やパースエラー時はフォールバック（例: macro_sentiment=0.0）するなど処理継続を優先しています。
- セキュリティ:
  - news_collector では SSRF 防止、受信サイズチェック、defusedxml を用いた XML パース等、安全性に配慮しています。
- ロギング:
  - 各モジュールは logging を使用しており、LOG_LEVEL によって出力を切り替えられます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                         # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      # ニュース NLP スコアリング
    - regime_detector.py               # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                # J-Quants API クライアント・保存処理
    - pipeline.py                      # ETL パイプライン (run_daily_etl など)
    - etl.py                           # ETLResult の再エクスポート
    - news_collector.py                # RSS 取得・前処理
    - calendar_management.py           # マーケットカレンダー関連ユーティリティ
    - quality.py                       # データ品質チェック
    - stats.py                         # 統計ユーティリティ（z-score）
    - audit.py                         # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py               # ファクター計算（momentum/value/volatility）
    - feature_exploration.py           # forward returns, IC, summary, rank
  - （他: strategy, execution, monitoring などのサブパッケージがエクスポートされていますが、本リポジトリの一部実装では未提供の可能性があります）

よくある運用例 / ワークフロー
- 毎朝（夜間バッチ）:
  1. run_daily_etl を実行して市場カレンダー・株価・財務データを更新
  2. ニュース収集と score_news による AI スコアリング
  3. regime_detector による市場レジーム算出
  4. 戦略モジュールが ai_scores / market_regime / 各種ファクターを参照してシグナル生成
  5. 監査ログ（signal_events → order_requests → executions）でトレーサビリティを確保
- 開発中:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動ロードを無効にし、テスト用の環境差し替えを行えます。

補足
- 実運用では OpenAI の利用に伴うコストやレイテンシ、API レート制限に注意してください。
- J-Quants の API レート制御やアクセストークン管理は jquants_client に実装されていますが、利用には J-Quants 側の契約・認証情報が必要です。

質問や追加してほしい節（例: CLI の使い方、CI 設定、テストの書き方など）があればお伝えください。README をその要望に合わせて調整します。