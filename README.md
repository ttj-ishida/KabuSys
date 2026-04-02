# KabuSys

日本株向け自動売買／データプラットフォームライブラリ

概要
- KabuSys は日本株のデータ取得（J-Quants）、ETL、品質チェック、ニュース NLP、マーケットレジーム判定、研究用ファクター計算、監査ログなどをまとめたライブラリ群です。
- コードベースは DuckDB を内部データストアとして使用し、OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析やレジーム判定機能を提供します。
- 設計上、バックテストやデータ取得でルックアヘッドバイアスが入らないよう配慮されています（target_date の明示や strict なウィンドウ指定など）。

主な機能
- データ ETL
  - J-Quants から株価（日足）・財務データ・市場カレンダーの差分取得（ページネーション対応、再取得/バックフィル対応）。
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）。
  - run_daily_etl による一括 ETL と品質チェック（欠損・スパイク・重複・日付不整合）。
- カレンダー管理
  - market_calendar に基づく営業日判定、next/prev_trading_day、get_trading_days、SQ 判定。
  - calendar_update_job による夜間バッチ更新。
- ニュース収集／NLP
  - RSS フィード取得（SSRF 対策・gzip 対応・トラッキングパラメータ除去）と前処理ユーティリティ。
  - OpenAI を用いたニュースごとのセンチメント（ai_scores への書き込み）: kabusys.ai.news_nlp.score_news
  - マクロニュース + ETF（1321）200日 MA 乖離を合成した市場レジーム判定: kabusys.ai.regime_detector.score_regime
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査スキーマを DuckDB に初期化して、シグナル→発注→約定のトレースを保持
  - init_audit_db / init_audit_schema による初期化ユーティリティ
- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定）と Settings クラス経由のアクセス

セットアップ手順（開発時）
1. Python バージョン
   - Python 3.10 以上を推奨（型アノテーションに | を使用しているため）。
2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージ（代表例）
   - pip install duckdb openai defusedxml
   - 実プロジェクトでは requirements.txt / pyproject.toml からインストールしてください。
4. 環境変数
   - プロジェクトルートに .env（または .env.local）を置くと、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（Settings で _require されているもの）
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（発注等で使用）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : Slack チャンネル ID
   - その他（デフォルトあり）
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG/INFO/...）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - OpenAI を使用する機能は OPENAI_API_KEY を環境にセットするか、score_news / score_regime に api_key 引数で渡してください。

簡単な使い方（例）
- 基本的な DuckDB 接続と ETL 実行
  - from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントのスコアリング（OpenAI API 必須）
  - from kabusys.ai.news_nlp import score_news
    # api_key を None にすると環境変数 OPENAI_API_KEY を参照
    n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査 DB の初期化（監査用別 DB）
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" 指定も可能

- カレンダー関連ユーティリティ
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
    is_business = is_trading_day(conn, some_date)
    nxt = next_trading_day(conn, some_date)
    days = get_trading_days(conn, start_date, end_date)

運用上の注意
- 自動環境変数読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索し、.env / .env.local を自動で読み込みます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- OpenAI 呼び出し
  - news_nlp / regime_detector は gpt-4o-mini を想定しており、JSON mode 形式を利用します。API エラー（429, 5xx, タイムアウト等）は再試行ロジックとフォールバック（0.0）を内蔵しています。
- J-Quants API
  - レート制限（120 req/min）や 401 リフレッシュ処理、ページネーションの取り扱いを jquants_client が担います。refresh token は JQUANTS_REFRESH_TOKEN に設定してください。
- DuckDB
  - 一部の実装は DuckDB のバージョン差異（executemany の空リスト扱いなど）に配慮していますが、本番環境での動作確認を行ってください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                       - 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュース NLP（score_news）
    - regime_detector.py            - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント & DuckDB 保存
    - pipeline.py                   - ETL パイプライン（run_daily_etl, run_*_etl）
    - etl.py                        - ETLResult 再エクスポート
    - stats.py                      - 統計ユーティリティ（zscore_normalize）
    - quality.py                    - データ品質チェック
    - calendar_management.py        - カレンダー管理（is_trading_day 等）
    - news_collector.py             - RSS 取得・前処理
    - audit.py                      - 監査テーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py            - ファクター計算（momentum/value/volatility）
    - feature_exploration.py        - 将来リターン, IC, 統計サマリ
  - ai/（上に示した）
  - research/（上に示した）

テスト・開発メモ
- 自動ロードされる .env を無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテストでの環境独立化に有用）。
- ニュース NLP / レジーム検出の OpenAI 呼び出しは再現性のため mock 可能な設計になっています（内部の _call_openai_api を patch してテストしてください）。
- DuckDB のスキーマ初期化や監査スキーマの作成には init_audit_schema / init_audit_db を利用してください。

免責と運用注意
- 本ライブラリは売買システムの一部を構成します。実際に売買を行う場合は発注・約定ロジック、リスク管理、法令遵守（金融商品取引法等）を十分に整備してください。
- 実口座での自動発注は重大なリスクを伴います。paper_trading 環境で十分な検証を行った上で live 環境へ移行してください（KABUSYS_ENV により挙動を分離）。

補足
- README に示したコマンドや依存は最小限の例です。実環境では pyproject.toml / requirements.txt に記載される正確な依存バージョンに従ってセットアップしてください。
- 追加の使用方法や API の詳細は各モジュールの docstring を参照してください（コード内に詳細設計・処理フローの説明が含まれています）。

もし特定の機能の使い方サンプル（ETL の cron 設定例、Slack 通知の仕組み、kabu API を使った発注フローのサンプルなど）が欲しければ、目的を教えてください。より具体的な README 例や運用手順を作成します。