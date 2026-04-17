# KabuSys

日本株自動売買システムのサンプル実装（モジュール群・ユーティリティ群）。  
この README はコードベース（src/kabusys 以下）を説明するための概要ドキュメントです。

注意: このリポジトリは実運用向けのテンプレート/実装例を含みます。実際に運用する際は API キー/パスワードの管理・リスク管理・テストを十分に行ってください。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要コマンド例）
- 環境変数（主要なもの）
- ディレクトリ構成（主要ファイルの役割）
- 運用に関する注意点

---

プロジェクト概要
- KabuSys は日本株の自動売買を想定したコンポーネント群です。
- 発注エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算・特徴量解析）、AI を使ったニュース NLP、ペーパートレード用ツールなどを含みます。
- DB に DuckDB（分析用）と SQLite（監視・発注ログ等）を利用します。
- 本番（live）・ペーパー（paper_trading）・開発（development）環境を切り替える仕組みがあり、ペーパートレードは本番 DB と分離して動作します。

主な機能一覧
- ExecutionEngine 起動用スクリプト（run_execution.py）
  - 環境に応じて MockBroker（paper_trading）または実ブローカーを使用
  - Order 管理、RiskManager、Reconciler などの組み立てを行いバックグラウンドスレッドでセッションを実行
- Monitoring（run_monitoring.py / monitoring/*）
  - SystemMonitor: プロセス生存・CPU/メモリ/ディスク・データ鮮度を監視
  - TradeMonitor: 滞留注文・約定異常価格を検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、kill switch のトリガー
  - MonitoringDB: 監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）用 SQLite 層
  - MonitoringEngine: 各モニタを束ねるポーリングループ
- ポートフォリオ構成（portfolio/*）
  - 銘柄選定、重み算出（等重／スコア重み）、ポジションサイズ計算、セクターキャップ、レジーム乗数など
- リサーチ（research/*）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - DuckDB を直接参照して計算
- AI モジュール（ai/*）
  - ニュース NLP（news_nlp.py）: OpenAI を使って銘柄ごとのセンチメントを算出し ai_scores に格納
  - レジーム判定（regime_detector.py）: ETF の MA とマクロニュースの LLM 結果を合成して market_regime に書き込み
- ツール（tools/*）
  - Paper Trading 検証レポート生成（paper_verification_report.py）
- 設定ユーティリティ
  - config_setup.py : .env の対話式ウィザード
  - validate_config.py : 環境変数・設定ファイルの検証 CLI

セットアップ手順（開発環境向けの推奨手順）
1. Python バージョン
   - Python 3.10 以上を推奨（typing の | 記法を使用）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) または .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - 必須依存（コード参照から推定）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定 YAML 検証時に必要、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がない場合は上記を手動インストールしてください）
4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参考に .env を作成して必要な環境変数を設定
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります
6. データディレクトリ
   - デフォルトで data/ 以下に DB 等が作成されます。必要に応じて作成またはパスを変更してください。

主要な環境変数（概要）
- 必須:
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 動作モード:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- データベース:
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 時の専用 SQLite（デフォルト: data/paper_trading.db）
- AI:
  - OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- ログ/運用:
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - PID_FILE_PATH: execution.pid の場所（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag の場所（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- Monitoring:
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- Paper trading specific:
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

使い方（主要コマンド例）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- モニタリング起動（ローカルで監視ループを動かす）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - run_monitoring は常時ループします。停止は data/stop_requested.flag を作成するか Ctrl+C。
- ExecutionEngine 起動（注文エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker が使われ、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 実行中は pid ファイル（data/execution.pid）を書きます。停止は data/stop_requested.flag を作成するか kill でプロセス停止。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - フィルタ期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

重要なファイル / 運用フラグ
- data/kill.flag: KillSwitch が書き込むと ExecutionEngine の停止シグナルになる（手動で書き込むことも可能）。
- data/stop_requested.flag: run_* スクリプトがこのファイルを検出するとグレースフルに終了する。
- data/execution.pid: ExecutionEngine 起動時に PID が書き込まれる（SystemMonitor が存在確認に使用）。

ディレクトリ構成（src/kabusys の主要ファイルと役割）
- __init__.py
- config.py: 環境変数・.env 自動読み込み・Settings クラス
- config_setup.py: .env 対話式ウィザード
- validate_config.py: 起動前の設定検証 CLI
- run_execution.py: ExecutionEngine 起動スクリプト（環境に応じて MockBroker を利用）
- run_monitoring.py: SystemMonitor をポーリングするスクリプト
- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成
- ai/
  - news_nlp.py: ニュースを OpenAI でスコアリングし ai_scores へ投入
  - regime_detector.py: マクロ＋MA による市場レジーム判定
- monitoring/
  - monitoring_db.py: 監視用 SQLite テーブル作成・CRUD ラッパー
  - system_monitor.py: プロセス・資源・データ鮮度監視
  - trade_monitor.py: 滞留注文・約定異常検出
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag の制御ロジック
  - monitoring_engine.py: 各モニタを束ねるループ
  - alert_manager.py: （アラート送信ロジック、未表示部分あり）
- execution/ (発注関連) — 主要クラスは run_execution で組み立てて使用
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, order_record.py など（発注ロジックを含む）
- portfolio/
  - portfolio_builder.py: 候補選定 / 重み計算
  - position_sizing.py: 発注株数計算（単元丸め・リスク制限）
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- research/
  - factor_research.py: ファクター計算（momentum/value/volatility）
  - feature_exploration.py: 将来リターン・IC 計算・統計サマリー
- utils/
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ
  - __init__.py

運用に関する注意点
- 本システムは実際の売買を行う構成を含みます。live 環境で運用する前に十分なテストを行ってください。
- 機密情報（API キー・パスワード）は .env に保存しますが、絶対に Git にコミットしないでください。
- KABUSYS_ENV=paper_trading は本番 DB と分離され、MockBroker によるシミュレーションを行います。ペーパートレード検証は tools/paper_verification_report.py を利用してください。
- OpenAI を利用する機能（news_nlp / regime_detector）は API 呼び出しに料金・レート制限が発生します。API キーと使用量に注意してください。
- Monitoring 系は監視ログを SQLite に永続化します。長期間運用する場合はログ管理（ローテーション / サイズ管理）を検討してください。
- set_process_priority 等の API は環境依存（権限・OS）で失敗する可能性があるため、エラーハンドリングが実装されています。

最小の .env 例
（本番運用では適切に置き換えてください）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

さらに詳しいドキュメント（設計・数理モデル・運用手順）はプロジェクト内のドキュメント（例: PortfolioConstruction.md, StrategyModel.md 等）やコード内の docstring を参照してください。

何か特定部分（例えば ExecutionEngine の使い方、AI モジュールのテスト方法、DB スキーマの詳細など）について README を拡張したい場合は、どのセクションを深掘りするか指示してください。