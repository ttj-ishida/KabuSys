KabuSys
======

日本株向けのデータ基盤・研究・自動売買（戦略→発注監査）を補助する Python ライブラリ群です。  
本リポジトリは主に以下の領域をカバーします：データ ETL（J-Quants）、ニュース収集・NLP（OpenAI）、ファクター計算・リサーチ、監査ログ（発注／約定トレーサビリティ）、市場カレンダー管理 等。

要点
- DuckDB をデータストアとして利用する ETL / データ品質チェック機能
- J-Quants API 経由で株価・財務・カレンダーを差分取得・保存するクライアントとパイプライン
- RSS ベースのニュース収集と OpenAI を使った銘柄別/マクロのセンチメント評価
- ファクター計算（モメンタム／ボラティリティ／バリュー等）・特徴量探索ユーティリティ
- 監査テーブル（signal → order_request → execution）の初期化と管理

主な機能一覧
- データ取得・保存
  - J-Quants API クライアント（jquants_client）
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar など
    - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
- ETL パイプライン
  - run_daily_etl（カレンダー取得 → 株価ETL → 財務ETL → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
  - ETLResult（実行結果の集約）
- データ品質チェック（quality）
  - 欠損・重複・スパイク・日付不整合の検出（QualityIssue を返す）
  - run_all_checks でまとめて実行
- ニュース収集（news_collector）
  - RSS フィード取得（SSRF 対策、トラッキングパラメータ除去、受信サイズ制限）
  - raw_news への冪等保存 + news_symbols との紐付け（実装参照）
- ニュース NLP（ai.news_nlp）
  - calc_news_window、score_news：銘柄別ニュースをまとめて OpenAI に投げ、ai_scores に書き込む
  - バッチ処理、JSON mode、リトライ・バリデーションを実装
- 市場レジーム判定（ai.regime_detector）
  - ETF（1321）200日移動平均乖離とマクロ記事センチメントを合成して market_regime を算出・保存
- リサーチ（research）
  - calc_momentum / calc_volatility / calc_value 等のファクター算出
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- カレンダー管理（data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間差分更新
- 監査ログ（data.audit）
  - 監査テーブル DDL とインデックス、init_audit_schema / init_audit_db による初期化

セットアップ手順（開発環境）
- 推奨 Python バージョン
  - Python 3.10 以上（型注釈で | 演算子を使用しているため）
- 必須パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで動く箇所もありますが、上記は本プロジェクトの主要機能で必要）
- 仮想環境作成・依存関係インストール（例）
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install duckdb openai defusedxml
  - （開発用に他のパッケージが必要なら requirements.txt を用意してください）

環境変数 / .env の取り扱い
- 本パッケージはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を検出して、
  自動的に .env → .env.local を読み込み、環境変数を設定します（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 必須の環境変数
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード（発注実装がある場合）
  - SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
  - SLACK_CHANNEL_ID: Slack チャンネル ID
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を呼ぶ際に指定がない場合に参照）
- 任意（デフォルト値あり）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト INFO）
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: デフォルト data/monitoring.db
- .env のサンプル（README 用例）
  - JQUANTS_REFRESH_TOKEN=your_refresh_token
  - OPENAI_API_KEY=sk-...
  - SLACK_BOT_TOKEN=xoxb-...
  - SLACK_CHANNEL_ID=C01234567
  - KABU_API_PASSWORD=your_password
  - KABUSYS_ENV=development
  - LOG_LEVEL=INFO

基本的な使い方（コード例）
- DuckDB 接続を開く / ETL 実行（日次 ETL）
  - from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())
- ニューススコアリング（OpenAI API キーは環境変数か引数で渡す）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
    print("wrote", n_written)
- 市場レジーム判定
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
- 監査ログ DB 初期化（監査用の独立 DB を作る）
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn を使って監査テーブルに書き込み可能
- リサーチ関数の利用例（モメンタム）
  - from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    records = calc_momentum(conn, target_date=date(2026, 3, 20))
    # records: list[dict] を解析して研究・集計に利用

注意点 / 設計方針の要約
- ルックアヘッドバイアス回避
  - 多くの関数が内部で datetime.today()/date.today() に依存せず、引数として target_date を受け取る設計です。バックテスト用途では対象日を明示してください。
- 冪等性
  - ETL 保存処理は ON CONFLICT DO UPDATE（DuckDB）で設計されており、差分実行や再実行に強い設計です。
- フェイルセーフ
  - OpenAI / J-Quants の API 呼び出しが失敗した場合でも、適切にフォールバックまたは部分失敗にとどめるロジックがあります（ログ出力・スキップ等）。
- セキュリティ対策
  - RSS フェッチ周りは SSRF 対策（ホストチェック・リダイレクト検証）、受信サイズ制限、defusedxml を利用して安全性を高めています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                         : 環境変数読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py                      : ニュースセンチメント分析（銘柄別）
    - regime_detector.py               : 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                : J-Quants API クライアント + DuckDB 保存
    - pipeline.py                      : ETL パイプライン（run_daily_etl 等）
    - etl.py                           : ETLResult 再エクスポート
    - news_collector.py                : RSS ニュース収集
    - quality.py                       : データ品質チェック
    - calendar_management.py           : 市場カレンダー管理
    - stats.py                         : 共通統計ユーティリティ
    - audit.py                         : 監査テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py               : ファクター計算（momentum/value/volatility）
    - feature_exploration.py           : 将来リターン・IC・統計サマリー等
  - research/*（その他ユーティリティ群）
- その他
  - pyproject.toml / setup.cfg 等（プロジェクトルート検出用）
  - .env / .env.local （ローカル設定）

よくある運用フロー（例）
1. .env を準備（J-Quants / OPENAI / Slack などのキーを設定）
2. DuckDB（data/kabusys.duckdb）を用意
3. 日次バッチで run_daily_etl を実行してデータを更新
4. ニュース収集ジョブで raw_news を更新 → score_news により ai_scores を更新
5. research モジュールでファクターを算出・正規化・評価
6. strategy 層（本リポジトリ外）でシグナル生成 → audit テーブルへ記録 → execution 層へ橋渡し

開発・貢献
- 仕様変更や追加機能は各モジュールの設計コメント（ファイル冒頭の docstring）に沿って行ってください。
- テストは各機能ごとにモック（OpenAI / J-Quants / ネットワーク）を用いて外部依存を切り分けて行うことを推奨します（本コードはその意図で設計されています）。

サポート / 連絡
- 本 README に記載のない細かい実装仕様は、各モジュール冒頭の docstring を参照してください。問題や質問があれば Issue を作成してください。

以上。README のサンプルとして簡潔にまとめました。必要ならインストール用の requirements.txt や .env.example を追加で生成しますか？