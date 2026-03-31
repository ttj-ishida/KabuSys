KabuSys — 日本株自動売買プラットフォーム（README）
概要
- KabuSys は日本株向けのデータ基盤・リサーチ・AI スコアリング・監査ログ・ETL を備えたライブラリ群です。
- 主な目的は「J-Quants 等の外部データ取得 → DuckDB へ保存 → 解析／ファクター計算／AI スコアリング → 監査ログ／発注連携に向けた下支え」を提供することです。
- コードベースは以下のレイヤーで構成されています：
  - data: ETL、J-Quants クライアント、カレンダー、ニュース収集、データ品質チェック、監査ログなど
  - ai: ニュース NLP（銘柄別センチメント）および市場レジーム判定（MA + LLM）
  - research: ファクター計算・特徴量探索ユーティリティ
  - config: 環境変数／設定管理

主な機能一覧
- データ取得（J-Quants API）
  - 日足（OHLCV）、財務情報、上場銘柄情報、マーケットカレンダーをページネーション対応で取得
  - レート制限（120 req/min）やリトライ、401 自動リフレッシュに対応
- ETL パイプライン
  - 差分更新・バックフィル、品質チェック、カレンダー先読み、結果の ETLResult レポート
- データ品質チェック
  - 欠損（OHLC）、スパイク（前日比）、重複、日付整合性チェック
- ニュース収集
  - RSS 取得（SSRF 対策、URL 正規化、トラッキング除去、記事ID生成）、raw_news への冪等保存想定
- AI スコアリング
  - ai.news_nlp.score_news: 銘柄ごとのニュースをまとめて LLM（gpt-4o-mini）でセンチメント算出 → ai_scores に保存
  - ai.regime_detector.score_regime: ETF 1321 の MA とマクロニュースの LLM センチメントを合成して市場レジーム（日次）を生成
  - 両者とも JSON Mode を使う想定でリトライ・フェイルセーフ実装あり
- リサーチ／ファクター
  - momentum / volatility / value 等のファクター計算、将来リターン計算、IC（Spearman）や統計サマリー
  - stats.zscore_normalize によるクロスセクション正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions などの監査テーブルを冪等で初期化するユーティリティ
  - init_audit_schema / init_audit_db を提供

セットアップ手順（ローカル開発向け）
1. Python 環境
   - 推奨: Python 3.10+
2. 依存ライブラリをインストール
   - 主要な依存: duckdb, openai, defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - 実際のプロジェクトでは requirements.txt / pyproject.toml に従ってください。
3. 環境変数 / .env
   - ルート（.git または pyproject.toml があるディレクトリ）にある .env / .env.local を自動読み込みします（config モジュール）。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必須環境変数（Settings が要求する）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API パスワード
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知先 Slack
   - 任意（デフォルトあり）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development, paper_trading, live）
     - LOG_LEVEL（DEBUG/INFO/...）
   - .env.example を参考に .env を作成してください。
4. データベース初期化（監査ログ等）
   - 監査テーブルを初期化する最短例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - 既存の DuckDB 接続へスキーマだけ適用する:
     - from kabusys.data.audit import init_audit_schema
     - import duckdb; conn = duckdb.connect("data/kabusys.duckdb"); init_audit_schema(conn)
5. J-Quants 認証確認
   - get_id_token() を呼んで ID トークンが取得できることを確認してください（settings.jquants_refresh_token が必要）。

基本的な使い方（コード例）
- DuckDB 接続を作って ETL を実行する（日次 ETL）
  - import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())
- AI ニューススコアを作る
  - from kabusys.ai.news_nlp import score_news
    score_count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None だと OPENAI_API_KEY を参照
- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20), api_key=None)
- リサーチ関数（ファクター計算など）
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    momentum = calc_momentum(conn, target_date=date(2026,3,20))
- ニュース RSS 取得（単独）
  - from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
- J-Quants API の直接利用
  - from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
    token = get_id_token()
    quotes = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
- データ品質チェック
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=date(2026,3,20))
    for i in issues: print(i)

設計上の注意点（挙動・制約）
- Look-ahead bias 防止:
  - 多くの処理（news window, MA 計算, ETL の日付処理）は date.today()/datetime.now() の直接参照を避け、明示的な target_date を受け取る設計です。バックテストでの使用時は target_date を必ず指定してください。
- 冪等性:
  - ETL → 保存処理（save_*）は ON CONFLICT DO UPDATE 等で冪等に設計されています。複数回実行してもデータが重複しません。
- レート制限・リトライ:
  - J-Quants クライアントは 120 req/min の制御とリトライ（指数バックオフ、401 の場合はトークンリフレッシュ）を備えています。OpenAI 呼び出しもリトライ戦略を持ちます。
- フェイルセーフ:
  - AI 呼び出し失敗時はゼロスコアにフォールバックする等、処理全体の停止を避ける実装が多いです。詳細は各モジュールの docstring を参照してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — 銘柄別ニュースセンチメント算出
    - regime_detector.py         — 市場レジーム判定（ETF MA + マクロ LLM）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API client + 保存ユーティリティ
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult 再公開
    - calendar_management.py     — マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py          — RSS 収集・前処理
    - quality.py                 — データ品質チェック
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py         — Momentum/Value/Volatility 計算
    - feature_exploration.py     — 将来リターン・IC・統計サマリー
  - research/__init__.py
- そのほか:
  - .env, .env.local, .env.example（プロジェクトルート）
  - pyproject.toml 等（存在する場合）

トラブルシュート（よくある問題）
- 環境変数未設定エラー
  - settings の必須プロパティは _require() を通して ValueError を投げます。JQUANTS_REFRESH_TOKEN / SLACK_* / KABU_API_PASSWORD 等が未設定だと起こります。
- OpenAI 呼び出しの失敗
  - OPENAI_API_KEY が設定されているか確認してください。API 呼び出しは JSON Mode を期待するため、レスポンスのパースエラーが発生することがあります（フェイルセーフで 0 にフォールバックする設計）。
- DuckDB への接続エラー
  - 指定パスの親ディレクトリを作成しておくか、init 関数にて自動作成されることを確認してください（audit.init_audit_db は親ディレクトリを作成します）。

開発・コントリビュート
- 各モジュールの docstring に設計意図・想定動作・エッジケースが詳述されています。変更時は docstring とユニットテスト（想定）を合わせて更新してください。
- テストは外部 API 呼び出しをモックする前提で設計されています（例: ai の _call_openai_api をパッチするなど）。

参考
- 設定値は kabusys.config.settings 経由で参照してください。
- 詳細な関数仕様・リカバリロジックは各モジュール（docstring）を参照してください。

必要であれば README を英語化、または具体的な例（.env.example のテンプレート、簡易スクリプト）を追加で作成します。どの追加情報が欲しいか教えてください。