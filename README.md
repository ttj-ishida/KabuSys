# KabuSys

日本株向け自動売買フレームワーク（ライブラリ + 実行スクリプト群）

このリポジトリは、売買エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）などの機能を持つ自動売買システムのコードベースです。設計は安全性（ペーパートレード分離、Kill Switch、冪等操作）とテストしやすさ（純粋関数・DB分離）を重視しています。

主な特徴や構成、セットアップ／起動手順、簡単な使い方を以下にまとめます。

プロジェクト概要
- 言語: Python
- 永続化:
  - DuckDB: 分析用（デフォルト: data/kabusys.duckdb）
  - SQLite: 監視 / 発注ログ（デフォルト: data/monitoring.db）
  - ペーパートレードは専用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と分離
- 実行スクリプト:
  - 実行エンジン起動: run_execution.py
  - 監視ループ起動: run_monitoring.py
  - .env ウィザード: config_setup.py
  - 設定検証 CLI: validate_config.py
  - Paper Trading 検証レポート: tools/paper_verification_report.py
- AI 機能:
  - ニュースセンチメント（OpenAI を使用）
  - 市場レジーム判定（ETF とマクロニュースの合成）
- ロギング: 共通ユーティリティで stdout + 日次ローテートファイル（logs/<app>.log）

機能一覧
- ExecutionEngine（発注・注文管理・リスク管理・Reconciler 等）
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- Portfolio construction（候補選定、重み計算、ポジションサイズ計算、セクター制限）
- Research（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI（ニュース NLP による銘柄ごとのスコアリング、レジーム判定）
- CLI 支援:
  - .env 対話ウィザード（config_setup）
  - 設定検証（validate_config）
  - Paper Trading の検証レポート生成（tools.paper_verification_report）

セットアップ手順（概要）
1. Python 環境の用意
   - 推奨: Python 3.10+（プロジェクト要件に合わせて調整）
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 手動で必要になる主要パッケージ:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（validate_config の YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. プロジェクトルートの準備
   - data/ および logs/ ディレクトリを作成（多くの処理が自動で作成するが、手動で作ると権限問題回避に便利）
     - mkdir -p data logs

4. 環境変数設定 (.env)
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（config_setup で作られる主要キー:）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用デフォルト: data/paper_trading.db)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意: アラート用)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR)
     - KILL_FLAG_CLEAR_ON_START (0|1)

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. (任意) OpenAI を使う機能を使う場合
   - OPENAI_API_KEY 環境変数を設定（.env に追加してロード）
   - AI 機能はネットワークアクセスと API コストが必要です

使い方（主要スクリプト）
- 監視ループ起動（SystemMonitor）
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（例: 30）
  - 実行:
    - python -m kabusys.run_monitoring
    - または環境変数を指定して:
      - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 注意:
    - run_monitoring は Monitoring 用の sqlite DB（settings.sqlite_path）を使います。KABUSYS_ENV に関わらず監視用 DB は本番パスを使用します。
    - 停止方法: data/stop_requested.flag を作成するとループが検知して終了します。Ctrl+C（KeyboardInterrupt）でも終了します。

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV に応じて動作が変わります:
    - paper_trading: MockBrokerClient を使用し、紙の取引は data/paper_trading.db に記録（本番 DB と分離）
    - development/live: 実際の broker クライアントが利用される（設定に依存）
  - 実行:
    - python -m kabusys.run_execution
    - 例: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止方法:
    - data/stop_requested.flag が作成されるとエンジンは停止します。
    - run_execution は起動時に data/execution.pid を使って PID 管理を行います。

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラーとして扱います

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスはオプション --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

主要環境変数（抜粋）
- KABUSYS_ENV: execution の動作モード（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI を使う場合は必須（AI 機能）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

運用上の注意
- Kill Switch:
  - RiskMonitor 等が設定閾値を越えた場合、KillSwitch が data/kill.flag を書き込み ExecutionEngine 停止を促します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag が自動クリアされますが、本番環境では 0 を推奨します。
- ログ:
  - logs/<app_name>.log に日次ローテートで保存されます。デフォルトのログディレクトリは logs/（環境変数 LOG_DIR で変更可能）。
- 優先度設定:
  - 実行スクリプトは起動時に set_process_priority("high") を呼びプロセス優先度を上げようとします（psutil に依存し、失敗しても警告で続行します）。
- DB マイグレーション:
  - init_monitoring_db は起動時に必要テーブルを作成し、簡単なスキーマ追加（マイグレーション）も行います。既存データは保持されますが、本番運用前にバックアップを推奨します。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env の自動ロードと Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — 優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — 監視 DB の永続化レイヤ
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 発注ログ監視（存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねる
    - kill_switch.py — kill.flag 制御
    - alert_manager.py — 通知管理（LINE 等・存在）
  - execution/  — 発注エンジン関連（BrokerFactory / ExecutionEngine / OrderManager 等）
  - portfolio/  — 候補選定、重み、ポジションサイズ、リスク調整
  - research/   — ファクター計算、特徴量探索
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

開発 / 貢献
- コードはモジュール化されており、ユニットテストを追加しやすい設計です（多くのビジネスロジックは純粋関数で DB 参照を最小化）。
- 変更を行う際は .env.example（存在する場合）を参照し、設定の安全性（特に本番用パスや Kill Switch）に注意してください。

よくある操作例（まとめ）
- .env を作る:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- 監視を起動（デフォルト 60s）:
  - python -m kabusys.run_monitoring
- 実行エンジンをペーパーモードで起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

その他
- README に書かれている手順はローカルテスト／開発用の基本ガイドです。実運用（特に KABUSYS_ENV=live）に移す際は、API キーやパスワード、Kill Switch の運用方針、ログ／バックアップ戦略を十分に検討してください。
- 追加のドキュメント（PortfolioConstruction.md、StrategyModel.md 等）がある場合はそれらも参照してください（リポジトリに同梱されている想定）。

フィードバック／質問があれば実装箇所や使い方、運用上のベストプラクティスについてさらに詳しく説明します。