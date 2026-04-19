KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なフレームワークです。
主要機能は戦略のリサーチ（ファクター計算・特徴量解析）、ポートフォリオ構築、注文実行（本番／ペーパートレード）、監視（プロセス/データ鮮度/リスク）および、ニュースを用いた AI スコアリングです。

現在のパッケージバージョン: 0.1.0

主な特徴
--------
- 戦略・研究
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- ポートフォリオ構築
  - 候補選定（スコア/等金額）、重み計算、ポジションサイズ決定（リスクベース）
  - セクター集中制限、レジーム乗数
- 注文実行
  - ExecutionEngine を介した注文管理（本番／ペーパートレード分離）
  - RiskManager / OrderManager / Reconciler などの実装を想定
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を統合した MonitoringEngine
  - kill.flag による外部からの停止シグナル
  - 監視ログは SQLite（monitoring.db）に保存
- AI連携
  - OpenAI を使ったニュースセンチメント評価（ai.news_nlp）
  - マクロセンチメントを用いた市場レジーム判定（ai.regime_detector）
- ユーティリティ
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成ツール

前提条件 / 必要パッケージ
-----------------------
- Python 3.10 以上（typing の | 記法が使われています）
- 必須（例）:
  - duckdb
  - psutil
  - openai
- 任意（機能により必要）:
  - PyYAML（config/*.yaml の検証に使用）
- 標準ライブラリ: sqlite3, logging, threading, datetime 等

（実際の requirements.txt はプロジェクトに含めてください。上記はコードベースから推測した例です）

セットアップ手順
---------------
1. リポジトリをクローン / 展開
   - プロジェクトルートには src/ 配下にパッケージが存在します。

2. 仮想環境を作成して依存パッケージをインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install duckdb psutil openai PyYAML

3. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants / kabuAPI / DB パス / LOG_LEVEL などを設定します。
   - .env は絶対に Git へコミットしないでください（秘密情報を含むため）。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います。

5. DB 初期化
   - 監視用 SQLite（デフォルト: data/monitoring.db）や DuckDB（data/kabusys.duckdb）は
     実行スクリプトが自動で初期化（必要テーブル作成）します。
   - Paper Trading を使う場合は data/paper_trading.db（デフォルト）が使用されます。

実行方法（基本）
----------------
- 実行エンジン（注文処理）起動:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用いて data/paper_trading.db に記録し、本番 DB と分離されます。
    - 起動時に data/stop_requested.flag があれば起動せず終了します。
    - プロセス優先度を high に設定（set_process_priority）。
    - 実行中の停止は data/stop_requested.flag を書き込むか kill.flag により制御できます。
    - 実行時に pid ファイル（デフォルト data/execution.pid）を利用します。

- 監視プロセス起動:
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（秒、デフォルト 60）。
    - 監視は設定にかかわらず本番 sqlite_path（data/monitoring.db）を使用します（監視ログ集約のため）。
    - SystemMonitor が定期的にチェックし、MonitoringEngine 経由でアラートや KillSwitch 評価を行えます。
    - 停止フラグ（data/stop_requested.flag）を検知するとループ終了。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

環境変数（主要）
----------------
- 必須（例）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB）
- ロギング:
  - LOG_LEVEL（例: INFO） / LOG_DIR（ログ保存ディレクトリ、デフォルト logs/）
- AI:
  - OPENAI_API_KEY（ai.news_nlp / ai.regime_detector で使用）
- その他:
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒）
  - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1。デフォルト 0。production では 0 推奨）
  - KILL_FLAG_PATH（デフォルト data/kill.flag）

停止 / Kill Switch
------------------
- kill.flag（デフォルト data/kill.flag）
  - KillSwitch によって書き込まれると ExecutionEngine に停止指示を送れます。
  - KillSwitch は RiskMonitor の結果（例: drawdown, ポジション上限）に応じて作成します。
- stop_requested.flag（data/stop_requested.flag）
  - run_execution / run_monitoring がこのファイルの存在を検知するとループを抜け安全に終了します。
- PID ファイル:
  - data/execution.pid（ExecutionEngine が使用）

主要モジュールとディレクトリ構成
--------------------------------
（src/kabusys 以下、主要ファイルのみ抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py       — 起動前設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py            — ニュースを OpenAI でスコアリングして ai_scores に書き込み
    - regime_detector.py     — マクロ + MA200 で市場レジーム判定
  - research/
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - portfolio/
    - portfolio_builder.py   — 候補選定・等重/スコア重み
    - position_sizing.py     — 株数決定・資金配分・単元処理
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - monitoring/
    - monitoring_db.py       — SQLite の永続層（テーブル作成・読み書き）
    - system_monitor.py      — システム / データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねる
    - kill_switch.py         — kill.flag 書き込みロジック
    - (他: trade_monitor, alert_manager など想定)
  - utils/
    - logging_setup.py       — 統一的なログ設定（stdout + 日次ローテーションファイル）
    - process_priority.py    — プラットフォーム横断でのプロセス優先度設定
  - data/                    — 実行時に使用されるデータファイル（logs/, data/ 以下を想定）

使い方の例
-----------
- .env を作成:
  - python -m kabusys.config_setup
- 設定を検証:
  - python -m kabusys.validate_config
- 監視の単発実行（テスト）:
  - Python REPL またはテストで MonitoringEngine を組み立て run_once を呼ぶ
- 監視のデーモン起動:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- 注文エンジン起動（ペーパー）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- PaperTrading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

注意事項 / ベストプラクティス
------------------------------
- .env は秘密情報を含むためバージョン管理に含めないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します。自動クリアは危険です。
- OpenAI API を利用する機能はネットワーク呼び出し/料金が発生します。テスト時はモック化してください。
- ログディレクトリ作成に失敗した場合はコンソールに警告が出て、ファイルログは無効化されます。LOG_DIR を適切に設定してください。
- Monitoring は監視 DB を使用して稼働状況やアラート情報を永続化します。運用時は監視 DB のバックアップ戦略を検討してください。

補遺（内部実装に関するメモ）
-------------------------
- run_monitoring は MONITOR_POLL_INTERVAL でポーリング（デフォルト 60 秒）。不正値はデフォルトにフォールバックします。
- run_execution は paper_trading モード時、paper_sqlite_path に完全分離して記録します。
- logging_setup.setup_logging は stdout と日次ローテーションをルートロガーに設定します。
- process_priority.set_process_priority は Windows / POSIX の差を吸収して優先度を設定します（権限がない場合は警告でスキップ）。
- monitoring_db.init_monitoring_db は既存 DB を壊さないマイグレーション処理（ALTER TABLE 追加など）を含みます。

ライセンス / 貢献
-----------------
README に特定のライセンス記載がないため、用途や配布方法に応じて適切なライセンスを追加してください。
バグ報告・機能提案は Issue を使ってください。

以上がプロジェクトの概要・セットアップ・使い方のまとめです。追加で README に載せたいサンプル設定例（.env.example）や requirements.txt、デプロイ手順があればそれらのテンプレートも作成できます。必要であれば教えてください。