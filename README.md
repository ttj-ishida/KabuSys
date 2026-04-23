# KabuSys — 日本株自動売買システム (README)

本リポジトリは、日本株向けの自動売買／リサーチ基盤ライブラリ群です。  
監視（Monitoring）、実行（Execution）、ポートフォリオ構築、リサーチ（ファクター計算）、AI（ニュースセンチメント・レジーム判定）などのコンポーネントを含み、ローカル開発・ペーパートレード・本番（live）を想定した設計になっています。

主な設計方針：
- 環境変数（.env）で挙動を切り替え可能
- Paper Trading は本番 DB と完全分離（data/paper_trading.db）
- OpenAI を用いたニュース解析はフェイルセーフ設計（API 失敗時はスキップ／フォールバック）
- DuckDB を分析用途、SQLite を監視・ログ用途に使用

## 機能一覧
- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用して paper_trading DB に記録
  - Process 優先度設定・PID 管理・停止フラグ連携
- 監視プロセス（SystemMonitor / TradeMonitor / RiskMonitor）起動スクリプト（run_monitoring）
  - システムリソース、データ鮮度、ポジション／ドローダウン等の監視
  - kill.flag による ExecutionEngine 強制停止 (Kill Switch)
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き
- 監視ログ永続化層（MonitoringDB） — SQLite スキーマ初期化・読み書きユーティリティ
- リスク監視（RiskMonitor） — ドローダウン・ポジション上限の検出とログ記録
- ポートフォリオ構築ユーティリティ
  - 候補選定（select_candidates）
  - 重み計算（等重・スコア加重）
  - 単位株丸め・資金配分（calc_position_sizes）
  - セクターキャップ適用・レジーム乗数
- リサーチ／ファクター計算（research）
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ
- AI モジュール
  - news_nlp: OpenAI を使ったニュースセンチメント集約 → ai_scores に書込み
  - regime_detector: MA200 とマクロセンチメントを合成して日次レジーム判定
- 開発用 CLI
  - config_setup: 対話式 .env ウィザード（初期作成・更新）
  - validate_config: .env や config/*.yaml の事前検証
  - tools.paper_verification_report: Paper Trading の検証レポート生成

## 必要要件（例）
- Python 3.9+
- 主要依存パッケージ（抜粋）:
  - duckdb
  - openai
  - psutil
  - PyYAML（config YAML の検証を行う場合、任意）
- SQLite（標準ライブラリ sqlite3 を利用）
- ネットワーク接続（OpenAI API を使用する場合）

requirements.txt は本リポジトリに含まれていない想定のため、必要に応じて上記パッケージをインストールしてください。

例:
pip install duckdb openai psutil pyyaml

## セットアップ手順（ローカル開発向け）
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai psutil pyyaml

3. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくはプロジェクトルートに直接 .env を作成
     例（最低限必要な必須項目）:
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO

4. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も FAIL 扱いになります

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data logs

## 使い方（主要コマンド）
- 実行エンジンを起動（本番／開発は KABUSYS_ENV で切替）
  - python -m kabusys.run_execution

  動作補足:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録するため本番 DB と分離されます。
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid に PID を書きます（設定で変更可能）。

- 監視プロセスを起動
  - python -m kabusys.run_monitoring

  動作補足:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path（monitoring DB）と DuckDB を使用します。
  - data/stop_requested.flag を設置すると監視ループは終了します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション --strict（警告を FAIL 扱い）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB ファイルを明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラムから直接呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続、日付、API キー（省略時は OPENAI_API_KEY 環境変数を参照）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI モジュール利用時に必要）
- LOG_LEVEL（INFO 等）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））
- KILL_FLAG_CLEAR_ON_START（本番での自動クリアを制御、0 推奨）

.env は git 管理対象外にしてください（機密情報を含むため）。

## 停止と Kill Switch
- 強制停止（Execution 停止）をトリガーするにはプロジェクトの data/kill.flag に理由を書き込むか、KillSwitch ロジックで自動的に書き込みが行われます。
- run_monitoring と run_execution は data/stop_requested.flag の存在で起動ループを止めます（停止フラグ）。
- run_execution は起動時に KILL_FLAG_CLEAR_ON_START の値に応じて kill.flag を自動クリアする設定がありますが、本番では 0（クリアしない）を推奨します。

## ディレクトリ構成（主要ファイル）
プロジェクトルート下に src/kabusys パッケージが格納されています。以下は主要ファイル・ディレクトリのツリー（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ初期化・DB ラッパ
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       —（注文ログ監視）※実装参照
    - risk_monitor.py        — ドローダウン・ポジション監視
    - monitoring_engine.py   — 各 Monitor を束ねる
    - kill_switch.py         — kill.flag ハンドリング
    - alert_manager.py       —（通知管理）※実装参照
  - execution/
    - execution_engine.py    — ExecutionEngine（発注セッション）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py     — Momentum / Volatility / Value 等
    - feature_exploration.py — IC / forward returns / summary
  - ai/
    - news_nlp.py            — ニュースセンチメント scoring（OpenAI）
    - regime_detector.py     — MA200 + マクロセンチメントでレジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度/CPU affinity 設定
    - __init__.py

（注）上記は主要ファイルのみ抜粋。実装の詳細は各モジュールの docstring を参照してください。

## ロギング
- 共通のロギング初期化ユーティリティ：kabusys.utils.logging_setup.setup_logging(app_name=...)
  - コンソール(stdout) と 日次ローテートログ（logs/<app_name>.log）を設定
  - LOG_LEVEL / LOG_DIR 環境変数で上書き可能

## 注意事項 / 運用上のポイント
- 本番（KABUSYS_ENV=live）での起動前に必ず validate_config を実行し、LINE 通知等の設定を確認してください。
- OpenAI API を用いる機能は API キー管理／コストに注意してください。API 失敗時はフェイルセーフでフォールバックする設計ですが、頻繁な失敗は機能低下につながります。
- Paper Trading 用 DB は本番 DB と完全に分離しているため、ペーパートレードでの誤発注が本番に影響を与えることはありません（想定通りの環境変数設定が前提）。
- PID / flag ファイルは data/ 配下に置かれます。運用側のプロセス監視やデプロイ方法に合わせて配置や権限を調整してください。

---

この README はコードベースに含まれるモジュールの概要と運用手順をまとめたものです。詳細な API 仕様や設計書（PortfolioConstruction.md、StrategyModel.md 等）が別途ある場合はそちらも併せて参照してください。質問や追加で記載してほしい項目があれば教えてください。