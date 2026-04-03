KabuSys
=======

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
本リポジトリはデータ収集（J-Quants）、ETL、データ品質チェック、ニュースのNLP評価（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを含むコンポーネント群を提供します。

主な目的
- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する
- ニュースを収集・前処理し、OpenAI を用いて銘柄ごとのニュースセンチメントを算出する
- ETF を用いた市場レジーム判定（MA と マクロニュースの合成）
- ファクター計算・特徴量探索（研究用）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 発注・約定までを追跡可能にする監査ログスキーマの初期化

機能一覧
- 環境設定管理（.env 自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
- ニュース収集（RSS 取得、SSRF 防御、前処理、raw_news への保存は実装方針あり）
- OpenAI を使ったニュース NLP（score_news）と市場レジーム判定（score_regime）
- リサーチ用ファクター計算（momentum, volatility, value 等）と統計ユーティリティ（zscore_normalize, IC, rank 等）
- 監査ログテーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）

セットアップ手順（開発環境）
1. Python インタプリタを用意
   - Python 3.10+ を想定（typing | None の表記等に合わせる）
2. リポジトリをクローンしてパッケージをインストール
   - 推奨: 仮想環境（venv / pyenv など）を作成して有効化
   - プロジェクトルートに移動して:
     - pip install -e . あるいは requirements を用意している場合は pip install -r requirements.txt
3. 必要な Python パッケージ（主要な外部依存）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリを広く使用しているため追加は最小限）
   - 実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください
4. 環境変数の設定
   - .env または環境変数で各種設定値を指定できます。プロジェクトルートの .env/.env.local が自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 重要な変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabu ステーション API パスワード（必須／発注連携時）
     - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime を使う時）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 通知用（オプション）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用途の SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV           : environment ('development' / 'paper_trading' / 'live')（デフォルト development）
     - LOG_LEVEL             : ログレベル（DEBUG/INFO/...）
     - PID_FILE_PATH, KILL_FLAG_PATH, *_THRESHOLD_PCT などの監視設定
   - .env.example を用意している想定なのでそれをコピーして編集してください。

基本的な使い方（サンプル）
- 設定読み込みと DuckDB 接続
  - 設定は kabusys.config.settings からアクセスできます。
  - 例:
    from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - run_daily_etl は市場カレンダー・株価・財務を差分取得し品質チェックを実行します。
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=None)  # target_date=None は今日扱い
    print(result.to_dict())

- ニューススコア（OpenAI を使用）
  - score_news は raw_news / news_symbols を参照して ai_scores に銘柄スコアを書き込みます。
    from kabusys.ai.news_nlp import score_news
    from datetime import date
    count = score_news(conn, target_date=date(2026, 3, 20))  # api_key を渡すことも可（api_key="..."）

  - OpenAI API キーを環境変数 OPENAI_API_KEY にセットするか、api_key 引数で指定します。

- 市場レジーム判定
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI キーは環境変数または api_key 引数

- 監査ログ DB の初期化（監査用 DuckDB を作る）
    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も指定可

- リサーチ関数の利用例（ファクター）
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    from datetime import date
    momentum = calc_momentum(conn, target_date=date(2026,3,20))
    volatility = calc_volatility(conn, target_date=date(2026,3,20))
    value = calc_value(conn, target_date=date(2026,3,20))

注意点・設計上のポイント
- Look-ahead bias（将来データ参照）を避ける設計思想が各所に反映されています:
  - API 呼び出し・スコアリング関数は target_date を明示することを前提とし、内部で datetime.today() を乱用しません。
  - prices_daily 等の SQL は date < target_date のようにルックアヘッドを防いでいます。
- ETL は差分更新・バックフィルを採り、API の後出し修正を吸収する仕組みがあります（backfill_days の設定）。
- ニュース収集は SSRF 対策、受信サイズ制限、トラッキングパラメータ削除などを行います。
- OpenAI 呼び出しは JSON Mode（厳密な JSON を期待）を前提にし、レスポンスパース失敗時はフォールバックします。
- J-Quants クライアントはレート制御（120 req/min）とリトライ・401トークンリフレッシュを実装しています。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメントスコアリング
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult 再エクスポート
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - quality.py                     — データ品質チェック
    - calendar_management.py         — 市場カレンダー管理・営業日判定
    - news_collector.py              — RSS ニュース取得（SSRF 対策等）
    - audit.py                       — 監査ログスキーマの定義・初期化
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Volatility / Value 計算
    - feature_exploration.py         — 将来リターン・IC・統計サマリー等
  - monitoring/, execution/, strategy/ (パッケージ公開想定; 省略ファイルがある場合あり)

環境変数自動ロード
- config.py はプロジェクトルート（.git または pyproject.toml がある場所）を探索し、.env と .env.local を自動的に読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。

ログ・モード
- KABUSYS_ENV = development | paper_trading | live によるモード分けがあります。
- LOG_LEVEL 環境変数でログレベルを調整します（INFO デフォルト）。

テスト・モックについて
- OpenAI 呼び出しや _urlopen 等はテストで差し替え可能な実装（関数やハンドラをモック）になっています。ユニットテストではこれらを patch して外部依存を切り離してテストしてください。

付記
- README 内の使用例は簡略化したサンプルです。実運用ではログの設定、例外ハンドリング、バックオフ戦略、スケジューラ（cron / airflow など）での定期実行、発注時の安全ガード等を整備してください。
- セキュリティ: API キー等は公開リポジトリに含めないでください。CI/デプロイ環境ではシークレット管理を推奨します。

必要に応じて、デプロイ手順・運用手引き・API モック用テストガイドなどの追加ドキュメントを作成できます。必要なドキュメント項目を教えてください。