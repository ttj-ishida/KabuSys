# KabuSys

小型の日本株自動売買システム向けユーティリティ群と監視・検証ツール群を含むリポジトリです。ポートフォリオ構築、発注エンジンの起動補助、監視（System / Trade / Risk）、Paper Trading 用検証レポート生成、AI を使ったニュースセンチメント処理などの機能を提供します。

---

目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- セットアップ手順
- 使い方（起動・停止・ユーティリティ）
- 主要環境変数
- ディレクトリ構成（主要ファイル説明）

---

プロジェクト概要
- KabuSys は日本株自動売買システムの補助ライブラリ群と運用用ツール（監視、検証、AI スコアリング）を提供します。
- コア機能は純粋関数群（ポートフォリオ構築／リスク調整／ポジションサイジング）、発注・再同期ロジック（Reconciler / OrderManager）、監視サブシステム（System / Trade / Risk モニタ）、および Streamlit ベースの監視ダッシュボードなどです。
- Paper Trading 実行時は本番 DB と分離された専用 SQLite を使用（KABUSYS_ENV=paper_trading）。

機能一覧
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額／スコア加重配分
  - リスク調整（セクター上限、レジーム乗数）
  - 発注株数計算（リスクベース、等配分等）、単元株丸め、aggregate cap
- 発注関連
  - OrderManager、OrderRepository、ExecutionEngine（run_execution 起動スクリプト）
  - Reconciler（起動時の発注状態・ポジション照合）
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor とそれを束ねる MonitoringEngine
  - SQLite に監視ログを永続化（monitoring_db）
  - AlertManager（LINE push 通知）
  - KillSwitch（条件により ExecutionEngine 停止フラグを作成）
  - Streamlit ダッシュボード（監視 DB を可視化）
- AI / リサーチ
  - ニュース NLP（OpenAI を使った銘柄別センチメント → ai_scores）
  - 市場レジーム判定（ETF MA200 とマクロセンチメントの合成）
  - ファクター計算（momentum / volatility / value）・特徴量探索ユーティリティ
- ツール
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）
  - プロセス優先度 / CPU affinity ユーティリティ（psutil を抽象化）

前提・依存関係
- Python >= 3.10（| 型注釈など）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- （プロジェクトに requirements.txt がない場合）仮想環境作成後に手動でインストールしてください。

セットアップ手順（簡易）
1. リポジトリのクローン / 作業ディレクトリへ移動
2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. データディレクトリを作成
   - mkdir -p data
   - （実行時に自動作成される箇所もありますが、手動で作ると良い）
5. 環境変数設定
   - .env または .env.local をプロジェクトルートに置くと自動読み込み（既定）。読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主要な環境変数については下の「主要環境変数」を参照。

起動・使い方

共通
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）に .env / .env.local を置くと自動読み込みされます。
  - .env.local は .env より優先して上書き（ただし OS 環境変数は保護される）。
  - テストなどで自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

ExecutionEngine（発注エンジン）
- 起動:
  - python -m kabusys.run_execution
  - 起動時に Settings に基づきブローカークライアントを生成。KABUSYS_ENV=paper_trading の場合は MockBroker を使用して data/paper_trading.db を使う（本番 DB と完全分離）。
- 停止:
  - ExecutionEngine は start 時に data/execution.pid を書き、停止は kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）の作成で実行できます（KillSwitch が書く）。管理者が手動で kill.flag を作成するとエンジン停止シグナルになります。
  - stop_requested.flag は run_execution ループでも監視され、存在するとエンジン停止処理を行います（スクリプト内で使用される停止フラグ）。
- PID / フラグ:
  - デフォルト PID ファイル: data/execution.pid（Settings.pid_file_path）
  - 停止フラグ: data/stop_requested.flag（run scripts が参照）
  - Kill flag: data/kill.flag（KillSwitch 用）

Monitoring（監視）
- システム監視ループ（軽量版: SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト60秒）。
  - run_monitoring は SystemMonitor を定期実行して monitoring DB に system_status を記録します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使う（監視は本番データを前提）。
- 豊富な監視機能は MonitoringEngine（monitoring_engine.py）を利用して System/Trade/Risk のポーリング、KillSwitch 評価、AlertManager 通知を行えます（テスト用に run_once() などを呼べます）。
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB は監視 DB（読み取り専用 URI を作る例あり）。起動前に monitoring データがないと警告が出ます。

Paper Trading 検証レポート
- コマンドライン実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH で指定することもできます（デフォルト: data/paper_trading.db）。

AI（ニュース NLP / レジーム判定）
- OpenAI API を用いてニュースセンチメントやマクロセンチメントを計算します。API キーは OPENAI_API_KEY 環境変数か関数引数で渡します。
- 主要な公開関数:
  - kabusys.ai.score_news(conn, target_date, api_key=None) — raw_news から銘柄別スコアを ai_scores テーブルへ書き込み
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime テーブルへ書き込み
- 失敗時はフェイルセーフ（多くの場合 0.0 やスキップ）でシステムの継続を優先します。

停止・強制停止の挙動
- run_monitoring / run_execution はプロジェクトルートの data/stop_requested.flag を監視します。ファイルが存在するとループを終了します（外部から停止指示を与える用途）。
- KillSwitch はリスク閾値（ドローダウンやポジション上限）を満たしたときに Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込み、ExecutionEngine の停止トリガーとなります。
- KillSwitch.clear() で kill.flag を削除できます（起動時にクリアするオプションあり）。

主要環境変数（抜粋）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト development。
  - paper_trading 時は発注用 DB が分離され、MockBroker を使用。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須とされるプロパティあり）。
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）。
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）。
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager による LINE 通知に使用（未設定時は送信をスキップ）。
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）。
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）。
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）。
- PID_FILE_PATH: デフォルト data/execution.pid（ExecutionEngine が使用）。
- KILL_FLAG_PATH: デフォルト data/kill.flag。
- MONITOR_POLL_INTERVAL: run_monitoring が参照するポーリング間隔（秒）。デフォルト 60。
- PAPER_FILL_MODE: Paper Trading の約定モード（instant / partial / never / reject）。デフォルト "instant"。

ディレクトリ構成（主要）
- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数/.env ローディングと Settings クラス（各種設定プロパティ）
  - run_execution.py — ExecutionEngine 起動スクリプト（本番 / paper_trading を考慮）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - risk_adjustment.py — セクター制約・レジーム乗数
    - position_sizing.py — 発注株数計算、単元丸め、aggregate cap
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視 DB 初期化・アクセスレイヤ
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - alert_manager.py — LINE Push 通知ユーティリティ
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 Monitor を束ねるエンジン（テスト用 run_once / 本番用 run）
    - streamlit_dashboard.py — Streamlit ダッシュボード起動スクリプト
  - execution/
    - order_manager.py, reconciler.py, order_repository.py, execution_engine.py, broker_factory.py, ...（発注・再同期の実装）
  - ai/
    - news_nlp.py — raw_news を OpenAI でセンチメント化して ai_scores に書き込むロジック
    - regime_detector.py — マクロセンチメント + ETF MA200 を合成した市場レジーム判定
  - research/
    - factor_research.py — momentum / volatility / value などのファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー等
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意
- 監視は本番 DB を参照することが想定されているため、Paper Trading 時でも監視 DB は分離しない（設計上の意図）。Paper Trading の DB は発注ログ等を分離する目的。
- OpenAI を利用する機能は API コストやレート制限に注意。リトライ・バックオフ実装あり。
- SQLite / DuckDB によるデータアクセスは同時書き込み・ロックの挙動に注意（複数プロセスが同時書き込みする場合の運用設計を推奨）。
- .env のロードはプロジェクトルートを .git / pyproject.toml で判定するため、パッケージ配布後も想定どおり動作するよう設計されています。

貢献・拡張
- ポートフォリオ設計（PortfolioConstruction.md 等の参照）に基づく調整や、ブローカープラグインの追加、より詳細な監視ルール追加などが想定されています。
- テストについて: 各モジュールは副作用を最小化するよう設計されています。AI API 呼び出し箇所はモック可能な形で実装されています（ユニットテスト時は _call_openai_api 等を patch してください）。

---

以上がこのコードベースの README 相当の概要です。必要であればサンプル .env.example、運用手順（systemd サービス定義例 / Supervisor / Dockerfile）や詳細な API ドキュメントを追加で作成できます。どの情報を優先して追加しますか？