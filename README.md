プロジェクト README（日本語）
以下は与えられたコードベースに基づく README です。プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
- 名称: KabuSys
- 概要: 日本株のデータパイプライン・リサーチ・AI 知見・監査ログ・ETL を備えた自動売買支援ライブラリ。J-Quants API からのデータ取得、DuckDB を用いた永続化、OpenAI を利用したニュースセンチメント判定、ETF を用いた市場レジーム判定、ファクター計算や品質チェック、監査用テーブル初期化等の機能を提供します。

主な特徴（機能一覧）
- データ取得 / ETL
  - J-Quants から株価（日次 OHLCV）、財務データ、JPX マーケットカレンダー等を差分取得して DuckDB に保存（ページネーション・レート制御・リトライ・ID token 自動リフレッシュ）。
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）。
- データ品質チェック
  - 欠損（OHLC）、スパイク（前日比閾値）、重複、日付整合性（未来日付／非営業日）を検出。QualityIssue を返却。
- ニュース収集・NLP
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去、前処理）と raw_news 保存。
  - OpenAI（gpt-4o-mini）を用いたニュース（銘柄ごと）センチメントスコアリング（score_news）。
- 市場レジーム判定（AI 統合）
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して日次で regime（bull/neutral/bear）を算出・保存（score_regime）。
- 研究（Research）
  - Momentum/Volatility/Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）。
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化ユーティリティ。
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブルを DuckDB に冪等で作成するヘルパ（init_audit_schema / init_audit_db）。注文と約定のトレーサビリティ設計。
- 設定管理
  - 環境変数 / .env 自動読み込み（プロジェクトルートの .env/.env.local、OS 環境変数優先、.env.local は上書き）。テストで自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD。

動作環境（目安）
- Python 3.10+
- 主要依存（概略）:
  - duckdb
  - openai（OpenAI Python SDK）
  - defusedxml
  - その他: 標準ライブラリ（urllib 等）
（実際の requirements はプロジェクトの packaging / requirements ファイルを参照してください）

環境変数（主要）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（get_id_token 用）
  - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（Slack 連携を使う場合）
  - SLACK_CHANNEL_ID: Slack チャンネル ID
  - KABU_API_PASSWORD: kabuステーション API パスワード（発注関連）
- 任意 / デフォルトあり
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY: OpenAI 呼び出しで使用（score_news / score_regime 等）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - PID_FILE_PATH: 実行監視用 PID ファイルパス（デフォルト: data/execution.pid）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
  - KABUSYS_ENV: environment（development / paper_trading / live、デフォルト development）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- 自動 .env 読み込みについて:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env と .env.local を自動ロードします。
  - OS 環境変数は保護され、.env.local は .env より優先して上書きします。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

セットアップ手順（概略）
1. Python 環境を用意（3.10+ 推奨）。
2. 依存パッケージをインストール
   - 例:
     - pip install duckdb openai defusedxml
     - （プロジェクトに requirements.txt / pyproject があればそれに従ってください）
3. プロジェクトルートに .env を用意（推奨: .env.example を参照して JQUANTS_REFRESH_TOKEN 等を設定）
   - 例 .env に最低限:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - KABU_API_PASSWORD=...
4. DuckDB ファイル保存先のディレクトリを作成（必要に応じて）
   - e.g. mkdir -p data
5. （任意）監査 DB を初期化
   - Python で:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
6. テストや CI で自動 env ロードを抑えたい場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

基本的な使い方（コード例）
- DuckDB に接続して日次 ETL を実行（最低限の流れ）
  - 例:
    - import duckdb, datetime
    - from kabusys.config import settings
    - from kabusys.data.pipeline import run_daily_etl
    - conn = duckdb.connect(str(settings.duckdb_path))
    - result = run_daily_etl(conn, target_date=datetime.date(2026,3,20))
    - print(result.to_dict())

- ニューススコアリング（OpenAI API key 必須）
  - from kabusys.ai.news_nlp import score_news
  - import duckdb, datetime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - n = score_news(conn, datetime.date(2026,3,20))  # RETURN: 書き込み銘柄数

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - r = score_regime(conn, datetime.date(2026,3,20))  # RETURN: 1 成功

- 研究用関数（例: モメンタム）
  - from kabusys.research.factor_research import calc_momentum
  - records = calc_momentum(conn, datetime.date(2026,3,20))

- 監査テーブル初期化（ファイルに対して）
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")

注意点 / 実運用上の注意
- OpenAI 呼び出しは外部 API に依存するため APIキー管理・コスト制御に注意。score_news / score_regime は API 呼び出し失敗時にフェイルセーフ（スコア=0 等）で継続しますが、キー未設定だと ValueError を投げます。
- J-Quants API のレート制御とリトライを実装していますが、長時間の大量取得時は十分に注意してください。
- DuckDB executemany に関する注意（空リストバインド回避）やトランザクションの取り扱い（init_audit_schema の transactional オプション等）がコード上にあります。運用スクリプト側でも例外処理を適切に行ってください。
- .env パースはシェル形式をある程度サポートします（export, クォート、コメント処理など）。ただし極端に特殊な記法は想定外になる可能性があります。

主要なディレクトリ / ファイル構成（概要）
- src/kabusys/
  - __init__.py
  - config.py                : 環境変数 / .env 自動ロード + Settings
  - ai/
    - __init__.py
    - news_nlp.py            : ニュースの LLM スコアリング（score_news）
    - regime_detector.py     : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      : J-Quants API クライアント（fetch, save 関数）
    - pipeline.py            : ETL（run_daily_etl, run_prices_etl 等）と ETLResult
    - etl.py                 : ETLResult の再エクスポート
    - news_collector.py      : RSS 収集・前処理
    - calendar_management.py : マーケットカレンダーの判定・更新
    - stats.py               : zscore_normalize 等の統計ユーティリティ
    - quality.py             : データ品質チェック（各種 check_*）
    - audit.py               : 監査スキーマ定義・初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py     : calc_momentum/calc_value/calc_volatility
    - feature_exploration.py : calc_forward_returns, calc_ic, factor_summary, rank
  - ai/*（LLM 関連）と research/*（ファクター/統計）で、バックテスト用のデータ参照は DuckDB の prices_daily / raw_financials 等に限定されています（実運用口座にはアクセスしない）。

ライセンス・貢献
- 本 README ではライセンス情報や貢献方法はソースに明示されていません。実運用・配布前にプロジェクトの LICENSE や CONTRIBUTING ドキュメントを追加してください。

補足（トラブルシューティング）
- .env 自動読み込みが期待通りに動かない／テスト環境で env の影響を避けたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして自動ロードを抑止したうえで、テスト内で必要な env を明示的に設定してください。
- OpenAI からの JSON Mode レスポンスやネットワークエラーへのフォールバックは各モジュールで考慮済みですが、応答のフォーマットが変わるとパースエラーとなる可能性があります。問題発生時は WARN/ERROR ログを確認してください。

以上がコードベースに基づく README の内容です。追加したい利用例・CI 手順・具体的な requirements.txt や pyproject.toml の情報があれば、それに合わせてドキュメントを拡張します。