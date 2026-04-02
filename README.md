KabuSys — 日本株自動売買 / データプラットフォーム
概要
- KabuSys は日本株向けのデータ収集・品質管理・リサーチ・AI ニュース解析・市場レジーム判定・監査ログ（オーダー追跡）などを含むソフトウェア基盤のコアライブラリ群です。  
- 主に DuckDB をデータストアとして、J-Quants API からの ETL、RSS ニュース収集、OpenAI を用いたニュースセンチメント評価、ファクター計算・解析、監査ログスキーマなどを提供します。  
- ルックアヘッドバイアスを避ける設計、堅牢な API リトライ／レート制御、冪等保存（ON CONFLICT）や品質チェックを重視しています。

主な機能一覧
- 環境設定:
  - kabusys.config.Settings: .env / 環境変数読み込み（自動ロード、優先順: OS > .env.local > .env）、必須 env の取得ユーティリティ
- データ ETL / 管理:
  - kabusys.data.pipeline:
    - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl: J-Quants からの差分取得・保存・品質チェック実行
    - ETLResult: 実行結果の構造化
  - kabusys.data.jquants_client:
    - J-Quants API クライアント（認証、ページネーション、レート制御、保存関数: save_daily_quotes, save_financial_statements, save_market_calendar 等）
  - kabusys.data.calendar_management:
    - 営業日判定・翌営業日/前営業日取得・カレンダー更新ジョブ
  - kabusys.data.news_collector:
    - RSS 取得・前処理・raw_news 保存（SSRF対策・サイズ制限・トラッキング除去）
  - kabusys.data.quality:
    - データ品質チェック（欠損、重複、スパイク、日付不整合）と QualityIssue 構造
  - kabusys.data.audit:
    - 監査ログテーブル定義・初期化（signal_events / order_requests / executions）
- AI（OpenAI）関連:
  - kabusys.ai.news_nlp.score_news:
    - ニュースを銘柄ごとに集約し OpenAI (gpt-4o-mini) でセンチメント評価し ai_scores に保存
  - kabusys.ai.regime_detector.score_regime:
    - ETF（1321）の200日MA乖離 + マクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）を判定・保存
  - リトライ、JSON 検証、フェイルセーフ（API失敗時のフォールバック）を実装
- リサーチ／統計:
  - kabusys.research.factor_research:
    - calc_momentum / calc_value / calc_volatility: ファクター計算（モメンタム、バリュー、ATR 等）
  - kabusys.research.feature_exploration:
    - calc_forward_returns / calc_ic / factor_summary / rank: 将来リターン、IC、統計サマリ等
  - kabusys.data.stats.zscore_normalize: クロスセクション Z スコア正規化

セットアップ手順（開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - 必須パッケージの例: duckdb, openai, defusedxml
   - 例: pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）
4. 環境変数 / .env 設定
   - .env.example を参考にプロジェクトルートに .env を作成してください。
   - 自動ロードの仕様:
     - 起点はパッケージファイル位置から上の親ディレクトリで .git または pyproject.toml を探索してプロジェクトルートを特定します。
     - OS 環境変数の優先度 > .env.local > .env
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用）。
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client で使用）
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
     - OPENAI_API_KEY: OpenAI 呼び出しで使用（score_news / score_regime）
   - その他設定（デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live)、LOG_LEVEL、DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（監視用）
5. DuckDB（データベース）準備
   - デフォルトでは data/kabusys.duckdb（settings.duckdb_path）を使用する想定です。必要に応じてパスを変更してください。
   - 監査ログの初期化例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
     - （または既存の DuckDB 接続に init_audit_schema(conn) を呼ぶ）

基本的な使い方（コード例）
- 日次 ETL を実行（Python REPL やスクリプト内で）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    import duckdb
    conn = duckdb.connect(str("data/kabusys.duckdb"))
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())
- ニューススコアリング（OpenAI API キーが環境にある前提）
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,3,20))
    print("scored", n_written)
- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20))
- 監査ログ初期化（既存 DB）
  - from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)
- ファクター計算例
  - from kabusys.research.factor_research import calc_momentum
    records = calc_momentum(conn, date(2026,3,20))

注意点 / 運用上の要点
- OpenAI 呼び出し:
  - gpt-4o-mini を想定した JSON Mode を使用。API レートやエラーに対してリトライ・フォールバックを実装済みですが、API キーは適切に管理してください。
- J-Quants API:
  - レート制限・認証（リフレッシュトークン → id_token の取得）やページネーション対応を実装しています。大量取得時は _RATE_LIMIT_PER_MIN を尊重してください。
- ルックアヘッドバイアス:
  - 多くの関数（score_news/score_regime/ETL/ファクター計算）は内部で date.today() を参照せず、引数で与えた target_date に基づいて処理します。バックテストや再現性のため、必ず target_date を指定して呼ぶことを推奨します。
- 冪等性:
  - save_* 系関数は ON CONFLICT DO UPDATE により冪等保存を行う設計です。
- テスト時:
  - 環境変数自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してテスト用に環境を切り替えやすくしています。
- セキュリティ:
  - news_collector は SSRF 対策（プライベートIP除外、リダイレクト検査）、defusedxml を用いた XML パース保護、受信サイズ制限を備えています。

ディレクトリ構成（主なファイル・概要）
- src/kabusys/
  - __init__.py: パッケージ初期化（version 等）
  - config.py: 環境変数 / Settings クラス、自動 .env ロードロジック
  - ai/
    - __init__.py
    - news_nlp.py: ニュースセンチメント集約・OpenAI 呼び出し・ai_scores 書込
    - regime_detector.py: ETF MA乖離 + マクロニュース合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（取得・保存関数）
    - pipeline.py: ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py: ETLResult の再エクスポートインターフェース
    - news_collector.py: RSS 取得・前処理・raw_news 保存
    - calendar_management.py: 市場カレンダー管理 / 営業日判定 / calendar_update_job
    - quality.py: データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py: zscore_normalize 等の統計ユーティリティ
    - audit.py: 監査ログ（テーブル DDL / 初期化 / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py: モメンタム / バリュー / ボラティリティ等の計算
    - feature_exploration.py: 将来リターン / IC / 統計サマリ
- その他:
  - デフォルトDBパス: data/kabusys.duckdb（settings.duckdb_path）
  - 監視用 sqlite: data/monitoring.db（settings.sqlite_path）

トラブルシューティング / よくある質問
- .env がロードされない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD がセットされていないか確認。プロジェクトルートは .git または pyproject.toml を基準に検出します。
- OpenAI / J-Quants の認証エラー:
  - 環境変数（OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を確認。J-Quants はリフレッシュトークンから id_token を取得するため、get_id_token の呼び出しで 401 を検知した場合は自動リフレッシュを行います。
- DuckDB 保存でエラーが出る:
  - スキーマが未作成のテーブルに対して insert を試みていないか確認。監査ログは init_audit_schema / init_audit_db を使って初期化してください。

貢献・拡張
- 新しいデータソースや解析モジュールは data/ または research/ に追加し、ETL パイプラインに組み込むことを想定しています。外部 API 呼び出し部分はリトライ・レート制御・ログ出力方針を踏襲してください。
- テスト: OpenAI など外部呼び出しはモックしやすいように内部呼び出し関数（例: _call_openai_api）を分離しています。ユニットテストでは該当関数を patch してください。

以上が本コードベースの概要・セットアップ・使い方・ディレクトリ構成の要約です。具体的な運用スクリプト（cron / Airflow / systemd）や requirements.txt、pyproject.toml がプロジェクトにある場合はそれに従って環境構築してください。必要であれば README 内に実行コマンド例や .env.example のテンプレート作成も支援します。