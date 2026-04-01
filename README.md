KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株のデータ取得（J-Quants）、データ品質チェック、特徴量算出、ニュースNLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、監査ログ（発注〜約定の追跡）などを含む自動売買・研究基盤ライブラリです。モジュール化されており、ETL パイプラインや研究（ファクター算出）、AI ベースのニュース解析、監査ログ初期化などを Python API として提供します。

主な特徴
--------
- J-Quants API 経由のデータ取得（株価日足 / 財務 / 上場情報 / マーケットカレンダー）
  - レート制限対応・リトライ・トークン自動リフレッシュ
- DuckDB を使った ETL パイプライン（差分更新 / バックフィル / 品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理、記事 → 銘柄紐付け
  - SSRF 対策・サイズ制限・トラッキングパラメータ除去済み
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析と市場レジーム判定
  - JSON Mode を使った堅牢なパース・リトライ処理を実装
- 研究用ユーティリティ（モメンタム/ボラティリティ/バリュー等のファクター計算、将来リターン、IC、Zスコア正規化など）
- 監査ログスキーマ（signal_events / order_requests / executions）を DuckDB に冪等で初期化するユーティリティ
- 環境変数・設定管理（.env/.env.local の自動読み込み、各種閾値やパスの設定）

必須環境
--------
- Python 3.10 以上（型注釈に | を使用）
- 必要パッケージ（主なもの）:
  - duckdb
  - openai
  - defusedxml
- 他、標準ライブラリ（urllib 等）を使用

セットアップ手順
---------------
1. リポジトリのクローン / 配布パッケージをインストール
   - 開発環境であれば editable インストール:
     - pip install -e .

2. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

3. 環境変数の準備
   - プロジェクトルートに .env（または .env.local）を用意してください。
   - 自動読み込み:
     - kabusys.config モジュールはプロジェクトルートを .git または pyproject.toml を基準に探索し、.env と .env.local を自動で読み込みます。
     - テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 必須環境変数（少なくとも下記を設定してください）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime の呼出しに必要）
   - KABU_API_PASSWORD     : kabuステーション API のパスワード（発注系使用時）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知を使う場合

5. 任意の設定（デフォルト有り）
   - KABUSYS_ENV (development | paper_trading | live) — 実行モード
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
   - DUCKDB_PATH — データ用 DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
   - PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

簡単な使い方（コード例）
-----------------------

- 設定の取得
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path 等が利用可能

- DuckDB 接続
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=some_date)
  - ETLResult オブジェクト（取得数 / 保存数 / 品質問題 / errors を含む）

- ニュースのスコアリング（OpenAI 必須）
  - from kabusys.ai.news_nlp import score_news
  - score_cnt = score_news(conn, target_date=some_date, api_key="...")  # api_key を省略すると OPENAI_API_KEY を参照

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - ret = score_regime(conn, target_date=some_date, api_key="...")

- ファクター計算・研究用ユーティリティ
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary, rank
  - momentum = calc_momentum(conn, target_date=some_date)

- 監査ログ初期化
  - from kabusys.data.audit import init_audit_schema, init_audit_db
  - conn_audit = init_audit_db(settings.duckdb_path)  # または既存 conn に対して init_audit_schema(conn)

- ニュース収集（RSS）単体呼出し
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss(url, source="yahoo_finance")

注意点（実運用・開発でのポイント）
--------------------------------
- OpenAI 呼び出し
  - API の失敗や JSON パース失敗に対してフェイルセーフ（0.0 等）で継続する実装です。ただし、キー未設定は例外になります。
  - テスト時は内部の _call_openai_api をモックして応答を差し替えてください（news_nlp / regime_detector 共にモック可能に設計）。
- J-Quants API
  - レート制限（120 req/min）に合わせた内部 RateLimiter を持ちます。401 時はリフレッシュを行って再試行します。
- ニュース収集
  - SSRF 対策（リダイレクトチェック、プライベートホスト拒否）や受信サイズ制限を実装済みです。
- DuckDB の executemany に空リストを渡すと互換性問題が出るため、ライブラリ内で空チェックを行っています（呼出し側も同様の注意を）。
- 環境変数読み込み
  - .env/.env.local は自動的にプロジェクトルート（.git または pyproject.toml）から読み込まれます。
  - 上書き順序: OS 環境 > .env.local > .env。OS 環境を保護するため .env.local は上書きオプションあり。
- ログレベル・実行モード
  - settings.env / settings.is_live などで動作モードを切り替えられます。テスト環境では KABUSYS_ENV=development を使用してください。

ディレクトリ構成（主なファイル）
-------------------------------
src/kabusys/
- __init__.py                — パッケージ定義（version 等）
- config.py                  — 環境変数 / 設定管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py              — ニュースの NLP スコアリング（score_news）
  - regime_detector.py       — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（fetch / save 関数群）
  - pipeline.py              — ETL パイプライン（run_daily_etl 等）
  - etl.py                   — ETLResult の再エクスポート
  - news_collector.py        — RSS 取得・前処理・挿入ロジック
  - calendar_management.py   — マーケットカレンダー管理 / is_trading_day 等
  - quality.py               — データ品質チェック（check_missing_data 等）
  - stats.py                 — zscore_normalize 等の統計ユーティリティ
  - audit.py                 — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py       — momentum/volatility/value の計算
  - feature_exploration.py   — forward returns / IC / summary / rank
- ai/、research/ 以下に各種ユーティリティや公開 API を備えています。

主要 API（抜粋）
----------------
- data.pipeline.run_daily_etl(conn, target_date=None, ...)
  - 日次 ETL を実行し ETLResult を返す
- data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - ページネーション対応のデータ取得
- data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
  - DuckDB へ冪等保存
- data.news_collector.fetch_rss(url, source, timeout=30)
  - RSS を取得して前処理したニュース一覧を返す
- ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ニュースを銘柄ごとにスコア化し ai_scores に保存
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - MA200 とマクロニュースセンチメントを合成して market_regime に保存
- data.audit.init_audit_schema(conn, transactional=False)
  - 監査ログ用テーブルを初期化
- research.factor_research.calc_momentum / calc_volatility / calc_value
  - ファクター計算

開発・テストのヒント
--------------------
- 自動 .env 読み込みを無効化する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI のコールをモックする:
  - unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api", mock_fn) のように差し替えてテストできます（regime_detector も同様）。
- DuckDB は :memory: でインメモリ DB を使えます（init_audit_db(":memory:") など）。

ライセンス・貢献
----------------
（この README に含めるべき具体的なライセンス情報やコントリビュート手順がなければ、プロジェクトの LICENSE ファイルと CONTRIBUTING を参照してください。）

最後に
------
この README はソースの主要モジュールに基づいて作成しています。実際の実行やデプロイ時は .env.example（存在する場合）や各種ドキュメント（DataPlatform.md / StrategyModel.md 等）を参照のうえ、API キーとデータベースパスを正しく設定してください。必要なら、サンプルスクリプトや CLI を追加して運用手順を明文化することを推奨します。