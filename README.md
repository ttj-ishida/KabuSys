# KabuSys

日本株自動売買システムの軽量コアライブラリ（ドキュメント）。  
このリポジトリは、アルゴリズム取引のためのデータ処理・ポートフォリオ構築・実行エンジン・監視・AI 補助モジュール等を含むモジュール群を提供します。

注意: この README は提供されたソースコード (src/kabusys 以下) を基にした概要と利用手順です。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提（依存）とインストール
- セットアップ手順（.env 作成 → 検証）
- 実行方法（Execution / Monitoring / ツール類）
- 環境変数の説明（主要項目）
- ディレクトリ構成（ファイル一覧と説明）
- 運用上の注意

---

プロジェクト概要
- KabuSys は日本株自動売買を想定したライブラリ群です。  
  - データ取得・DuckDB を用いた分析（research / ai）  
  - ポートフォリオ構築（選定、重み付け、ポジションサイズ計算）  
  - ExecutionEngine（発注ロジック、リスク管理、Order 管理）  
  - 監視（SystemMonitor、TradeMonitor、RiskMonitor、Kill Switch、アラート）  
  - Paper Trading（本番 DB と分離されたシミュレーション）  
  - OpenAI を利用したニュース NLP / レジーム判定サポート

---

主な機能一覧
- config_setup: 対話式ウィザードで .env を作成／更新
- validate_config: .env と config/*.yaml（存在する場合）の検証 CLI
- run_execution: 実際の ExecutionEngine を起動するスクリプト（KABUSYS_ENV により本番 / ペーパートレード切替）
- run_monitoring: SystemMonitor のポーリングループ（監視ログを SQLite に永続化）
- monitoring: system_status / trade_logs / risk_logs / dashboard 用の永続化層と監視ロジック
- portfolio: 候補選定、重み計算、ポジションサイズ決定、セクター制限、レジーム乗数
- research: DuckDB 接続を使ったファクター計算（momentum / value / volatility）や特徴量解析
- ai: OpenAI を使ったニュース NLP（score_news）と市場レジーム判定（score_regime）
- tools: Paper Trading の検証レポート生成（paper_verification_report）
- utils: ロギング設定、プロセス優先度／CPU affinity 設定ユーティリティ

---

前提（依存）とインストール
- Python 3.9+（型注釈等から想定）
- 主な外部パッケージ（最低限）
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - pyyaml （config YAML 検証を行う場合、任意）
- インストール例（仮）
  - pip install duckdb psutil openai pyyaml
- リポジトリをクローン後、仮想環境作成と依存インストールを推奨

---

セットアップ手順（.env の準備）
1. リポジトリをクローンして作業ディレクトリへ移動
2. 対話式ウィザードで .env を作成（推奨）
   - python -m kabusys.config_setup
   - ウィザードは .env に以下などを書き込みます（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能利用時）
     - LOG_LEVEL / LOG_DIR 等
   - .env は絶対に Git にコミットしないでください
3. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数不足や主要ファイルの不備を検出できます
   - --strict を付けると警告も失敗（exit 1）になります

環境変数の自動読み込み
- デフォルトではプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し .env / .env.local を自動読み込みします。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

使い方（実行コマンド例）

1) ExecutionEngine を起動（本番 or ペーパートレード）
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合:
    - MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にすべて記録します（本番 DB と分離）。
  - 実行前に kill flag（data/kill.flag）を確認し、存在する場合は起動しません。
  - 停止は外部から data/stop_requested.flag を置くことで実行中のループに検出させ停止できます（または kill.flag を使って停止トリガーを送る運用も有り）。

2) Monitoring を起動（システム監視）
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト 60 秒）
- python -m kabusys.run_monitoring
  - 監視は常に（KABUSYS_ENV に関わらず）本番 sqlite_path（SQLITE_PATH）を使用して記録します
  - 監視中に data/stop_requested.flag が存在するとループを終了します

3) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB は data/paper_trading.db。--db でパス指定可

4) AI 関連（プログラムから利用）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続と target_date を与えてニュースセンチメントを ai_scores テーブルへ書き込みます
  - api_key を省くと環境変数 OPENAI_API_KEY を参照
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - レジーム判定を market_regime テーブルへ書き込みます

5) ロギング
- logging は kabusys.utils.logging_setup.setup_logging を通じて統一的に設定されます
- デフォルトログディレクトリ: logs/
- 各アプリ名（monitoring / execution 等）ごとに日次ローテーションされた logs/<app_name>.log が作られます

停止フラグ・Kill Switch（運用）
- data/stop_requested.flag: run_monitoring / run_execution のループを止めるための外部フラグ（存在確認して安全に終了）
- data/kill.flag: KillSwitch により書き込まれるフラグ（ExecutionEngine に停止アラート／停止命令として扱う想定）
- PID ファイル: data/execution.pid（デフォルト）等で実行プロセス管理

---

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 実行／動作制御
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- DB パス
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視 DB デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB デフォルト data/paper_trading.db
- AI
  - OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime で使用）
- その他
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
  - KILL_FLAG_CLEAR_ON_START: 本番での Kill フラグ自動クリア設定（0/1）

詳しくはソースの docstring（config.py, run_monitoring.py, run_execution.py など）を参照してください。

---

ディレクトリ構成（src/kabusys の主なファイルと役割）
- __init__.py
  - パッケージ公開情報、バージョン
- config.py
  - 環境変数の読み込み・設定ラッパー（Settings クラス）
  - .env 自動読み込み（.env, .env.local）、バリデーション helper
- config_setup.py
  - 対話式 .env 作成ウィザード
- validate_config.py
  - 起動前設定検証 CLI（.env / config/*.yaml の存在や値検証）
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading の分離・MockBroker 対応）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）
- utils/
  - logging_setup.py: 統一ログ設定（コンソール + 日次ファイルローテーション）
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ（psutil ベース）
- monitoring/
  - monitoring_db.py: SQLite 用永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: システム状態・データ鮮度監視
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: Kill Switch（フラグファイル操作）
  - monitoring_engine.py: 各 Monitor を束ねるエンジン（テスト用 run_once / 本番 run）
  - other monitors: trade_monitor / alert_manager 等（実装参照）
- execution/
  - ExecutionEngine, OrderManager, Reconciler, RiskManager, BrokerFactory 等（発注系）
- portfolio/
  - portfolio_builder.py: 候補選定・重み付け
  - position_sizing.py: 発注株数決定（リスク基準・単元丸め・スケーリング）
  - risk_adjustment.py: セクター上限・レジーム乗数
- research/
  - factor_research.py: ファクター計算（momentum/value/volatility）
  - feature_exploration.py: 将来リターン・IC 計算・統計サマリ
- ai/
  - news_nlp.py: ニュース NLP スコアリング（OpenAI API で記事を評価して ai_scores に書込）
  - regime_detector.py: 市場レジーム判定（MA200 + マクロ NLP 合成）
- tools/
  - paper_verification_report.py: Paper Trading の検証レポート出力

（上記は主要ファイルの抜粋です。詳細はソースコード内の docstring を参照してください。）

---

運用上の注意
- .env に API キーやパスワードを保存する場合、絶対にバージョン管理に含めないでください。
- KABUSYS_ENV=live の設定は本番実行になります。validate_config は live 時に追加注意を促します（LINE 通知設定など）。
- run_execution/run_monitoring は外部フラグファイル（data/stop_requested.flag, data/kill.flag）に依存するため、運用ルールを整備してください。
- OpenAI 等の API 呼び出しはネットワーク失敗時にリトライ・フェイルセーフの実装がありますが、API コストとレート制限を考慮して運用してください。
- DuckDB / SQLite ファイルのバックアップ、ログローテーション（logs/）の管理を行ってください。

---

参考コマンド一覧（まとめ）
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードの docstring を要約したものです。各モジュールの詳細な使い方や API、設定項目は該当ソースファイル内のドキュメント（docstring）を参照してください。必要であれば、各モジュールのサンプル使用例や運用手順書を追加で作成できます。