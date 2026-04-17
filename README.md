# KabuSys — 自動売買システム（README）

このドキュメントは、提供されたコードベース（src/kabusys 以下）を使い始めるための概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

重要: 本リポジトリは日本株向けの自動売買・監視・研究コンポーネント群を含みます。実際の資金を扱う際は十分に検証し、適切な権限や安全対策を行ってください。

概要
- KabuSys は日本株自動売買のためのモジュール群（Execution / Monitoring / Portfolio / Research / AI / Tools / Utils 等）を提供します。
- ExecutionEngine（発注実行）と Monitoring（監視）は分離され、monitoring は本番用監視DBを参照します。
- Paper Trading（模擬売買）モードを備え、本番DBと分離された専用 SQLite ファイルに記録できます。
- DuckDB は時系列価格・ファクター計算・ニュース集計などの分析向けに利用します。
- OpenAI（gpt-4o-mini）を用いたニュースの NLP スコアリングや市場レジーム判定の仕組みを持ちます（APIキー必須）。

主な機能一覧
- 発注・注文状態管理（execution モジュール）
  - OrderManager / ExecutionEngine / Reconciler（再起動時の突合せ）
  - Broker クライアントの抽象化（実運用・モック切替）
- 監視（monitoring モジュール）
  - SystemMonitor：CPU/メモリ/Disk/プロセス状態・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション数監視、ダッシュボード更新
  - KillSwitch：一定条件で ExecutionEngine 停止フラグを作成
  - AlertManager：LINE push による通知（トークン未設定時はログのみ）
  - Streamlit ベースのダッシュボード（読み取り専用）
- ポートフォリオ構築（portfolio）
  - 候補選定、等重/スコア重み、リスク調整、株数算出（単元丸め等）
- 研究用（research）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（情報係数）計算、ファクター統計
- AI（ai）
  - news_nlp.score_news：ニュース記事をまとめて LLM で銘柄別センチメントを算出し ai_scores に書き込み
  - regime_detector.score_regime：ETF (1321) の MA200 とマクロニュースから日次の市場レジーム判定を行い保存
- ツール（tools）
  - paper_verification_report：Paper Trading DB を集計して検証レポートを出力
- ユーティリティ
  - Settings（環境変数管理、.env 自動読み込み）
  - process_priority：プロセス優先度 / CPU affinity の設定
  - MonitoringDB：監視用 SQLite の初期化と読み書きユーティリティ

セットアップ手順（開発 / 実行環境の準備）
1. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージ（主な依存）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit（ダッシュボード使用時）
   - これらを requirements.txt で管理している場合: pip install -r requirements.txt
   - ない場合は個別に: pip install duckdb psutil requests openai streamlit

3. プロジェクトルートと .env
   - Settings モジュールはプロジェクトルートを .git または pyproject.toml から自動検出します。
   - ルートに .env / .env.local を置くと自動で読み込まれます（環境変数が未設定のキーのみ .env が適用され、.env.local は上書き）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 重要な環境変数（.env で設定すべき例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合は必須）
     - KABUSYS_ENV：development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE：instant | partial | never | reject（paper_trading 用）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
     - LOG_LEVEL（例: INFO）

4. データディレクトリ
   - デフォルトで data/ 以下に .db / PID / フラグファイルを置きます。実行前に data/ を作成しておくと安全です。
   - 例: mkdir -p data

使い方（起動・運用ガイド）
- 実行エンジン（ExecutionEngine）起動
  - 本番/開発共通の起動スクリプト:
    - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、記録先は data/paper_trading.db（本番DBと完全分離）。
    - 実行スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil が必要）。権限不足の場合は警告が出ます。
    - 停止フラグ: data/stop_requested.flag を作成するとエンジンは安全に停止します（run_execution・run_monitoring の両方で監視）。
    - ExecutionEngine 停止要求（KillSwitch）は data/kill.flag に書き込まれます。Execution 起動時に KILL_FLAG_CLEAR_ON_START が 1 に設定されていると起動時に kill.flag を消去します（Settings.kill_flag_clear_on_start）。

- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は monitoring DB（Settings.sqlite_path）を使用。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使います（これは設計上の挙動です）。

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視DBを読み取り専用で開きます（URI の mode=ro を使用）。監視プロセスが起動していることが推奨。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で SQLite ファイルを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI 機能（プログラム的利用）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
    - api_key を None にすると環境変数 OPENAI_API_KEY を参照します。未設定だと ValueError。
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

プロセス制御とフラグ
- stop_requested.flag（data/stop_requested.flag）
  - run_execution / run_monitoring はこのファイルの存在をチェックし、存在する場合はループを終了します。手動で停止する際に利用できます。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch がトリガー条件を満たすとこのファイルを出力し、ExecutionEngine に停止シグナルを与えます（Execution 側は設計により kill.flag を参照して挙動を取ります）。
  - KillSwitch は冪等にファイル作成を行い、既存の場合は再作成しません。
- PID ファイル（data/execution.pid）
  - Execution 起動時に PID を書き、SystemMonitor がそのプロセス存否を確認します。stale PID（ファイルはあるがプロセスが存在しない）を検出すると削除しアラートログを残します。

設定・環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live（動作モード）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- OPENAI_API_KEY: OpenAI API キー（AI 機能）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 認証トークン（必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（設定がないと通知はスキップされログのみ）

トラブルシューティング（よくある注意点）
- Settings が必須環境変数を見つけられない場合は ValueError を送出します（起動失敗）。.env の設定を確認してください。
- OpenAI を使う機能は API キーが必須です。未設定だと score_* 関数が例外を投げます。
- psutil を用いたプロセス優先度設定・CPU affinity は権限や OS により失敗することがあります（警告ログ）。
- Streamlit で監視DBを読み込む際、他プロセスが書き込み中でも読み取り専用 URI で開けるように権限設定を確認してください。
- DuckDB/SQLite の executemany に空リストを投げるとエラーになるコード箇所があるため、既にコードでは空チェックを行っています。DB 操作でエラーが出る場合は入力パラメータを確認してください。

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義と __version__
  - config.py — Settings クラス、.env 自動ロード、必須変数チェック
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ
  - execution/
    - execution_engine.py (存在想定) — 発注実行エンジン（起動/停止制御）
    - order_manager.py — OrderManager（発注フロー管理）
    - order_repository.py — DB レイヤ（SQLite）
    - reconciler.py — 再起動時の照合ロジック
    - broker_factory.py, broker_api.py — ブローカー抽象/実装（Mock 含む）
    - order_record.py — OrderRecord, OrderState 等
  - monitoring/
    - monitoring_db.py — 監視DB 初期化 & 永続層（MonitoringDB クラス）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン/ポジション数監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各 Monitor の統合とループ
    - streamlit_dashboard.py — Streamlit ダッシュボード（起動コマンド記載）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・スケーリング・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュース集約→OpenAIで銘柄別スコア算出・ai_scores 書き込み
    - regime_detector.py — MA200 + マクロニュースで日次レジーム判定
  - data/ （実行時に作られる想定）
    - monitoring.db （デフォルトの監視 SQLite）
    - paper_trading.db （paper_trading モード用 SQLite）
    - kabusys.duckdb（DuckDB ファイル）
    - execution.pid, stop_requested.flag, kill.flag などの運用ファイル
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

追加メモ
- 本コードベースは設計文書（PortfolioConstruction.md, StrategyModel.md 等）に準拠した設計思想が注記されています（コメントや docstring に記載）。
- DB スキーマは monitoring_db.init_monitoring_db() で初期化・マイグレーション（若干の ALTER）まで行うように実装されています。
- AI 呼び出し（OpenAI）は JSON mode を使い、レスポンスの堅牢なバリデーションと再試行ロジックを備えています（429 / タイムアウト / 5xx に対する指数バックオフ等）。
- 本 README はコードベースから抽出した情報に基づくサマリです。詳細な API や実装の振る舞いは各モジュールの docstring / コメントを参照してください。

問題や追加で知りたい項目（例: ブローカー実装の詳細、ExecutionEngine の API、unit test の実行方法など）があれば教えてください。必要に応じて README を拡張します。