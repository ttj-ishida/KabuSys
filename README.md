# KabuSys

日本株向け自動売買システム（ライブラリ & 実行スクリプト群）

このリポジトリは、データパイプライン、リサーチ（ファクター計算）、ポートフォリオ構築、注文実行エンジン、監視・アラート、AI を用いたニュース解析などを含む自動売買プラットフォームの一部実装です。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要コマンド）
- 重要な環境変数
- ディレクトリ構成
- 運用メモ / トラブルシュート

---

プロジェクト概要
- ディスク: DuckDB（分析用） / SQLite（監視・発注ログ）
- 実行: ExecutionEngine（発注）・MonitoringEngine（監視）を個別に起動
- 環境切替: KABUSYS_ENV（development / paper_trading / live）
  - paper_trading: MockBroker を使い paper_trading.db に記録して本番 DB と分離
- AI: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント分析 & レジーム判定
- 設定: .env を利用。対話式ウィザードと検証ツールを提供

主な機能
- 設定管理
  - .env 自動ロード（プロジェクトルート検出）
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証ツール（kabusys.validate_config）
- 実行エンジン
  - 発注フロー組み立て（BrokerFactory / OrderManager / RiskManager 等）
  - paper_trading モードで MockBroker を使用し DB を分離
  - PID 管理 / stop フラグ検知で安全停止
- 監視・キルスイッチ
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログは SQLite（monitoring.db）へ永続化
  - KillSwitch により閾値超過時に data/kill.flag を書き込み ExecutionEngine に停止シグナル送信
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、リスクベース配分、単元丸め、セクター上限、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由で prices_daily 等を参照）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI 支援
  - ニュースを LLM で解析し ai_scores に書き込む（部分失敗耐性・バッチ処理・リトライ）
  - ETF とマクロニュースから市場レジーム判定を行い market_regime に永続化
- ツール
  - ペーパートレード検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順（開発向け）
1. 要求環境
   - Python 3.10+
   - 推奨ライブラリ（最低限）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - pyyaml (validate_config の YAML 検証を行う場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動: プロジェクトルートに .env を作成（.env.example を参考）
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いにできます

5. ディレクトリ作成
   - data/ や logs/ は自動で作成されることが多いですが、権限の問題がある場合は手動作成してください

使い方（主要コマンド）
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine の起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は paper_trading DB（PAPER_TRADING_SQLITE_PATH）を使用
    - 起動時に data/stop_requested.flag が既にある場合は起動せず終了
    - 停止は data/stop_requested.flag を作成するか、KillSwitch が data/kill.flag を書き込むことでトリガーされます
- MonitoringEngine の起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に本番 sqlite_path を参照（環境に依存せず）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

重要な環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API）
- KABU_API_PASSWORD: 必須（kabuステーション API）
- OPENAI_API_KEY: AI 機能を使う場合に必須
- PAPER_FILL_MODE: paper_trading 時のモック埋め方（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch 用フラグ（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

簡単な .env 例
（秘密情報は実際にはマスクして保存）
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト（PID / stop フラグ管理）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定（stdout + 日次ローテート）
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 + DB アクセス層
    - system_monitor.py      — システム/データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション数監視
    - trade_monitor.py       — （注文監視ロジック：省略ファイル参照）
    - monitoring_engine.py   — 監視の束ね処理・アラート通知連携
    - kill_switch.py         — KillSwitch 実装（data/kill.flag 書込）
    - alert_manager.py       — （アラート送信ロジック：省略ファイル参照）
  - execution/
    - execution_engine.py    — 実行エンジン本体（セッション管理）
    - broker_factory.py      — Broker クライアント生成（Mock/実ブローカー選択）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・単元丸め・投下上限調整
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — ETF MA + マクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

運用メモ / トラブルシュート
- ログ
  - デフォルトは logs/<app_name>.log（日次ローテート、30日保持）。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- プロセス優先度設定
  - 起動スクリプトは set_process_priority("high") を呼びますが、権限不足や非対応 OS の場合は警告が出て無視されます（正常動作）。
- 停止フラグ
  - run_execution.py / run_monitoring.py は data/stop_requested.flag を監視して安全に終了します。KillSwitch は data/kill.flag を書き込んで ExecutionEngine に停止を促します（kill.flag は ExecutionEngine 側で設定次第クリアする設計）。
- AI（OpenAI）関連
  - OPENAI_API_KEY が未設定だと AI 機能は例外を投げます。AI 呼び出しは冪等性やリトライ・フォールバック設計が組み込まれていますが、API クォータやネットワーク障害を考慮してください。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等で、必要に応じてカラム追加（例: peak_value, latency_ms）を行います。
- Paper Trading
  - paper_trading モードでは発注は MockBroker を通して data/paper_trading.db へ記録され、本番 DB と分離されます。PAPER_FILL_MODE で約定挙動を制御できます。

最後に
- これはシステムの一部実装です。実運用では broker 実装、アラート送信（LINE 等）、堅牢なエラーハンドリング、監査ログ、CI/CD、監視体制の整備が必要です。
- まずは .env を作成 → python -m kabusys.validate_config で検証 → python -m kabusys.run_monitoring / python -m kabusys.run_execution を試してください。