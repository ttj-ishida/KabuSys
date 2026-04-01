# KabuSys

日本株向け自動売買 / データ基盤ライブラリ KabuSys のリポジトリ向け README（日本語）

バージョン: 0.1.0

概要
----
KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、ETL、ニュース NLP（OpenAI を利用した銘柄センチメント評価）、市場レジーム判定、ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供する Python コードベースです。バックテスト・研究環境および本番の注文実行基盤に組み込めるモジュール群を含みます。

主な設計方針
- ルックアヘッドバイアスを避けるため datetime.today()/date.today() を直接参照しない実装
- DuckDB を用いたローカルデータストア
- J-Quants API / OpenAI API 呼び出しに対する堅牢なリトライ・フェイルセーフ処理
- 冪等的な DB 書き込み（ON CONFLICT / DELETE→INSERT 等）
- 外部 API キーは環境変数または .env で管理（自動読み込みの仕組みあり）

機能一覧
--------
- データ取得 / ETL
  - J-Quants からの株価日足（OHLCV）、財務データ、JPX カレンダー取得（jquants_client）
  - 差分更新・バックフィル・品質チェックをまとめた run_daily_etl パイプライン
- データ品質
  - 欠損、重複、日付不整合、スパイク検出（data.quality）
- ニュース収集 / NLP
  - RSS 取得・前処理（SSRF 対策・トラッキング除去等）と raw_news への保存に向けたユーティリティ（data.news_collector）
  - OpenAI を使った銘柄ごとのニュースセンチメント評価（ai.news_nlp.score_news）
- レジーム判定
  - ETF 1321 の 200 日 MA 乖離 + マクロニュースの LLM センチメントを合成して市場レジームを判定（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算（research.factor_research）
  - 将来リターン計算、IC 計算、統計サマリー（research.feature_exploration, data.stats）
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ（data.audit）
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings API（config）

前提・要件
-----------
- Python 3.10 以上（typing の | 演算子などを使用）
- 主要依存ライブラリ（pip インストールが必要）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の他パッケージが将来追加される可能性あり）

セットアップ手順
----------------
1. リポジトリのクローン（例）
   - git clone <repo-url>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージのインストール（プロジェクト側で requirements.txt があればそれを使用）
   - pip install duckdb openai defusedxml
   - （ローカル開発向けに）pip install -e .
4. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（config.py の自動読み込み）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. データベース準備
   - デフォルトの DuckDB ファイルパスは data/kabusys.duckdb（settings.duckdb_path）。
   - 監査ログ用独立 DB を初期化するには data.audit.init_audit_db を利用できます。

主な環境変数
-------------
必須（ライブラリ／各機能を使う場合に必要）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 実行時）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector）
- SLACK_BOT_TOKEN : Slack 連携がある場合
- SLACK_CHANNEL_ID : Slack 通知先チャンネルID
- KABU_API_PASSWORD : kabuステーション等と連携する場合のパスワード

任意・デフォルトあり
- KABU_API_BASE_URL : デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH : data/kabusys.duckdb（settings.duckdb_path）
- SQLITE_PATH : data/monitoring.db
- PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV : development / paper_trading / live（デフォルト development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

注意: config.Settings からこれらは型付きで取得され、未設定の必須項目は ValueError を投げます。

使い方（簡易サンプル）
--------------------

共通：DuckDB 接続を使う
- 例: conn = duckdb.connect(str(settings.duckdb_path))

1) 日次 ETL 実行
- from datetime import date
- from kabusys.data.pipeline import run_daily_etl
- conn = duckdb.connect(str(settings.duckdb_path))
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

2) ニューススコアリング（AI）
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- conn = duckdb.connect(str(settings.duckdb_path))
- n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")

3) 市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- from datetime import date
- conn = duckdb.connect(str(settings.duckdb_path))
- score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")

4) 研究用ファクター計算
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- conn = duckdb.connect(str(settings.duckdb_path))
- momentum = calc_momentum(conn, date(2026, 3, 20))
- value = calc_value(conn, date(2026, 3, 20))

5) 監査ログ初期化（監査専用 DB）
- from kabusys.data.audit import init_audit_db
- conn_audit = init_audit_db("data/audit.duckdb")

注意点・運用上のヒント
---------------------
- ETL などは対象テーブル（raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / market_regime 等）が存在することを前提としています。これらのスキーマは別途準備してください（監査テーブルのみ data.audit.init_audit_schema / init_audit_db で初期化可能）。
- OpenAI 呼び出しは API の可用性に依存します。モジュール内ではリトライ・フォールバック（スコア 0.0 等）を取り入れていますが、料金やレート制限に注意してください。
- J-Quants API にはレート制限があり、クライアントは内部で固定間隔スロットリングを行います（_RateLimiter）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。CI / テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による無効化を推奨します。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP（score_news）
  - regime_detector.py            — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント（fetch / save）
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - etl.py                        — ETLResult の再エクスポート
  - calendar_management.py        — 市場カレンダー管理
  - news_collector.py             — RSS 収集ユーティリティ
  - quality.py                    — データ品質チェック
  - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
  - audit.py                      — 監査ログ（テーブル定義 / 初期化）
- research/
  - __init__.py
  - factor_research.py            — Momentum/Value/Volatility 等
  - feature_exploration.py        — 将来リターン / IC / 統計サマリー
- (将来的に) strategy/, execution/, monitoring/ などのサブパッケージが想定される

貢献・拡張
-----------
- 新しい ETL 対応、ニュースソース追加、OpenAI プロンプト改善、研究用指標追加などは歓迎します。
- 大きな API 変更やスキーマ変更を行う際は既存のデータ互換性（特に DuckDB スキーマ）に注意してください。

ライセンス
---------
- 本リポジトリのライセンス情報はリポジトリルートの LICENSE を確認してください（ここには記載していません）。

お問い合わせ
-------------
実装や使い方に関する質問は issue を立てるか、プロジェクトのメンテナにお問い合わせください。

以上。README に記載して欲しい追加の内容（例: 具体的な DB スキーマ SQL、CI 手順、開発用の docker-compose など）があれば教えてください。