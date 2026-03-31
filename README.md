KabuSys — 日本株自動売買プラットフォーム（README）
概要
本リポジトリは日本株のデータ基盤・研究・AIによるニュース解析・監査（トレーサビリティ）を提供する内部ライブラリ群です。
主に以下用途を想定しています。
- J-Quants からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB を用いたデータ永続化・ETL パイプライン
- ニュース記事の収集と LLM による銘柄別センチメント付与（gpt-4o-mini を想定）
- ETF とマクロニュースを統合した市場レジーム判定
- 研究用ファクター計算・特徴量解析（バックテスト前処理）
- 発注フローに対する監査ログスキーマ（監査テーブルの初期化）

機能一覧
- 環境設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須変数取得ユーティリティ（Settings クラス）
- データ ETL（kabusys.data.pipeline）
  - daily_etl の実行（市場カレンダー、株価、財務の差分取得／保存）
  - J-Quants API クライアント（fetch / save の実装、レートリミット/再試行/401 リフレッシュ対応）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集・NLP（kabusys.data.news_collector / kabusys.ai.news_nlp）
  - RSS フィード取得（SSRF 対策、サイズ制限、トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア化（ai_scores へ書き込み）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成し日次でレジーム（bull/neutral/bear）を算出・保存
- 研究モジュール（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution のトレーサビリティ用テーブル定義と初期化ユーティリティ
- その他ユーティリティ
  - 統計ユーティリティ（Zスコア正規化）
  - カレンダー操作（営業日判定、next/prev_trading_day 等）

セットアップ手順（ローカル開発向け）
1. レポジトリをクローンし、仮想環境を作成
   - python >= 3.10 を推奨
   - 例:
       python -m venv .venv
       source .venv/bin/activate

2. 依存パッケージをインストール
   - 必要な主要パッケージ（例）
       pip install duckdb openai defusedxml
   - （任意）requirements.txt があればそれを使用:
       pip install -r requirements.txt

3. 環境変数の準備
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）:
       JQUANTS_REFRESH_TOKEN=xxxxx
       OPENAI_API_KEY=sk-...
       KABU_API_PASSWORD=...
       SLACK_BOT_TOKEN=...
       SLACK_CHANNEL_ID=...
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       KABUSYS_ENV=development
       LOG_LEVEL=INFO
   - Settings クラスで必須チェック（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）を行います。

4. データディレクトリの作成（必要に応じて）
   - デフォルトの DuckDB ファイルは data/kabusys.duckdb です。親ディレクトリを作成するか、init 関数が自動作成します。

使い方（コード例）
- DuckDB 接続を用意する
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())  # ETL の概要を確認

- ニュースのセンチメントスコアを生成（OpenAI API キーは環境変数 OPENAI_API_KEY か引数で渡す）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} symbols")

- 市場レジーム判定を実行
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env または api_key 引数

- 監査ログ用 DB を初期化
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")  # :memory: を指定するとメモリ DB

- Settings を使って設定を参照
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.is_live)      # bool

注意点 / 運用上のポイント
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）から行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 に設定して自動読込を抑制してください。
- OpenAI の呼び出しはリトライやタイムアウトを考慮した実装がありますが、API キーやクォータに注意してください。score_news と regime_detector は API 呼び出し失敗時にフォールバック（多くは 0.0）するよう設計されています。
- J-Quants API はレート制限（120 req/min）に合わせた RateLimiter が組み込まれており、401 受信時の自動トークンリフレッシュもサポートします。
- DuckDB に対する executemany の空パラメータは一部バージョンでエラーになるため、空チェックを行ってから実行します。
- 全ての日時保存は UTC を想定している部分があります（監査ログは SET TimeZone='UTC' を実行）。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースの LLM によるセンチメント解析・ai_scores 書き込み
    - regime_detector.py             — ETF MA200 とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py         — 市場カレンダー管理・営業日ユーティリティ
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult の再エクスポート
    - jquants_client.py              — J-Quants API クライアント（fetch/save 実装）
    - news_collector.py              — RSS 取得・前処理・raw_news 保存
    - quality.py                     — データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログスキーマ定義と初期化
  - research/
    - __init__.py
    - factor_research.py             — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py         — 将来リターン計算、IC、統計サマリー
  - ai/、research/、data/ 以下の実装はドメイン知識に基づいた処理フローを含みます（詳細は該当ファイルの docstring を参照してください）

ライセンスと貢献
- （このテンプレートにはライセンスファイルが含まれていません。運用時は適切な LICENSE を追加してください）
- バグ報告や改善提案は Issue を作成してください。コード変更は PR を送ってください。

補足（よくある質問）
- Q: OpenAI / J-Quants の API キーはどの環境変数を使えば良いですか？
  - OpenAI: OPENAI_API_KEY（score_news / regime_detector は引数での注入も可能）
  - J-Quants: JQUANTS_REFRESH_TOKEN（config.settings.jquants_refresh_token で取得）
- Q: 自動で .env を読み込ませたくない場合は？
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを停止します。

以上。各モジュールの詳細な利用方法や運用ルールは該当ソース（docstring）を参照してください。必要であれば README にサンプル .env.example、requirements.txt、起動スクリプト例を追記します。どの追加情報が必要か教えてください。