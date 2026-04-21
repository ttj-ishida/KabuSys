KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）の実装コアを含みます。
主な機能は戦略のファクター計算、ポートフォリオ構築、発注実行エンジン、監視（監視ループ／Kill Switch）、
およびニュースの NLP スコアリング（OpenAI）などです。

以下はこのコードベースの README（日本語）です。

1. プロジェクト概要
------------------
KabuSys は以下のサブシステムで構成されます。

- Execution（発注エンジン）
  - Broker クライアント（本番/ペーパートレード切り替え）
  - OrderManager / RiskManager / Reconciler / ExecutionEngine
  - 発注ログは SQLite（paper_trading 時は専用 DB）に保存
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
  - 監視ログは SQLite に保存（monitoring.db）
  - ログやアラート条件に基づき Kill Switch を作動させ、Execution を停止可能
- Research / Portfolio
  - ファクター計算（momentum, value, volatility 等）
  - ポートフォリオ構築ロジック（候補選定・重み付け・ポジションサイズ計算）
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価 / 市場レジーム判定
- ユーティリティ
  - 設定管理（.env 読み込み）、ロギング設定、プロセス優先度設定など
- ツール
  - Paper Trading の検証レポート生成スクリプト など

2. 主な機能一覧
----------------
- 起動スクリプト
  - python -m kabusys.run_execution: ExecutionEngine を起動
  - python -m kabusys.run_monitoring: SystemMonitor のポーリングを開始
- 設定ヘルパー / 検証
  - python -m kabusys.config_setup: .env を対話式で作成・更新
  - python -m kabusys.validate_config: 環境変数・config/*.yaml の静的チェック
- 監視・Kill Switch
  - 監視結果を SQLite に永続化（system_status / trade_logs / risk_logs / dashboard 等）
  - 一定条件（ドローダウンやポジション上限）で kill.flag を書き込み Execution に停止指示
- ペーパートレード検証
  - python -m kabusys.tools.paper_verification_report: ペーパー DB から検証レポートを生成
- 研究用 / 分析
  - DuckDB を使ったファクター計算（momentum/value/volatility 等）
- ニュース NLP（OpenAI）
  - raw_news を集約して銘柄ごとにスコアを算出し ai_scores テーブルへ書き込み

3. 必要条件（想定）
-------------------
- Python 3.9+（パッケージのアノテーション等を想定）
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai
- 推奨 / 任意:
  - PyYAML（config 検証を行う場合）
- SQLite3: 標準ライブラリに同梱
- 注意: requirements.txt がない場合は下記のインストール例を参照してください。

4. セットアップ手順
-------------------
1) リポジトリをクローン
   - git clone <this-repo>

2) 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3) 必要パッケージをインストール
   例:
   - pip install duckdb psutil openai
   - (オプション) pip install pyyaml

   開発用途にパッケージをまとめてインストールする場合:
   - pip install -e .  # パッケージを編集可能インストール（プロジェクトに setup があれば）

4) .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードに従って必須値（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）を設定

   自動読み込み:
   - config.Settings はプロジェクトルートにある .env / .env.local を自動ロードします。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5) 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6) データディレクトリ
   - デフォルトで data/ 配下に SQLite / DuckDB / PID / フラグファイルが置かれます。
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更してください。

5. 使い方
---------

環境変数の例（.env に設定する主要項目の抜粋）
- KABUSYS_ENV=development|paper_trading|live
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- OPENAI_API_KEY=sk-...
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

起動例
- 監視ループを起動（デフォルト 60 秒間隔。MONITOR_POLL_INTERVAL で上書き可）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution を起動（環境に応じて本番 / ペーパートレードが切り替わる）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを直接指定可能（優先度: --db > 環境変数 > デフォルト）

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

停止・制御（フラグファイル）
- data/stop_requested.flag
  - run_monitoring / run_execution の起動ループはこのファイルの存在をチェックして安全に終了します。
  - 手動で停止したい場合はこのファイルを作成してください（ファイル内容は任意）。
- data/kill.flag
  - KillSwitch（監視側）が条件に応じて書き込むことで ExecutionEngine に強制停止要求を出します。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に自動でクリアされるので注意（本番は 0 を推奨）。

ログ
- デフォルトのログ出力先: logs/<app_name>.log（app_name は execution / monitoring 等）
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御
- setup_logging はコンソール（stdout）と日次ローテートファイルを設定します

AI（OpenAI）関連
- news_nlp や regime_detector は OPENAI_API_KEY を必要とします。未設定の場合、例外またはフォールバック動作が発生します（モジュールによる）。
- API 呼び出しはリトライ・バックオフを備え、失敗時はフェイルセーフで継続する設計です。

6. ディレクトリ構成（主要ファイル）
----------------------------------
（src/kabusys 以下の主要ファイル群を抜粋）

- src/kabusys/__init__.py
- src/kabusys/config.py
  - .env 自動読み込み、Settings クラス（環境変数アクセス）
- src/kabusys/config_setup.py
  - .env 対話式ウィザード
- src/kabusys/validate_config.py
  - 起動前チェック CLI

- src/kabusys/run_execution.py
  - ExecutionEngine を起動するスクリプト（KABUSYS_ENV により paper/live を切り替え）
- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔設定）

- src/kabusys/execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - 発注・リスク管理ロジック（本体は該当ディレクトリ参照）

- src/kabusys/monitoring/
  - monitoring_db.py (SQLite スキーマ / 永続化)
  - monitoring_engine.py
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, alert_manager.py（参照）
  - 監視周りの実装

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定・重み付け・株数計算・セクター制限など

- src/kabusys/research/
  - factor_research.py, feature_exploration.py
  - DuckDB を用いたファクター計算・IC 等の分析ユーティリティ

- src/kabusys/ai/
  - news_nlp.py（ニュースセンチメント）
  - regime_detector.py（市場レジーム判定）

- src/kabusys/tools/
  - paper_verification_report.py（ペーパートレード検証レポート）

- src/kabusys/utils/
  - logging_setup.py（統一ロギング設定）
  - process_priority.py（プロセス優先度 / CPU affinity 設定）

その他（プロジェクトルートに想定されるファイル・ディレクトリ）
- .env, .env.local  （環境変数）
- config/*.yaml     （各種 YAML 設定テンプレート）
- data/             （SQLite / DuckDB / フラグ / PID 等）
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag
- logs/             （ログがここに出力されます）

7. 開発メモ / 注意点
-------------------
- .env は機密情報（API トークン等）を含むため絶対に Git にコミットしないでください。
- Settings は起動時に .env を自動読み込みします（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB は分析用のローカル DB として想定されています。SQLite は監視・トレードログ用に使われます。
- OpenAI など外部 API を使う機能は API キーの設定とネットワーク接続が必要です。
- 本番環境（KABUSYS_ENV=live）では kill_flag やログ/通知の設定に特に注意してください（validate_config の警告参照）。
- run_execution は paper_trading のとき専用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離されます。

8. よくあるコマンドまとめ
-----------------------
- .env を作る（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 監視開始
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

9. サポート / 拡張ポイント
--------------------------
- strategy・execution 関連: ブローカープラグインの追加、RiskManager の閾値調整
- portfolio: lot_size を銘柄毎に持たせる拡張
- AI: 使用モデルやプロンプトのチューニング、レスポンス検証ロジックの強化
- monitoring: AlertManager の具体的通知バックエンド（LINE, Slack 等）実装

おわりに
--------
この README はコードベースを元にした概要と運用手順の簡易ガイドです。実運用前に必ず python -m kabusys.validate_config で設定を検証し、テスト環境（paper_trading）で十分に動作確認してください。質問や追加のドキュメント化が必要であれば教えてください。