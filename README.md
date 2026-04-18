# KabuSys

日本株自動売買システムのモジュール群（ライブラリ + 起動スクリプト群）。  
このリポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ファクター/リサーチ、ポートフォリオ構築、AI を使ったニュース解析など、運用に必要な主要コンポーネントを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動スクリプト・ツール）
- 環境変数一覧（主要）
- ディレクトリ構成
- 運用上の注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定した構成で、次の責務を持つコンポーネントを含みます。

- Execution: ブローカークライアントと発注エンジン（本番 / ペーパートレード切替）。
- Monitoring: システム状態・発注履歴・リスク監視・Kill Switch（停止フラグ）などのポーリング監視。
- Portfolio: 候補選定、ウェイト算出、ポジションサイジング、セクター制限等の純関数群。
- Research: DuckDB を使ったファクター計算・特徴量探索（Momentum / Value / Volatility 等）。
- AI: OpenAI を用いたニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）。
- Tools: ペーパートレード検証レポート等のユーティリティスクリプト。
- Utils: ログ設定、プロセス優先度設定、設定読み込みユーティリティなど。
- 設定支援: 対話式 `.env` 作成ウィザードと設定検証 CLI。

設計方針の特徴:
- DuckDB/SQLite を用いたローカル DB 管理（分析用 / 監視用 / paper_trading 用に分離）。
- 本番環境とペーパートレードを分離する仕組み（KABUSYS_ENV）。
- OpenAI 呼び出しは失敗時にフェイルセーフで継続する実装（可能な限りサービス停止を避ける）。
- ログは統一されたロギング設定（流し込みと日次ローテート）で管理。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper trading 切替（KABUSYS_ENV=paper_trading → MockBrokerClient、専用 SQLite）
  - PID ファイル生成・停止フラグ検知
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor のポーリング
  - Kill Switch（閾値到達時に data/kill.flag を書き込み Engine を停止）
  - monitoring DB（SQLite）による永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - run_monitoring.py によるデーモン的ループ起動（ポーリング間隔は環境変数で調整可）
- Portfolio
  - 候補選定（スコアソート）
  - 等配分 / スコア加重配分
  - ポジションサイズ計算（risk-based / equal / score）
  - セクターキャップ適用、レジーム乗数
- Research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ
- AI
  - ニュースのセンチメントスコア化（OpenAI）
  - マクロニュース + ETF MA200 による市場レジーム判定
- ツール
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report.py）
  - 対話式 .env ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- Utils
  - ロギングセットアップ（TimedRotatingFileHandler）
  - プロセス優先度 / CPU affinity 設定（psutil）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型ヒントに | 演算子等を使用）。
- 推奨環境は仮想環境（venv 等）を使用。

1. リポジトリをクローン、プロジェクトルートへ移動
   - 仮想環境を作り、アクティベートする。

2. 依存パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合はそれを使用してください。）

3. 初期設定ファイル（.env）作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは手動で `.env` を作成（.env.example を参考にすること）。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）

4. 設定検証（必須項目が揃っているか確認）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / ログの親ディレクトリは自動作成されるケースが多いですが、権限などを事前に確認してください。
   - デフォルト:
     - SQLite（監視）: data/monitoring.db
     - DuckDB（分析）: data/kabusys.duckdb
     - Paper trading DB: data/paper_trading.db
     - ログ: logs/

---

## 使い方

以下は主要な起動スクリプト / ツールの使い方例です。

- ExecutionEngine を起動（デーモン的に実行）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBrokerClient（実取引しない）
    - 実行時に data/execution.pid を作成（pid ファイル）
    - data/stop_requested.flag があれば起動を行わず終了
    - 起動直後にプロセス優先度を "high" に設定しようとします（psutil の権限次第で失敗することがあります）

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 動作:
    - Settings の sqlite_path（デフォルト: data/monitoring.db）に接続し、監視テーブルを初期化
    - duckdb に接続
    - SystemMonitor.check_once() を繰り返し実行
    - 繰り返し間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）で上書き可能
    - data/stop_requested.flag を検知したらループを終了する

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があれば exit(1) します

- .env 作成ウィザード
  - python -m kabusys.config_setup

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

- AI / リサーチの呼び出し（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡し、OpenAI API を使って ai_scores テーブルへ書き込む
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- テスト用に MonitoringEngine を単発実行
  - MonitoringEngine.run_once() を使えば一回だけ監視処理を回せます（ユニットテスト向け）。

停止シグナル / フラグ
- data/stop_requested.flag: run_* スクリプトが監視している "停止要求" ファイル（存在するとループが終了する）。
- data/kill.flag: KillSwitch によって書かれ、ExecutionEngine に停止を促すために使用されるファイル（実行中の Engine は起動時や監視ループでこのフラグを参照します）。

ログ
- ログは logs/ ディレクトリに app_name 単位で日次ローテートファイルが出力されます（例: logs/execution.log, logs/monitoring.log）。
- コンソール出力は stdout に流れます。

---

## 主な環境変数（抜粋）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - デフォルト: development
  - paper_trading のときは Execution が paper DB を使う

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL
  - デフォルト: http://localhost:18080/kabusapi
- LOG_LEVEL
  - DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH
  - デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH
  - デフォルト: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
- OPENAI_API_KEY
  - AI 機能を利用する場合に必須
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START
  - "1" にすると起動時に kill.flag を自動でクリア（本番では 0 推奨）

詳細は config_setup.py と config.py の docstring を参照してください。

---

## ディレクトリ構成

リポジトリの主要ファイル / モジュール構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py     — マクロ + MA200 によるレジーム判定
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (存在)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在)
  - execution/                — Execution 関連コンポーネント（broker_factory 等）
  - utils/
    - logging_setup.py
    - process_priority.py

（上記はリポジトリ内の主要ファイルを抜粋したツリーです。実ファイル数はさらに多く存在します。）

---

## 運用上の注意点 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では .env の設定を厳密に確認してください。validate_config の警告を必ず確認すること。
- .env は決して Git 等で公開リポジトリにコミットしないでください（config_setup も README にその旨を追記しています）。
- OpenAI API 等外部サービスを使う機能は、APIキー・コスト管理・レート制限に注意してください。AI 呼び出しはリトライ/バックオフ実装がありますが、運用ポリシーを定めてください。
- PID ファイル / flag ファイルは data/ 以下に作られます。起動権限やプロセス監視ツールとの連携ルールを事前に定めてください。
- ログディレクトリ (logs/) のローテーション・ディスク使用量に注意してください（デフォルトは 30 日分保持）。
- psutil を用いたプロセス優先度変更は権限が必要な場合があります。権限エラーは警告で済むよう実装されていますが、期待どおり設定されない可能性があります。

---

README はここまでです。詳細な API 仕様や設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）がプロジェクトに含まれている場合は、合わせて参照してください。必要であれば、起動シーケンス図、環境変数の完全一覧、運用手順（デプロイ・バックアップ・リストア）などの追加ドキュメントを作成します。どの部分を優先して拡充しましょうか？