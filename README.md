KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行う小規模なフレームワークです。戦略のポートフォリオ構築・ポジションサイジング・リスク制御、監視（システム／注文／リスク）、Paper Trading 検証ツール、さらに OpenAI を使ったニュースセンチメント／レジーム判定の機能群を含みます。  
本リポジトリは主に純粋関数的モジュール（ポートフォリオ構築等）と、ランタイム用の起動スクリプト（ExecutionEngine/Monitoring）を提供します。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）へ記録して本番 DB と分離
  - PID ファイル管理・停止フラグによる安全停止
- Monitoring（run_monitoring.py / MonitoringEngine）
  - system, trade, risk 各モニタで監視・ログ保存（SQLite）
  - Kill Switch（ルールに基づく停止判定）・アラート発行のフック
  - MONITOR_POLL_INTERVAL によるポーリング間隔の変更（デフォルト 60 秒）
- 設定関連 CLI
  - 対話式 .env 作成支援（config_setup.py）
  - 起動前設定検証ツール（validate_config.py）: --strict オプションあり
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB から稼働率・注文成功率・レイテンシ等を集計し PASS/FAIL 判定を出力
- ポートフォリオ構築ライブラリ（portfolio module）
  - 候補選択、等重／スコア重み、セクターキャップ、レジーム乗数、ポジションサイジング
- リサーチ機能（research module）
  - Momentum / Volatility / Value 等のファクター計算、将来リターン、IC 計算、統計サマリ
- AI 機能（ai module）
  - OpenAI を用いたニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）
- ユーティリティ
  - 環境変数ローダー（config.py）、プロセス優先度制御（utils/process_priority.py）等
- 永続層（monitoring_db.py）
  - 監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）を SQLite に保存。マイグレーションを一部自動で実行。

セットアップ
-----------
1. 必要要件（例）
   - Python 3.9+
   - 必須パッケージ: duckdb, psutil
   - AI 機能を使う場合: openai
   - （埋め込み YAML 検証を行う場合）PyYAML

   例: pip でインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```

2. プロジェクトルートに移動（.git または pyproject.toml を持つ場所）
3. data ディレクトリ作成（実行時に自動作成される場合もありますが事前作成推奨）
   ```
   mkdir -p data
   ```

4. 環境変数 (.env) の作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env を手動で作成（推奨設定例）
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```

5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

使い方
------
起動スクリプトと主要コマンド:

- ExecutionEngine を起動（本番／ペーパー両対応）
  ```
  python -m kabusys.run_execution
  ```
  動作ポイント:
  - KABUSYS_ENV 環境変数で実行モードを切替: development / paper_trading / live
  - paper_trading の場合は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）を使用
  - 実行中は data/execution.pid に PID を書き、停止フラグ data/stop_requested.flag を置くと停止します
  - Settings で PID ファイルパスや kill_flag のパスを上書き可能

- Monitoring を起動（システム／注文／リスクの定期チェック）
  ```
  python -m kabusys.run_monitoring
  ```
  動作ポイント:
  - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で変更可（例: MONITOR_POLL_INTERVAL=30）
  - 監視処理は常に本番の sqlite_path（Settings.sqlite_path）を使って記録します
  - data/stop_requested.flag を作成するとループを終了します

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは --db で指定、なければ環境変数 PAPER_TRADING_SQLITE_PATH、最終的に data/paper_trading.db を使用

- AI 機能（ニューススコア／レジーム判定）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定する必要があります
  - news_nlp.score_news / regime_detector.score_regime を呼び出して DuckDB 上の raw_news 等を処理します（ライブラリ関数）

停止・Kill Switch
- 実行中の ExecutionEngine を外部から停止する方法:
  - "stop_requested.flag"（data/stop_requested.flag）を作ると run_execution/run_monitoring のループは検知して終了します（run scripts 内の STOP_FLAG）
  - KillSwitch（監視側）は内部基準（ドローダウン超過、ポジション上限等）により data/kill.flag を書き、実行系に停止シグナルを与えます（ExecutionEngine は kill.flag を検知して停止します）
- 起動時に KILL_FLAG_CLEAR_ON_START=1 にすると kill.flag を自動クリアします（本番では 0 推奨）

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を利用する際の API キー
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 各種パス・動作制御

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 自動読み込みと Settings クラス
  - config_setup.py          — 対話式 .env 作成ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト（PID / stop flag 管理）
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 + MonitoringDB ラッパ
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — 注文滞留 / 約定異常監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - monitoring_engine.py   — 各モニタ統合・ポーリング管理
    - kill_switch.py         — kill.flag 書込みユーティリティ
    - alert_manager.py       — （アラート送信のためのフック）
  - execution/                — Execution 関連（OrderManager 等: 実装はリポジトリに依存）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースを OpenAI でスコアリングして ai_scores へ書込む
    - regime_detector.py     — マクロ + ma200 による日次レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

補足・運用上の注意
-----------------
- .env は決してリポジトリにコミットしないでください（config_setup.py のヘッダにも明示済み）。
- 本番モード（KABUSYS_ENV=live）では各種アラート・Kill Switch の設定を必ず確認してください（LINE 設定など）。
- Paper Trading モードは本番 DB と分離されるため安全にテストできます。
- OpenAI など外部 API 呼び出しは失敗時に安全側フォールバック（例: スコア 0.0）を行うよう設計されていますが、API キーやレート制限の管理には注意してください。
- SQLite / DuckDB ファイルのバックアップ・移行方法は運用ポリシーに合わせて行ってください。

ライセンス
---------
（ここにプロジェクトのライセンス表記を入れてください）

その他
-----
- 詳細な設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）が参照される想定です。実装内部に多くの注釈・設計意図がコメントとして残されていますので、機能拡張や運用変更の際は該当箇所を参照してください。

必要であれば、README に含める具体的な起動例や systemd ユニット、Dockerfile、あるいは CI 用コマンドの雛形などを追加できます。どの情報を詳しく追記しますか？