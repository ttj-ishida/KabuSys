KabuSys — 日本株自動売買プラットフォーム（README）
概要
- KabuSys は日本株向けのデータパイプライン・リサーチ・AI（ニュースNLP）・監査ログ・監視機能を含む基盤ライブラリです。
- 主に DuckDB をデータレイヤに用い、J-Quants API からのデータ取得、RSS ニュース収集、OpenAI を使ったニュースセンチメント評価、ファクター計算・探索、監査ログ（注文・約定トレース）の初期化などを提供します。
- 実際のブローカー発注やリアルタイム実行エンジンはこのコードベースの一部機能として想定されていますが、ここに含まれるモジュールは主にデータ処理・リサーチ・分析・監査周りのユーティリティ群です。

主な機能一覧
- 環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み（プロジェクトルート検出）、必須設定取得ユーティリティ
- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API から株価・財務・市場カレンダーを差分取得し DuckDB に保存
  - レートリミット・リトライ・トークン自動リフレッシュ対応
  - ETL の統合エントリ run_daily_etl を提供
- ニュース収集 / 前処理（kabusys.data.news_collector）
  - RSS フィードの取得、URL 正規化、SSRF 対策、記事保存準備
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント評価と ai_scores への書き込み
  - バッチ送信、リトライ、レスポンス検証、スコアクリップ
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離＋マクロニュースセンチメントの加重合成で日次レジーム判定を実行
- リサーチ・ファクター計算（kabusys.research）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
  - z-score 正規化ユーティリティ（kabusys.data.stats）
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出
  - QualityIssue オブジェクトで詳細を返す
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルのスキーマ定義と初期化ユーティリティ
  - init_audit_schema / init_audit_db を提供して監査DBを作成
- カレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーの取得・保存、営業日判定・前後営業日取得など
- 設定や監視に関する各種ユーティリティ（PID / キルフラグパス、閾値などを環境変数で制御）

前提・必須要件
- Python 3.10 以上（型アノテーションに | を使用）
- 外部ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI 等）
- J-Quants リフレッシュトークン、OpenAI API キーなどの環境変数（下記参照）

主な環境変数（キー）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone <repository-url>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を作成
   - 最低限 JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY（news 機能を使う場合）を設定
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
   - 自動ロードを避けたいテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます
5. DuckDB 初期化（監査用DB 等）
   - Python から init_audit_db を呼び出す（例は下記）

基本的な使い方（コード例）
- DuckDB 接続の取得と ETL 実行（日次 ETL）
  - from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- ニューススコアリング（指定日）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込み件数: {written}")

- 市場レジーム判定
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI キーは環境変数または引数で指定

- ファクター計算・リサーチ
  - from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    conn = duckdb.connect(str(settings.duckdb_path))
    mom = calc_momentum(conn, date(2026, 3, 20))
    vol = calc_volatility(conn, date(2026, 3, 20))
    val = calc_value(conn, date(2026, 3, 20))

- 監査DB 初期化（専用 DB を作る）
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")

運用・テストのヒント
- OpenAI / ネットワーク呼び出しは外部依存なのでユニットテストではモックしてください。
  - news_nlp._call_openai_api や regime_detector._call_openai_api を patch する設計になっています。
- 自動で .env を読み込む動作は config モジュールがプロジェクトルート（.git または pyproject.toml）を探索して行います。テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- ETL / API 部分はリトライ・バックオフ・レート制御の実装があるため、API 側のレート上限を考慮した運用が可能です。
- DuckDB の executemany に空リスト渡すと問題になるバージョンがあるため、モジュール側で空リストチェックをしています。運用で空の書き込みが発生した場合は問題になりにくい実装になっています。

ディレクトリ構成（主要ファイルと役割）
- src/kabusys/
  - __init__.py: パッケージ定義（バージョン）
  - config.py: 環境変数管理、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py: ニュースセンチメントの収集・OpenAI 呼び出し・ai_scores 書き込みロジック
    - regime_detector.py: マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py: ETL パイプライン（run_daily_etl, run_prices_etl 等）と ETLResult
    - etl.py: ETLResult の再エクスポート
    - news_collector.py: RSS 取得・前処理・記事ID生成・SSRF 対策
    - calendar_management.py: マーケットカレンダー管理・営業日判定・calendar_update_job
    - quality.py: データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py: zscore_normalize 等の統計ユーティリティ
    - audit.py: 監査ログスキーマ定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py: Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py: 将来リターン計算、IC / ランク等の解析ユーティリティ

注意事項・制約
- OpenAI 呼び出しや J-Quants API 呼び出しは実際のクレデンシャルとネットワーク環境が必要です。ローカル開発では関連機能をモックしてテストしてください。
- 設計方針として「ルックアヘッドバイアス防止」が徹底されており、各モジュールは内部で date.today() を直接参照しないように作られています（外部から target_date を明示的に渡す設計）。
- DuckDB のスキーマ（テーブル定義）は別途初期化処理（プロジェクト側のスキーマ初期化関数）を用意することを想定しています。audit.init_audit_db のように、必要テーブルを初期化するユーティリティを利用してください。

貢献・拡張
- 新しいデータソース（RSS、API）追加やシグナル→発注フローの実装、モニタリングエージェントの追加などを歓迎します。
- API クライアントや OpenAI 呼び出しまわりはリトライやエラーハンドリングを考慮した実装ですが、運用で見つかったケースに応じてログ・メトリクスを改善してください。

問い合わせ
- このコードベースに関する質問や改善提案はリポジトリの issue または PR を通してお願いします。

以上。必要であれば README に含める例やコマンドの追記（例えば systemd ユニット、cron 連携、より具体的な .env.example）を作成します。どの部分を詳しくしたいか教えてください。