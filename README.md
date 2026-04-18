# KabuSys

日本株向けの自動売買システム（ライブラリ／実行スクリプト群）のREADMEです。  
このリポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AIベースのニュース評価など複数コンポーネントで構成されています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数／設定
- ファイル・ディレクトリ構成（概観）
- 運用上の注意点

---

プロジェクト概要
- KabuSys は日本株自動売買を想定したモジュール群と起動スクリプトを提供します。
- 構成要素例：
  - ExecutionEngine（発注・注文管理・リスク管理）
  - Monitoring（システム稼働・注文状況・リスク監視、Kill Switch）
  - Portfolio（候補選定、配分、ポジションサイズ計算、セクター制約）
  - Research（ファクター計算、将来リターン、IC 等）
  - AI（ニュースのセンチメント評価、レジーム判定）
  - ユーティリティ（設定読み込み、ログ設定、プロセス優先度設定 等）
- データ永続化：
  - DuckDB（分析用、デフォルト: data/kabusys.duckdb）
  - SQLite（監視/発注履歴、デフォルト: data/monitoring.db）
  - Paper trading 用は data/paper_trading.db（KABUSYS_ENV=paper_trading 時に分離）

---

機能一覧
- 設定管理
  - .env/.env.local の自動読み込み（必要に応じて無効化可能）
  - config_setup.py による対話式 .env 作成ウィザード
  - validate_config.py による起動前チェック
- 実行関連
  - run_execution.py：ExecutionEngine 起動（本番 / paper_trading 切替）
  - run_monitoring.py：SystemMonitor のポーリングループ起動（デフォルト 60 秒）
- 監視／Kill Switch
  - system_status / trade_logs / risk_logs / positions / dashboard を SQLite に永続化
  - リスク監視（ドローダウン、ポジション上限等） → 必要なら data/kill.flag に書き込み
  - 停止フラグ（data/stop_requested.flag）で run_* スクリプトを停止
- ポートフォリオ
  - 候補選定、等重・スコア重み、セクターキャップ、レジーム乗数、ポジションサイズ計算（lot 単位丸め、利用可能現金でスケール）
- リサーチ
  - モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB を使用）
  - 将来リターンや IC（Spearman）計算
- AI
  - ニュースを OpenAI（gpt-4o-mini 等）でセンチメント化し ai_scores に格納
  - マクロニュースと ETF MA 乖離を用いた市場レジーム判定
- ツール
  - paper_verification_report：Paper Trading の検証レポートを生成（稼働率、成功率、レイテンシ等）

---

セットアップ手順（概要）
1. リポジトリをクローン
   - git clone <repo>
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - requirements.txt がある場合はそれを使うのが望ましいですが、無い場合は最低限以下をインストールしてください:
     - duckdb, psutil, openai, (PyYAML: validate_config の YAML 検証に必要)
   - 例:
     - pip install duckdb psutil openai pyyaml
4. .env 作成
   - 推奨: 対話式ウィザードを使用
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
5. 設定検証（必須項目の確認）
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合は --strict を付ける
6. データディレクトリの準備
   - data/ (デフォルトでログ・DB・フラグファイルがここに配置されます)
   - 実行前に必要なディレクトリを作成してください（logging で自動作成される場合もあります）

---

主要な使い方（コマンド例）
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動（フォアグラウンド）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると発注は MockBrokerClient に切替わり data/paper_trading.db を使用
- 監視プロセス起動（ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL（秒）を設定
    - 例: export MONITOR_POLL_INTERVAL=30
  - run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視データを書き込みます
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH
- AI 関連（プログラム API）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key=...)
  - 市場レジームスコア:
    - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)
    - （注意: ai/__init__.py は score_news のみをエクスポートしています。regime_detector は直接 import して利用）

停止・Kill 操作
- run_execution/run_monitoring はプロジェクトの data/stop_requested.flag の存在をチェックして安全停止します。
  - 停止要求を出すにはプロセスから stop フラグファイルを作成する、またはシグナルで停止してください。
- Kill Switch（自動停止）
  - RiskMonitor が条件を満たすと KillSwitch が data/kill.flag を書き込み、ExecutionEngine を停止指示（運用上はこのフラグを監視して停止させます）。
  - 本番で自動クリアさせたくない場合は KILL_FLAG_CLEAR_ON_START を 0（デフォルト）にしてください。

---

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（default: development）
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB、default: data/paper_trading.db）
- LOG_LEVEL（default: INFO）
- LOG_DIR（ログを出力するディレクトリ、default: logs/）
- OPENAI_API_KEY（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒、default: 60）
- PAPER_FILL_MODE（paper_trading の MockBroker の fill モード: instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START（0/1。本番で 1 は危険）

注意: config_setup.py が提示する項目や validate_config.py の _REQUIRED_ENV_VARS を参考に設定してください。

---

監視用 SQLite スキーマ（monitoring_db）
- system_status: CPU/メモリ/ディスク/プロセス稼働等の履歴
- trade_logs: 発注イベントログ（Created, Sent, Filled など）、latency_ms カラムあり
- positions: 現在ポジション（code を主キー）
- risk_logs: リスク関連イベント（ドローダウンアラート等）
- dashboard: ダッシュボード集計（id=1 の単一行）

---

ディレクトリ構成（src/kabusys の主要ファイル／モジュール）
（ハイレベルの役割を併記）

- kabusys/
  - __init__.py — パッケージ情報（__version__ 等）
  - config.py — .env / 環境変数の読み込み・Settings クラス
  - config_setup.py — .env 作成ウィザード（CLI）
  - validate_config.py — 起動前の設定検証（CLI）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート（CLI）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ローテートファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（テーブル作成・CRUD ヘルパー）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留／約定異常などの監視（該当ファイルはリポジトリに含まれます）
    - risk_monitor.py — ドローダウン・ポジション上限などのチェック
    - kill_switch.py — Kill Switch（flag ファイル）
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py — 通知（LINE など）を行うマネージャ（該当ファイルがあれば）
  - execution/
    - execution_engine.py — 実際の実行ロジック（Engine, run_session 等）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注・リスク・ブローカー関連
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 候補選定・配分・リスク調整
  - research/
    - factor_research.py, feature_exploration.py — ファクター計算、IC、統計等
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — マクロ + ETF MA でレジーム判定
  - data/ (実行時に生成される想定)
    - *.db, kill.flag, stop_requested.flag, execution.pid など

（注）上記はコードベースに含まれる主要モジュールの一覧です。実際のファイル一覧はリポジトリの tree を参照してください。

---

運用上の注意点 / ベストプラクティス
- 本番（KABUSYS_ENV=live）では .env を慎重に管理し、絶対にリポジトリにコミットしないでください。
- validate_config を起動前に必ず実行して必須項目とパスの整合性を確認してください。
- run_monitoring は監視用 DB に書き込むため、monitoring の SQLite は本番用に分離して運用してください（run_monitoring は環境に関わらず sqlite_path を使用します）。
- run_execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path（data/paper_trading.db）に分離して書き込みます。実際の発注は MockBrokerClient を使用します（本番 DB と完全分離）。
- kill.flag / stop_requested.flag の扱いに注意してください。特に本番で KILL_FLAG_CLEAR_ON_START=1 を設定するのは危険です（自動クリアで Kill Switch を無効化するため）。
- ログは logs/<app_name>.log に日次ローテートで保存されます（デフォルト 30 日保持）。ログディレクトリに書き込み権限が必要です。
- OpenAI API を叩く機能（news_nlp, regime_detector）は API レート制限やコストの考慮が必要です。API キーは安全に管理してください。

---

サンプル .env（最低限）
（対話ウィザードの出力を参考にした抜粋）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=sk-...

---

追加情報 / 開発者向け
- 各モジュール（portfolio, research, ai）は関数ベースで設計され、ユニットテストが組みやすい純粋関数部分と、DB/外部 API にアクセスする部分が分離されています。
- DuckDB を用いた分析処理は SQL と Python 混成で記述されており、大量の市場データ分析に向きます。
- ログ設定は中央の setup_logging で統一しているため、全起動スクリプトで同じ形式のログが得られます。

---

不明点・補足
- requirements.txt やデプロイ用の systemd ユニット等はプロジェクトに含まれている場合はそちらを参照してください。
- この README はコードベースの説明に基づく要約です。実装の詳細や運用ルールは各モジュールのドキュメント／コメントを参照してください。

必要でしたら、よく使う systemd サービスユニットの例や .env のより詳細なテンプレート、デバッグ手順（ログの場所・SQL の確認方法）などを追記します。どの情報を優先して追加しますか？