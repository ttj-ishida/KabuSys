KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株自動売買のためのモジュール群です。  
戦略・ポートフォリオ構築、注文執行エンジン、監視・アラート、リサーチ（DuckDB ベースのファクター計算）、およびニュース NLP / レジーム判定（OpenAI API を利用）などを含みます。  
設計方針としては「テスト可能で安全なデフォルト」「ルックアヘッドバイアス防止」「本番・ペーパートレードの明確な分離」を重視しています。

主な機能
--------
- 環境設定ウィザード（.env の対話式生成）
- 設定検証 CLI（環境変数 / config/*.yaml の簡易チェック）
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて本番/ペーパートレードを分離
  - ブローカークライアント（実ブローカー or Mock）を差し替え可能
  - リスク管理・注文管理・照合（reconciler）を内包
- 監視（Monitoring）サブシステム
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - 監視用 SQLite（monitoring.db）へのログ永続化
  - run_monitoring.py によるポーリング起動（MONITOR_POLL_INTERVAL で間隔設定）
- ポートフォリオ構築ライブラリ
  - 候補選定、等金額／スコア加重、セクター制約、ポジションサイズ計算（単元丸め、aggregate cap）
- リサーチ機能（DuckDB 接続）
  - モメンタム / ボラティリティ / バリュー 等ファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリ
- AI 支援機能（OpenAI）
  - ニュースのセンチメントスコアリング（ai/news_nlp.py）
  - 市場レジーム判定（ai/regime_detector.py）
  - OpenAI API のエラーハンドリング・リトライ実装付き
- ユーティリティ
  - ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定（psutil ベース）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

必須要件
--------
- Python 3.10 以上（PEP 604 の型記法などを使用）
- 推奨ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai（AI 機能を利用する場合）
  - PyYAML（config YAML の検証を行う場合）
- SQLite は標準ライブラリで利用可能

セットアップ手順
----------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （実運用では requirements.txt を用意して pip install -r requirements.txt を推奨）

3. プロジェクトルートに移動（パッケージは src/ 配下を想定）
   - ルートには .env, data/, logs/ 等が配置されます

4. 環境変数設定
   - 対話式ウィザードを使って .env を作成:
     - python -m kabusys.config_setup
   - または .env を手動で作成（最低限必要な環境変数）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - (任意) OPENAI_API_KEY=...
   - 自動ロード: config モジュールはプロジェクトルートの .env/.env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付与すると警告も失敗扱いになります

使い方
------
- Execution エンジン起動（本番/ペーパートレード共通エントリ）
  - python -m kabusys.run_execution
  - 動作環境は KABUSYS_ENV 環境変数で切替（paper_trading の場合は MockBroker が使われ、別 SQLite（data/paper_trading.db）に記録）
  - 実行中の停止: data/stop_requested.flag を作成するとエンジンは停止を受け付けます

- Monitoring 起動（監視ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更可能:
    - MONITOR_POLL_INTERVAL=30  # 秒
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します
  - 停止フラグ: project_root/data/stop_requested.flag を検知して終了します

- 環境設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションあり

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定できます（デフォルト data/paper_trading.db）

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY または関数引数で指定）
  - 例: kabusys.ai.score_news(conn, target_date, api_key=...)、kabusys.ai.regime_detector.score_regime(...)

ログ / モニタリング
------------------
- ログ設定は kabusys.utils.logging_setup.setup_logging を使用し、stdout + 日次ローテーション（logs/<app_name>.log）に出力します。
- LOG_LEVEL / LOG_DIR 環境変数で調整可能。
- 監視ログは SQLite（デフォルト data/monitoring.db）に永続化されます（system_status, trade_logs, positions, risk_logs, dashboard など）。

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト data/paper_trading.db）
- DUCKDB_PATH（DuckDB ファイル、デフォルト data/kabusys.duckdb）
- OPENAI_API_KEY（AI 機能利用時に必須）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒。デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1（.env 自動ロード無効化）

ファイル / ディレクトリ構成
-------------------------
（主要なものを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の自動読込・設定クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / cpu affinity 設定
  - execution/               — 実際の注文実行関連（engine, order_manager, broker_factory 等）
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite 永続化ロジック
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

運用上の注意 / ベストプラクティス
--------------------------------
- 本番（KABUSYS_ENV=live）では特に LINE の通知設定や Kill Switch の挙動を確認してください（validate_config の live ガードを参照）。
- .env は絶対にソース管理にコミットしないでください（config_setup.py のヘッダにも警告あり）。
- psutil によるプロセス優先度設定や CPU affinity は OS 権限に依存します。アクセス拒否時は警告が出てスキップされます。
- OpenAI 呼び出しはネットワークエラー・429・5xx を考慮した再試行実装がありますが、API コストとレート制限には注意してください。
- DuckDB の接続は読み込み中心のリサーチ用途を想定しています。トランザクションが必要な書き込みは SQLite を利用します（monitoring DB 等）。

開発 / テスト
--------------
- 各モニタ／機能は外部副作用を抑えた設計（引数で接続/クライアントを注入）になっています。ユニットテストではモック（例: unittest.mock）に差し替えてテストしてください。
- MonitoringEngine には run_once() があり、単回実行テストを行いやすくしています。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現行: 0.1.0）。

お問い合わせ / 変更履歴
---------------------
- ソース内の docstring / モジュールコメントに設計意図や注意が記載されています。実装を変更する場合は docstring を更新してください。

以上が README の概要です。必要であれば、サンプル .env テンプレートや systemd / supervisor 用の起動スクリプト例、requirements.txt の案も追記します。どれを追加しますか？