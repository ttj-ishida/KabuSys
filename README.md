KabuSys — 日本株自動売買システム
================================

この README はこのリポジトリのコードベース（src/kabusys 以下）を前提に作成しています。プロジェクトは自動発注エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ／ポートフォリオ構築、AI 補助（ニュース NLP / レジーム判定）などから構成されます。

プロジェクト概要
--------------
KabuSys は日本株向けの自動売買システムの基盤ライブラリです。主な目的は次の通りです：

- 発注エンジン（ExecutionEngine）：ブローカークライアント経由で発注を管理・実行（本番／ペーパートレード対応）
- 監視コンポーネント：システム稼働状況、注文ログ、リスク指標を定期的に監視し、kill フラグやアラートを発生
- ポートフォリオ構築：シグナル選定、重み付け、ポジションサイズ計算、セクター制限など純関数群
- リサーチ：ファクター計算（モメンタム／バリュー／ボラティリティ）、特徴量探索、IC 計算
- AI 補助：ニュースのセンチメントスコア化（OpenAI 使用）、市場レジーム判定
- ツール：ペーパートレード検証レポート生成などユーティリティ

主な機能一覧
--------------
- 設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート検出）
  - Settings クラス：環境変数に基づく各種設定値
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による paper_trading 切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL による間隔調整）
- 監視（kabusys.monitoring）
  - system_monitor, trade_monitor, risk_monitor：DB へログ記録とアラート判定
  - monitoring_db：SQLite スキーマの初期化・永続化処理
  - monitoring_engine：複数モニタを束ねるループ実行ロジック
  - kill_switch：フラグファイルで ExecutionEngine を停止する仕組み
- 発注周り（kabusys.execution）※実装ファイルは本スニペットに含まれていませんがファクトリ等を参照
  - ブローカークライアントファクトリ（本番 / モック切替）
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine
- ポートフォリオ（kabusys.portfolio）
  - 銘柄選定、等金額・スコア重み、ポジションサイズ計算、セクター上限、レジーム乗数
- リサーチ（kabusys.research）
  - ファクター計算（momentum, value, volatility）
  - 将来リターン、IC、統計サマリ、ランク変換
- AI（kabusys.ai）
  - news_nlp: OpenAI を用いたニュースセンチメントの取得と ai_scores への書き込み
  - regime_detector: ma200 とマクロニュースの LLM スコアを組み合わせた市場レジーム判定
- ツール（kabusys.tools）
  - paper_verification_report: ペーパートレーディング DB の検証レポート生成
- ユーティリティ（kabusys.utils）
  - logging_setup: 一貫したログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度・CPU affinity 設定

セットアップ手順
----------------
1. Python 環境（推奨: 3.10+）を用意
   - 仮想環境を作成して有効化してください（venv / poetry 等）。

2. 必要パッケージをインストール
   - 最低限の依存例:
     pip install duckdb psutil openai
   - 検証時に YAML の内容確認を行う場合:
     pip install PyYAML
   - （プロジェクトに requirements.txt があればそれを使用してください）

3. .env の用意
   - 対話式ウィザードを使って作成:
     python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに .env を作成。
   - 主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=...  （AI 機能を使う場合）
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0

   - 自動読み込みはデフォルトで有効。無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証
   - validator を実行して環境をチェック:
     python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     python -m kabusys.validate_config --strict

5. ディレクトリ・ファイル
   - デフォルトで使用されるパス:
     - SQLite (monitoring): data/monitoring.db
     - DuckDB: data/kabusys.duckdb
     - Paper trading SQLite: data/paper_trading.db
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログディレクトリ: logs/（設定で変更可能）

使い方（実行例）
----------------
- 実行エンジン（ExecutionEngine）を起動:
  - 通常（本番／ペーパーは KABUSYS_ENV で切替）:
    python -m kabusys.run_execution
  - ポイント:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します（本番 DB と完全分離）。
    - ExecutionEngine は停止フラグ（data/stop_requested.flag）を検知すると優雅に停止します。
    - PID ファイル（data/execution.pid）が書き出されます。

- 監視ループを起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト: 60）。
  - 監視は Settings の sqlite_path（監視用 DB）を使用します。環境にかかわらず本番 sqlite_path を参照する設計です。
  - 停止は data/stop_requested.flag を作成することで行えます（監視プロセスが検知して終了）。

- .env を対話式で作成/更新:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config

- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report
  期間指定例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（プログラム的利用）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

運用上の注意
-------------
- KABUSYS_ENV の有効値: development, paper_trading, live。live を設定すると本番向け挙動になるため慎重に。
- Kill Switch: RiskMonitor が条件を満たすと data/kill.flag に理由を書き込み、ExecutionEngine に停止シグナルを送ります。KILL_FLAG_CLEAR_ON_START = 1 にすると起動時に自動で消去されますが、本番では 0 を推奨します。
- ログ: kabusys.utils.logging_setup.setup_logging により stdout と logs/<app_name>.log に出力（デフォルト logs/）。
- 権限: process_priority.set_process_priority を呼んで優先度を上げますが、OS/権限により失敗する場合があります（警告ログのみ）。

ディレクトリ構成（主なファイル）
------------------------------
以下は src/kabusys 以下の主要ファイルと役割（この README 作成時点のスニペットに基づく）です。

- src/kabusys/
  - __init__.py                 — パッケージ定義（__version__ 等）
  - config.py                   — Settings クラス、.env 自動読み込み、環境変数検証
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 起動前設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring ポーリングループ起動スクリプト

- src/kabusys/execution/        — 発注エンジン関連（Engine, OrderManager, RiskManager 等）
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- src/kabusys/monitoring/
  - monitoring_db.py            — SQLite スキーマ初期化と永続化 API（MonitoringDB）
  - system_monitor.py           — システム・データ鮮度監視
  - trade_monitor.py            — 注文ログ監視（存在）
  - risk_monitor.py             — ドローダウン・ポジション上限監視
  - kill_switch.py              — kill.flag の作成 / 解除
  - alert_manager.py            — 通知管理（存在）

- src/kabusys/portfolio/
  - portfolio_builder.py        — 候補選定・重み計算
  - position_sizing.py          — 発注数量決定・スケーリング
  - risk_adjustment.py          — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py          — ファクター計算（momentum/value/volatility）
  - feature_exploration.py      — 将来リターン・IC・統計サマリ

- src/kabusys/ai/
  - news_nlp.py                 — ニュース NLP（OpenAI）による銘柄別センチメント
  - regime_detector.py          — レジーム判定（ETF ma200 + マクロ NLP）

- src/kabusys/utils/
  - logging_setup.py            — ログ設定
  - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート

補足（トラブルシューティング）
------------------------------
- DuckDB / SQLite のファイルパスは Settings で変更可能。パスの親ディレクトリが無ければ警告を出しますが、起動時に自動生成されることがあります。
- validate_config の YAML 検証は PyYAML が無いとスキップされます（警告）。
- OpenAI 関連機能を利用するには OPENAI_API_KEY を設定してください。API 呼び出しでの一時的なエラー（429 / タイムアウト / 5xx）は内部でリトライ処理を行いますが、最終的に失敗した場合はスキップして継続します（フェイルセーフ設計）。

ライセンス・貢献
----------------
- 本リポジトリのライセンス表記はここには含まれていません。利用・配布前に LICENSE ファイルを確認してください。
- バグ報告や機能提案は Issue を通じて行ってください。

以上。質問や README の補足（例: 具体的な .env.example、requirements.txt の生成、起動プロセスの systemd ユニット例など）が必要であれば教えてください。