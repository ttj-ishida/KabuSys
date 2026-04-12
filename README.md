# KabuSys

日本株自動売買システムの Python ライブラリ / 実行スクリプト群。

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・レポート・研究用ユーティリティを含むモジュール群で構成されています。設計上、ロジックは可能な限り純粋関数 / DB 層と分離されており、paper_trading（モックブローカー）と live（本番）の切替、監視、LLM を使ったニュースセンチメント評価などの機能を備えます。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 実行コンポーネント
  - 監視
  - Streamlit ダッシュボード
  - Paper Trading 検証レポート
  - AI（ニュース NLP / レジーム判定）
- 環境変数（主なもの）
- ディレクトリ構成

---

プロジェクト概要
- コア機能：銘柄選定、重み付け、ポジションサイズ計算、リスク調整、発注管理（OrderManager / Reconciler）、監視（System / Trade / Risk）、AI ベースのニューススコアリング・レジーム判定、研究用ファクター計算。
- DB：DuckDB（時系列 / ファクターデータなど）と SQLite（監視・トレードログ・orders DB 等）を併用。
- 設計方針：ルックアヘッドバイアス回避、クラッシュ耐性（永続化順序の配慮）、テストしやすい純関数群、外部 API 呼び出しは限定的に設計。

---

機能一覧
- portfolio
  - 候補選定（score / equal）
  - 重み計算（等配分・スコア重み）
  - セクター上限適用、レジーム乗数
  - 株数決定（risk_based / equal / score）、単元丸め、投下資金スケーリング
- research
  - momentum / volatility / value ファクター計算（DuckDB 経由）
  - 将来リターン計算、IC 計算、統計サマリー
- execution
  - OrderManager（状態遷移と broker 呼び出しラッパー）
  - Reconciler（起動時の同期）
  - BrokerFactory（paper_trading と live の切替想定）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringDB（SQLite による永続化）
  - MonitoringEngine（ポーリング統合）
  - KillSwitch（ファイルによる停止シグナル）
  - AlertManager（LINE への通知）
  - Streamlit ダッシュボード（監視可視化）
- ai
  - news_nlp: OpenAI を使った銘柄ごとのニュースセンチメント取得（ai_scores テーブルに書込）
  - regime_detector: ma200 とマクロニュースを合成した日次レジーム判定（market_regime テーブルに書込）
- tools
  - paper_verification_report: Paper Trading の検証レポート生成（SQLite の集計）

---

セットアップ手順（開発環境）
1. リポジトリをクローン
   ```
   git clone <repo_url>
   cd <repo_root>
   ```

2. Python 仮想環境作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール（例）
   - 最低限必要なパッケージ:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     ```
     pip install duckdb psutil openai requests streamlit
     ```
   - 実際の requirements はプロジェクト配布時に requirements.txt を用意してください。

4. 環境変数設定
   - プロジェクトルートの .env / .env.local を使って環境変数を設定できます。
   - 自動読み込みはデフォルトで有効（Settings モジュールがプロジェクトルートを探索して .env を読み込みます）。
   - テスト時などに自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DB 初期化
   - 実行スクリプトは起動時に monitoring DB のテーブルを冪等的に作成します（init_monitoring_db）。
   - DuckDB のスキーマ（prices_daily, raw_financials など）は別途データ投入が必要です（研究 / バックテスト用）。

---

使い方

1) 実行（ExecutionEngine）
- 本番/ペーパー切替:
  - 環境変数 KABUSYS_ENV により動作モードを切替します。許容値:
    - development（デフォルト）
    - paper_trading（モックブローカーを使用し data/paper_trading.db に記録）
    - live
- 実行方法:
  ```
  python -m kabusys.run_execution
  ```
  - 起動時に Settings を読み、DB 接続・ブローカークライアント生成・依存コンポーネント組み立て後、ExecutionEngine.run_session() を実行します。
  - Paper Trading 時は settings.is_paper が True になり、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用します。

2) 監視（Monitoring ポーリング）
- 起動:
  ```
  python -m kabusys.run_monitoring
  ```
- ポーリング間隔の調整:
  - 環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 0 以下や不正文字列が指定された場合はデフォルトにフォールバックします。
- 監視は本番 sqlite_path（Settings.sqlite_path / default data/monitoring.db）を使用します（KABUSYS_ENV に依らず本番 DB を参照する挙動です）。

3) Streamlit 監視ダッシュボード
- 起動:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
- データベースを read-only で開くため、監視プロセスと同時に参照できます。

4) Paper Trading 検証レポート
- スクリプト:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
- デフォルト DB: data/paper_trading.db。--db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。
- レポートでは稼働率・注文成功率・送信率・P95 レイテンシなどを出力し、PASS/FAIL 判定を行います。

5) AI（ニュース NLP / レジーム判定）
- 必要: OpenAI API キー（環境変数 OPENAI_API_KEY または関数引数で指定）
- news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news / news_symbols から記事を集約して OpenAI に投げ、ai_scores テーブルへ書き込みます。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 とマクロニュースの LLM スコアを合成して market_regime テーブルへ書き込みます。
- 実行は Python レベルで DuckDB 接続を渡して呼び出します（CLI ラッパーはありません）。

---

主な環境変数（抜粋）
- KABUSYS_ENV: development / paper_trading / live（動作モード）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のモック約定モード（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用必須トークン（Settings で _require により必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）で通知する場合に必要
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイル（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" で有効）

注意: Settings モジュールは .env / .env.local をプロジェクトルートから自動で読み込みます（OS 環境変数を上書きしない挙動などの制御あり）。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定してください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - data/                  — （想定）DuckDB/Prices/Raw データ処理モジュール（実装は別）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - execution/
    - order_manager.py
    - reconciler.py
    - ...（broker API / order_repository 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（上記は本リポジトリ内の主要モジュールの抜粋です。細かい実装は各ファイル内の docstring を参照してください。）

---

運用上の注意
- Paper Trading と Live の DB は分離してください（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI API を利用する機能は API 料金とレイテンシの影響を考慮してください。リトライ・バックオフの仕組みは実装済みですが、運用上の制御（頻度・バッチサイズ）を行ってください。
- 監視側は既定で本番 monitoring DB を使用します。テスト環境で監視を動かす場合は DB の取り扱いに注意してください。
- process priority / cpu affinity の設定はプラットフォーム依存のため、権限不足で失敗する可能性があります（警告ログのみ出力して継続します）。

---

貢献・開発
- 各モジュールは単体でテスト可能であることを意識して実装されています（純粋関数、DB 層の明瞭な境界）。
- 新しい外部依存を追加する場合は requirements.txt を更新してください。
- LLM 呼び出しは API の将来変更に備えて _call_openai_api を patch する形でテストできます（モック化が容易）。

---

ライセンス / バージョン
- パッケージバージョン: src/kabusys/__init__.py の __version__ = "0.1.0"
- ライセンス情報はプロジェクトルートに LICENSE を置いてください（本 README には含めていません）。

---

補足
- 詳細な設計意図（PortfolioConstruction.md, StrategyModel.md 等の参照）や DB スキーマ、外部 API の契約、運用手順は別ドキュメントとして管理することを推奨します。README は主に導入と実行方法のガイドです。

必要であれば、.env.example のサンプルや requirements.txt のテンプレート、よくあるトラブルシュート（例: OpenAI キー未設定、DuckDB ファイルが空など）を追加で作成します。どのドキュメントが必要か教えてください。