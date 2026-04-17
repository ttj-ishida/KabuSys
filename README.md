KabuSys — 日本株自動売買システム（README）
=======================================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。本リポジトリには以下の主要機能を持つモジュール群が含まれます。

- 監視（Monitoring）: システム状態・データ鮮度・注文状態・リスク（ドローダウン等）を定期的にチェックし、ログとアラートを出す
- Execution（発注エンジン）: ブローカークライアントを用いた注文発行、ペーパートレード時のモックブローカー対応
- Portfolio（ポートフォリオ構築）: 候補選定、重み付け、ポジションサイズ計算、セクター制限などの純粋関数群
- Research（リサーチ）: DuckDB を用いたファクター計算・特徴量探索
- AI（LLM）連携: ニュースのセンチメント評価（OpenAI）および市場レジーム判定
- ユーティリティ: 設定ウィザード、設定検証、プロセス優先度や CPU affinity 設定など

主な設計方針:
- DB（DuckDB / SQLite）を分析・監視の永続層として利用
- Paper Trading と本番 DB は分離（PAPER_TRADING_SQLITE_PATH を使用）
- LLM 呼び出しはフェイルセーフ（失敗時フォールバック）かつルックアヘッドバイアスを避ける設計

機能一覧
--------
- run_monitoring: SystemMonitor をポーリング（デフォルト 60 秒、環境変数 MONITOR_POLL_INTERVAL で上書き可）。monitoring は常に settings.sqlite_path を使用します（KABUSYS_ENV に依存しない）。
- run_execution: ExecutionEngine を起動。KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用して data/paper_trading.db に書き込む（本番 DB と分離）。
- config_setup: .env の対話式ウィザード生成/更新。
- validate_config: .env および config/*.yaml の起動前検証（--strict オプションで警告も失敗扱いに）。
- tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率、約定率、P95 レイテンシなど）。
- portfolio: 候補選定（select_candidates）・重み計算（等分/スコア加重）・位置数計算（calc_position_sizes）・セクター制限/レジーム乗数（apply_sector_cap / calc_regime_multiplier）。
- research: ファクター計算（モメンタム/ボラティリティ/バリュー）、将来リターン、IC、統計サマリー。
- ai.news_nlp / ai.regime_detector: OpenAI を用いた記事センチメント評価と市場レジーム判定（gpt-4o-mini を想定）。失敗時は安全側のフォールバック処理あり。
- monitoring: system_monitor, trade_monitor, risk_monitor, alert_manager, monitoring_db（永続化層）等。kill_switch により条件を満たすと ExecutionEngine 停止用の kill.flag を書き込む。

セットアップ手順
--------------
1. Python と依存パッケージ
   - 推奨: Python 3.9+（プロジェクトの要件ファイルがないため適宜確認）
   - 主な依存: duckdb, psutil, requests, openai, PyYAML（任意。config/*.yaml の検証に使用）
   - 例（pip）:
     pip install duckdb psutil requests openai PyYAML

   ※ 仮想環境（venv や conda）を使用することを推奨します。

2. リポジトリルート構成（README 下の「ディレクトリ構成」を参照）を確認し、data ディレクトリなどが必要なら作成してください（起動時に自動作成される箇所もありますが先に作ると分かりやすいです）:
   mkdir -p data

3. .env の準備
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 重要なその他環境変数（省略時はデフォルトを使用）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - OPENAI_API_KEY: OpenAI を使うとき必須
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
     - LOG_LEVEL: DEBUG/INFO/...
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時のモック約定挙動）
     - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
     - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

4. 設定検証（任意だが推奨）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. 必要な DB 初期化
   - monitoring 用の SQLite テーブルは起動時に自動作成されます（init_monitoring_db）。
   - DuckDB 用のテーブルはプロジェクト内のデータインジェストスクリプト等で準備してください（prices_daily, raw_financials, raw_news 等を想定）。

使い方（実行例）
----------------

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループを起動（デフォルトは MONITOR_POLL_INTERVAL=60 秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 補足: run_monitoring は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します。

- Execution（発注エンジン）を起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定するとペーパートレードモードになり、settings.paper_sqlite_path（デフォルト data/paper_trading.db）に書き込みます。本番 DB とは分離されます。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または指定 DB:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI / LLM 関数の呼び出し（Python から）
  - ニューススコアリング（例）
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026,4,10), api_key="sk-...")

  - レジームスコア（例）
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026,4,10), api_key="sk-...")

注意点 / 運用上のヒント
-----------------------
- プロセス優先度: run_monitoring / run_execution は起動時に set_process_priority("high") を呼びます（psutil を使用）。権限により設定できない場合は警告が出ます。
- 停止制御:
  - run_monitoring/run_execution はプロジェクトルートの data/stop_requested.flag を検知してループを終了します（運用で即時停止させたい場合に利用）。
  - Kill Switch（kill.flag）: monitoring の判定処理（KillSwitch）により data/kill.flag が書き込まれると ExecutionEngine 停止のトリガーになります。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 をセットしていると自動クリアされるため本番では 0 推奨。
- Paper Trading の分離:
  - paper_trading 環境は MockBroker を使用し、専用 SQLite（PAPER_TRADING_SQLITE_PATH）にのみ書き込みます。本番 DB に影響を与えません。
  - PAPER_FILL_MODE によりモックの約定挙動を制御できます（instant/partial/never/reject）。
- LLM 呼び出し:
  - OPENAI_API_KEY が必要です。失敗時のリトライやフォールバックが実装されていますが、API 利用はコストとレイテンシに注意してください。
  - news_nlp / regime_detector は外部 API へ依存するためテスト時は _call_openai_api をモックすることを推奨します。
- config/*.yaml の検証には PyYAML があると詳細検査が可能です（無ければ警告になり検証はスキップされます）。
- ログレベルは LOG_LEVEL 環境変数で設定可能（Settings.log_level を参照）。

ディレクトリ構成（主要ファイル・モジュール）
------------------------------------
（src/kabusys 以下を示します）

- __init__.py
  - パッケージ情報（__version__ など）

- config.py
  - Settings クラス：環境変数の読み込み、デフォルト値、検証ロジック
  - .env の自動ロード（プロジェクトルート検出）機能を含む

- config_setup.py
  - 対話式 .env 生成ウィザード

- validate_config.py
  - 起動前チェック CLI

- run_monitoring.py
  - SystemMonitor のポーリングループ入口スクリプト

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading の分離対応）

- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化と CRUD（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU/Mem/Disk、プロセスの存在、データ鮮度チェック
  - trade_monitor.py: 滞留注文・約定価格異常チェック
  - risk_monitor.py: ドローダウン/ポジション上限チェック
  - kill_switch.py: kill.flag の書き込み/判定
  - monitoring_engine.py: 複数モニタを束ねるエンジン
  - alert_manager.py: LINE 通知（push）クラス

- execution/ (発注関連: BrokerFactory, ExecutionEngine, OrderManager など)
  - （発注ロジック、OrderRepository 等。run_execution がこれらを組み立てて稼働させます）

- portfolio/
  - portfolio_builder.py: 候補選定・重み付け
  - position_sizing.py: 株数計算・スケール調整
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: モメンタム / ボラ / バリュー等のファクター計算（DuckDB を使用）
  - feature_exploration.py: 将来リターン、IC、統計サマリー

- ai/
  - news_nlp.py: ニュース記事を OpenAI でスコアリングして ai_scores に書き込む処理
  - regime_detector.py: MA200 とマクロセンチメントを合成して market_regime を算出・保存

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成スクリプト

- utils/
  - process_priority.py: クロスプラットフォームでプロセス優先度 / CPU affinity 設定

その他ファイル・ディレクトリ（運用）
- data/: デフォルトの DB ファイル・PID/flag ファイル等を置くディレクトリ（例: data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）

補足（よくある運用質問）
-----------------------
- 監視ログ（SQLite）はどこ？
  settings.sqlite_path（デフォルト data/monitoring.db）です。run_monitoring は常にこのパスを使います。

- 停止させたい／起動を阻止したい場合
  - 直ちに監視やエンジンを止めたい: data/stop_requested.flag を作成すると run_monitoring / run_execution が検知して終了します（これらスクリプトは stop_requested.flag を監視します）。
  - リスク条件による停止（Kill Switch）: monitoring が条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側がこれを検知して停止します。

- Paper Trading と本番 DB の混同防止
  - KABUSYS_ENV=paper_trading のとき、run_execution は settings.paper_sqlite_path を使いデータを分離します。monitoring は settings.sqlite_path（常に）を使用する点に注意してください。

ライセンス・貢献
----------------
- 各自の内部ポリシーに従って導入・テストを行ってください。外部 API キー（OpenAI やブローカーなど）は機密情報として取り扱い、.env を必ず Git 管理対象外にしてください（config_setup でも警告を出しています）。

問題報告・改善提案
-----------------
- バグや改善案があれば issue を作成してください。ユニットテストやモックの追加、依存関係の固定（requirements.txt / poetry）を行うと導入が容易になります。

以上がこのコードベースの概要、セットアップ、使い方、およびディレクトリ構成です。必要があれば具体的な運用手順（systemd ユニット、Dockerfile、CI 設定など）や依存関係の固定化（requirements.txt／poetry.lock）例も作成します。どの情報が必要か教えてください。