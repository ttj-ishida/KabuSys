KabuSys
=======

日本株向けのデータプラットフォーム & 自動売買支援ライブラリです。  
ETL（J-Quants からのデータ取得）／データ品質チェック／ニュース収集・NLP／ファクター計算／監査ログ（発注トレース）等の機能をモジュール化して提供します。

主な目的
- J-Quants API を用いた株価・財務・カレンダー等の差分ETLと DuckDB への永続化
- RSS ニュース収集と OpenAI を用いた銘柄センチメント（AI スコアリング）
- 研究用のファクター計算、将来リターン、IC・統計サマリー
- 監査ログ（signal → order_request → execution）のスキーマ初期化と保持
- データ品質チェック（欠損・スパイク・重複・日付不整合）

機能一覧
- データ取得 / ETL
  - J-Quants API クライアント (jquants_client.py)：株価日足、財務、マーケットカレンダー、上場情報の取得（ページネーション・レート制御・リトライ・トークン自動リフレッシュ対応）
  - ETL パイプライン (pipeline.py / etl.py)：差分取得・保存・品質チェックを統合（run_daily_etl など）
  - カレンダー更新ジョブ (calendar_management.py)
- データ品質
  - quality.py：欠損、スパイク（前日比閾値）、重複、日付整合性チェックと QualityIssue 出力
  - stats.py：Zスコア正規化などの統計ユーティリティ
- ニュース収集 / NLP
  - news_collector.py：RSS 取得、前処理、SSRF対策、DB挿入用整形
  - news_nlp.py：OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - regime_detector.py：ETF（1321）200日MA 乖離とマクロニュースの LLM スコアを合成して市場レジーム判定（score_regime）
- 研究（Research）
  - factor_research.py：Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py：将来リターン計算、IC (Spearman)、統計サマリー、ランク化ユーティリティ
- 監査（Audit / Tracing）
  - audit.py：signal_events / order_requests / executions の DDL 定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - config.py：.env 自動読み込み（プロジェクトルート検出）、環境変数ラッパー settings

セットアップ手順（開発環境）
1. リポジトリをクローン
   - git clone <repo_url>
   - プロジェクトは src/ 配下にパッケージを配置する構成です。

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .\.venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   必要な主要依存（例）:
   - duckdb
   - openai
   - defusedxml
   - そのほか標準ライブラリ外のパッケージやプロジェクト固有の依存があれば requirements.txt にまとめてください。

   例:
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）
4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数 / .env 設定
   プロジェクトルートに .env を置くと自動で読み込まれます（config.py により .git または pyproject.toml を探索してプロジェクトルートを決定）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   必須の環境変数（settings 参照）
   - JQUANTS_REFRESH_TOKEN       （J-Quants リフレッシュトークン）
   - KABU_API_PASSWORD           （kabuステーション API パスワード）
   - SLACK_BOT_TOKEN             （Slack 通知用 Bot トークン）
   - SLACK_CHANNEL_ID            （Slack 通知先チャンネルID）

   任意・デフォルト値あり
   - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO

   OpenAI を使う機能（news_nlp / regime_detector）のための API キーは OPENAI_API_KEY 環境変数に設定するか、関数呼び出し時に api_key 引数で渡してください。

使い方（簡単な例）
- DuckDB 接続を作って ETL を実行（Python REPL / スクリプト内で）
  - 例:
    from datetime import date
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=date(2026,3,20))

- ニューススコアリング（OpenAI キーは環境変数 OPENAI_API_KEY または api_key 引数）
  - 例:
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_count = score_news(conn, target_date=date(2026,3,20))  # OpenAI API key は環境変数から取得

- 市場レジームスコアリング
  - 例:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20))

- 監査スキーマ初期化（監査専用 DB）
  - 例:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成

- ETL の個別実行（価格・財務・カレンダー）
  - from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  - run_prices_etl(conn, target_date=...)
  - run_financials_etl(...)
  - run_calendar_etl(...)

注意点 / 実運用上の事項
- .env 自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動で読みます。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを無効化してください。
- OpenAI 呼び出し:
  - news_nlp と regime_detector はそれぞれ独立した内部 _call_openai_api 実装を持ち、テスト時は unittest.mock.patch で差し替えて容易にモックできます。
  - API 呼び出し失敗時は多くの箇所でフォールバック（スコア 0.0、またはスキップ）するよう設計されていますが、実運用ではレート・コスト管理に注意してください。
- J-Quants クライアント:
  - レート制御（120 req/min）、リトライ（408/429/5xx）、401 時のトークン自動リフレッシュに対応しています。ID トークンは内部キャッシュされます。
- DuckDB 互換性:
  - 一部の executemany 挙動や list バインドの互換性（DuckDB のバージョン差）に注意した実装になっています（空リストバインド回避など）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                   パッケージ定義（version 等）
  - config.py                     環境変数・.env 管理と Settings
  - ai/
    - __init__.py
    - news_nlp.py                 ニュースセンチメント（score_news）
    - regime_detector.py          市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           J-Quants API クライアント（fetch/save）
    - pipeline.py                 ETL パイプライン（run_daily_etl 他）
    - etl.py                      ETL の公開型（ETLResult）
    - calendar_management.py      マーケットカレンダー管理（営業日判定・更新ジョブ）
    - stats.py                    統計ユーティリティ（zscore_normalize）
    - quality.py                  品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py                    監査ログスキーマ定義と初期化
    - news_collector.py           RSS 取得・正規化・前処理
  - research/
    - __init__.py
    - factor_research.py          モメンタム / バリュー / ボラティリティの計算
    - feature_exploration.py      将来リターン / IC / 統計サマリー / ランク
  - monitoring/, execution/, strategy/ (パッケージ公開名は __all__ に含まれていますが、ここに示した以外の実装はプロジェクトに応じて配置されます)

開発 / テストについて
- OpenAI・外部API 呼び出し部分はモックしてユニットテストを行うことを推奨します（news_nlp._call_openai_api, regime_detector._call_openai_api などをパッチする）。
- news_collector はネットワーク・XML パース周りでセキュリティ対策（SSRF 検査、defusedxml、受信サイズ制限）を備えています。テストでは _urlopen を差し替えると HTTP 周りをモックできます。

ライセンス・貢献
- 本リポジトリのライセンス、貢献ポリシーについてはリポジトリのトップレベルにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

付録: 典型的な .env（例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C12345678
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

README に書かれている以外にも各モジュールに詳細な docstring が実装されています。まずは ETL を実行してデータを揃え、研究モジュールやニューススコアリングを順に試してください。必要であれば README をプロジェクト実態に合わせて追記・補強してください。