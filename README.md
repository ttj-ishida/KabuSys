# KabuSys

日本株向け自動売買 / データプラットフォーム用のライブラリ群です。ETL、ニュース NLP（LLM）、市場レジーム判定、研究用ファクター計算、監査ログなどを含みます。

概要
- プロジェクト名: KabuSys
- 説明: J-Quants や RSS 等からデータを収集・保存し、DuckDB 上で品質チェック・ETL を行い、LLM（OpenAI）を用いたニュースセンチメントや市場レジーム判定、研究用のファクター計算、監査ログ（トレース可能な約定ログ）を提供するモジュール群。
- 目的: データ取得・前処理・品質確認・ファクター算出・AI スコアリング・監査を一貫して行い、自動売買戦略や研究に利用できる基盤を提供する。

主な機能
- データ取得 / ETL
  - J-Quants API から株価（日足）、財務データ、上場銘柄情報、JPXカレンダーを差分取得・保存（ページネーション・リトライ・レート制御・冪等保存）
  - run_daily_etl による日次 ETL（カレンダー・株価・財務・品質チェック）
- データ品質チェック
  - 欠損検出、スパイク検出、重複検査、日付整合性チェック（market_calendar 対応）
- ニュース収集 / 前処理
  - RSS 収集（SSRF 対策・トラッキング除去・前処理）と raw_news への冪等保存設計（記事ID = 正規化URL の SHA256 部分）
- ニュース NLP（LLM）
  - 銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini 等）に投げ、銘柄別センチメント ai_score を ai_scores テーブルへ保存（バッチ処理・リトライ・レスポンス検証）
  - calc_news_window によるニュース収集ウィンドウ（JST 基準の時間帯）計算
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し daily に 'bull'/'neutral'/'bear' を判定して market_regime に保存
- 研究用モジュール
  - Momentum / Volatility / Value などのファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、ファクター統計要約、Z スコア標準化
- 監査ログ（audit）
  - signal_events, order_requests, executions 等のテーブル定義と初期化ユーティリティ（監査・トレーサビリティ確保）
- 設定管理
  - .env（プロジェクトルート）自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクト経由で環境変数にアクセス

必須環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client に使用）
- OPENAI_API_KEY: OpenAI API キー（score_news, score_regime などで使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（設定に含まれるが本コード中では参照されるプロパティを用意）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（プロジェクトで使用する場合）
- その他:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG / INFO / ...（デフォルト INFO）
  - DUCKDB_PATH, SQLITE_PATH: データベースパス（defaults: data/kabusys.duckdb, data/monitoring.db）

セットアップ手順（開発 / 実行環境）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python バージョン
   - Python 3.10+ を推奨（型ヒントに | を使用）
3. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
4. 依存パッケージをインストール
   - 必要最低限のパッケージ例:
     - pip install duckdb openai defusedxml
   - 実運用では requirements.txt を用意して pip install -r requirements.txt を推奨
5. 環境変数の用意
   - プロジェクトルートに .env を置く（.env.example を参考）
   - 主要な環境変数（上記）を設定
   - 自動読み込みはデフォルト有効。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可
6. ディレクトリの準備
   - data/ フォルダなどを作成（DUCKDB_PATH の親ディレクトリ）
     - mkdir -p data

基本的な使い方（サンプル）
- DuckDB 接続を作る（設定されたパスを利用）
  - from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))
- 日次 ETL を実行
  - from kabusys.data.pipeline import run_daily_etl
    from datetime import date
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())
- ニューススコアリング（LLM）
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    # api_key を引数で渡すか、OPENAI_API_KEY 環境変数を設定
    n_written = score_news(conn, date(2026,3,20), api_key=None)
- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    from datetime import date
    score_regime(conn, date(2026,3,20), api_key=None)
- 監査ログ用 DB 初期化
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db(settings.duckdb_path)  # または別 DB path
- 研究用ファクター計算
  - from kabusys.research.factor_research import calc_momentum
    recs = calc_momentum(conn, date(2026,3,20))

設計上の注意 / 運用メモ
- Look-ahead bias を避けるため、内部実装は date.today()/datetime.today() を直接参照しない関数設計です（target_date を明示的に与えることを推奨）。
- OpenAI 呼び出しはリトライ・フォールバック（失敗時は中立扱い 0.0）等のフェイルセーフを備えていますが、API コストやレート制限に注意してください。
- J-Quants API のレート制御（120 req/min）が組み込まれています。get_id_token によるトークン取得と自動リフレッシュを行います。
- RSS 取得には SSRF 対策、受信サイズ制限、トラッキングパラメータ除去などの保護を入れています。
- DuckDB に対する executemany の空リスト渡しなど、DuckDB のバージョン依存の制約に注意した実装がなされています（空リストは避ける等）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP（score_news）
    - regime_detector.py               — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API client / 保存ロジック
    - pipeline.py                      — ETL パイプライン（run_daily_etl 他）
    - etl.py                           — ETLResult の再エクスポート
    - calendar_management.py           — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py                — RSS 収集 / 前処理
    - quality.py                       — データ品質チェック
    - stats.py                         — Z スコア等統計ユーティリティ
    - audit.py                         — 監査ログテーブル初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py               — Momentum / Volatility / Value 等
    - feature_exploration.py           — 将来リターン / IC / 統計サマリー
  - research/*（その他ユーティリティ）
- data/                                — デフォルトのローカル DB やファイル格納先（推奨）

貢献・開発
- バグ修正 / 機能追加は PR をお願いします。主要なユニットは外部 API 呼び出し部分を抽象化しているため、テスト時はモック差し替えが可能です（各モジュールに差し替えポイントあり）。
- 環境依存の挙動は .env にまとめて管理してください。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

ライセンス
- プロジェクトに同梱の LICENSE ファイルを参照してください（ここにはライセンスの記載は含めていません）。

補足（よくあるコマンド例）
- pip install duckdb openai defusedxml
- python -c "from kabusys.config import settings; import duckdb; conn = duckdb.connect(str(settings.duckdb_path)); print('OK')"

必要に応じて README を具体的な実行例（コマンドラインスクリプト・docker-compose・CI 設定）に拡張できます。特定の用途（例えば ETL の定期実行スクリプトや Slack 通知連携）のサンプルが必要であれば教えてください。