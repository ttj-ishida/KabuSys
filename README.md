# KabuSys

日本株向け自動売買システムの一部実装。ポートフォリオ構築、ポジションサイズ計算、監視、ペーパートレード用検証ツール、LLM を使ったニュース NLP / レジーム判定などのモジュール群を含みます。

以下はこのコードベースの簡易 README（日本語）です。開発・ローカル実行向けのセットアップ手順、使い方、主要コンポーネントの説明をまとめています。

注意: この README はリポジトリ内のソースコードから仕様を抜粋して作成しています。実運用前に必ず設定を確認し、テスト環境で動作検証してください。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド・スクリプト）
- 主要設定項目（環境変数）
- 停止／キルフラグについて
- ディレクトリ構成（主要ファイルの説明）
- 備考（依存関係・注意点）

---

プロジェクト概要
- KabuSys は日本株を対象に設計された自動売買フレームワークの一部です。
- ファクター計算、ポートフォリオ構築、ポジションサイズ決定、リスク調整、監視（System / Trade / Risk）、ペーパートレード検証、ニュースの NLP スコアリング（OpenAI）や市場レジーム判定などの機能を提供します。
- SQLite / DuckDB をデータ永続化に使用し、外部 API（kabuステーション、J-Quants、OpenAI）と連携する設計になっています。ペーパートレードは本番 DB と分離して管理できます。

機能一覧
- 環境設定読み書き・ウィザード: config_setup.py（.env の作成・更新支援）
- 設定検証 CLI: validate_config.py（.env と config/*.yaml のチェック）
- 監視プロセス:
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID、データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - MonitoringEngine: 各モニタの統合、アラート／Kill Switch 連携
  - AlertManager: LINE Messaging API へのプッシュ通知（オプション）
- 実行エンジン起動スクリプト（ExecutionEngine 起動補助）: run_execution.py
  - KABUSYS_ENV=paper_trading の場合はモックブローカーを用いて paper_trading DB に記録（本番 DB と分離）
- 監視ループ起動スクリプト: run_monitoring.py（ポーリングで監視情報を永続化）
- ポートフォリオ構築:
  - 候補選定、等加重/スコア加重、セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、リスクベース配分、aggregate cap のスケーリング）
- リサーチ:
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI 関連:
  - news_nlp: raw_news を LLM（OpenAI）で評価して ai_scores に書き込み
  - regime_detector: ma200 とマクロニュースの LLM 判定を合成して market_regime に書き込み
- ツール:
  - paper_verification_report: ペーパートレード DB を集計して検証レポートを生成

セットアップ手順（ローカル開発向け）
1. Python 環境
   - Python 3.9+ を推奨（コードは型注釈を使用）。
   - 仮想環境を作成して有効化してください（venv / conda 等）。

2. 必要パッケージをインストール
   - 最低限の依存（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - PyYAML（config の YAML 検証に必要。ただし必須ではない）
   - 例: pip install duckdb psutil requests openai PyYAML

3. リポジトリルートに移動し .env を作成
   - .env を手動作成するか、対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - .env に必要な環境変数（下記参照）を設定してください。
   - .env は絶対に公開リポジトリにコミットしないでください（秘密情報を含む）。

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 問題があれば修正してください。--strict オプションで警告も失敗扱いにできます。

5. 初期 DB / データディレクトリ
   - デフォルトは data/ 以下のファイルを使用します（data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db 等）。
   - 必要に応じて事前にディレクトリを作成してください。多くのスクリプトは起動時に親ディレクトリを自動作成しますが、アクセス権に注意してください。

使い方（主要コマンド）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- 監視ループ起動（System / Trade / Risk をポーリングして monitoring DB に書き込む）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - 監視プロセスはプロセス優先度を high に設定します（set_process_priority）。

- 実行エンジン起動（ExecutionEngine をバックグラウンドスレッドで起動）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、専用の paper_trading DB（デフォルト data/paper_trading.db）を使用し、MockBrokerClient を使って発注のテストを行います。
  - 実行中は data/execution.pid に PID を書き込みます。停止は stop フラグや kill.flag により制御されます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（Python API）
  - ニュース NLP スコアリング:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)  # api_key 未指定時は OPENAI_API_KEY 環境変数を使用
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - これらは CLI エントリポイントを持たないため、Python スクリプトや管理タスクから呼び出して使用します。

主要設定項目（環境変数）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 主要オプション（デフォルト値）
  - KABUSYS_ENV: 実行環境 (development | paper_trading | live) — default: development
  - DUCKDB_PATH: DuckDB ファイルパス — default: data/kabusys.duckdb
  - SQLITE_PATH: SQLite（監視 DB）パス — default: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite — default: data/paper_trading.db
  - LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）— default: INFO
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
  - OPENAI_API_KEY: OpenAI の API キー（news_nlp / regime_detector で使用）
  - PAPER_FILL_MODE: paper_trading 時のモック約定挙動 — instant | partial | never | reject（default: instant）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、default: 60）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（開発用。0推奨）

停止／キルフラグについて
- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring と run_execution が監視する「停止フラグ」ファイル。存在するとそれぞれのループは終了します（run_monitoring では検出したら監視ループを抜ける）。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch により書き込まれる「実行エンジン停止」フラグ。主にリスク条件（ドローダウン・ポジション上限）を満たしたときに作成され、ExecutionEngine 停止トリガとなります。
- execution.pid（data/execution.pid）
  - run_execution が PID を書き込むファイル。SystemMonitor はこの PID ファイルをチェックして実行プロセスの死活検出（stale PID）の判定を行います。

ディレクトリ構成（主要）
- src/kabusys/
  - __init__.py — パッケージ定義、__version__
  - config.py — 環境変数管理、.env 自動読み込みロジック、Settings クラス
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証ツール
  - run_monitoring.py — SystemMonitor ポーリングループの起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（Execution 側の組み立て、スレッド起動）
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ永続化層（テーブル初期化・CRUD）
    - system_monitor.py — CPU/メモリ/ディスク、プロセス、データ鮮度監視
    - trade_monitor.py — 滞留注文・約定異常検知
    - risk_monitor.py — ドローダウン / ポジション上限監視、ダッシュボード更新
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - kill_switch.py — kill.flag 書き込み/管理
    - alert_manager.py — LINE 通知（Push）
  - execution/  (参照されるモジュール群)
    - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py, ...（ExecutionEngine に関係する実装）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケーリング・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — raw_news を LLM でスコア化して ai_scores に書き込む
    - regime_detector.py — マクロニュース + ma200 を合成して market_regime 判定
  - tools/
    - paper_verification_report.py — ペーパートレード DB 集計・レポート生成
  - utils/
    - process_priority.py — Windows / POSIX の差を吸収してプロセス優先度 / CPU affinity 設定

備考・注意点
- DB 分離:
  - 監視（monitoring）データは settings.sqlite_path（デフォルト data/monitoring.db）を使用します。run_execution は KABUSYS_ENV によって paper_trading 用 DB を使い分けます（paper_trading 時は settings.paper_sqlite_path を使用）。
- OpenAI 利用:
  - news_nlp / regime_detector は OPENAI_API_KEY を必要とします。API 呼び出しは堅牢化（リトライ、JSON バリデーション、部分成功の保護）されていますが、API キーとコストに注意してください。
- 権限:
  - プロセス優先度 / CPU affinity の設定は OS 権限に依存します。許可がない場合は警告ログを出してスキップします。
- テストと自動化:
  - validate_config.py や config_setup.py を CI に組み込むと安全です。--strict モードで警告も失敗扱いにできます。
- ログ:
  - 各スクリプトは logging.basicConfig(level=INFO) を呼ぶため LOG_LEVEL を環境変数で調整できます。

以上が本コードベースの概略 README です。実際に運用する場合は、各 config/*.yaml（strategy_config 等）や ExecutionEngine の実装（ブローカークライアント、注文管理ロジック）を確認し、必要なテストを十分に行ってください。必要であれば README に追記する項目（systemd ユニット例、Dockerfile、CI 設定、より詳細な環境変数の一覧など）を指定してください。