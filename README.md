# KabuSys

日本株向けの自動売買システム（リファクタ済みモジュール群）。  
このリポジトリは、発注エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）や AI を使ったニュース解析などのコンポーネントで構成されています。

## プロジェクト概要
- 発注（ExecutionEngine）と監視（MonitoringEngine）を分離して実装。
- paper trading（ペーパートレード）モードをサポートし、本番 DB と分離して動作可能。
- DuckDB を分析用 DB、SQLite を監視 / 発注ログ用 DB として利用。
- ニュースを LLM（OpenAI）でスコアリングして市場レジーム判定やセンチメントを生成。
- ポートフォリオ構築、リスク調整、ポジションサイジング等は純粋関数として実装（単体テストしやすい）。

## 主な機能一覧
- Execution
  - ExecutionEngine の起動・停止（run_execution）
  - Broker クライアントファクトリ（paper_trading 時は MockBroker）
  - Order 管理、リスク管理、Reconciler 等
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、プロセス死活）
  - TradeMonitor（滞留注文、約定異常）
  - RiskMonitor（ドローダウン、ポジション上限）
  - KillSwitch（条件に応じた停止フラグ書込）
  - MonitoringEngine（複数モニタの統合ループ）
- Research / Portfolio
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC 計算、統計サマリ
  - 候補選定、重み計算、ポジションサイジング、セクター上限適用
- AI
  - ニュース NLP（OpenAI を使った銘柄センチメント scroing）
  - 市場レジーム判定（MA200 とマクロニュースの LLM 集約）
- ツール
  - Paper Trading 検証レポート生成（paper_verification_report）

## 必要条件 / 依存
- Python 3.10+
- 必須 Python パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- オプション
  - PyYAML（`python -m kabusys.validate_config` が config/*.yaml の検証を行う場合）
- OS: Windows / Linux / macOS（process priority や CPU affinity は権限や OS により挙動が変わります）

（依存は pyproject.toml / requirements.txt があればそちらを参照してください）

## セットアップ手順（例）
1. リポジトリをクローンして venv を作成
   ```bash
   git clone <このリポジトリ>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install duckdb psutil openai PyYAML
   ```
2. 初期環境変数 (.env) 作成（ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   - 表示に従って各種キーやパスを入力します。
   - .env は Git に絶対コミットしないでください。
3. 設定検証
   ```bash
   python -m kabusys.validate_config        # 警告は出力するが exit 0
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱いで exit 1
   ```
4. 必要なデータディレクトリ（例: data）を作成（多数の処理で自動作成されますが、手動で用意しておくと安心）
   ```bash
   mkdir -p data
   ```

## 使い方 / 実行例

- ExecutionEngine を起動（デフォルト動作）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV により挙動が切り替わります:
    - development: 実発注なし（主に開発用）
    - paper_trading: MockBroker を使用し、デフォルトで data/paper_trading.db に記録（本番 DB と分離）
    - live: 本番（実際に発注）
  - 実行中は data/execution.pid（デフォルト）を作成します。
  - 停止は data/stop_requested.flag（ローカルの停止フラグ）を作成するか、標準的な KeyboardInterrupt で可能。

- Monitoring を起動（ポーリングループ）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Monitoring DB（デフォルト data/monitoring.db）に記録されます。
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV にかかわらず監視用 DB は本番パスを参照します）。

- Paper Trading 検証レポートの生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  ```
  - DB パスはデフォルト data/paper_trading.db。`--db` または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

## 主要な環境変数
- 必須（最低限セットする）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 主な任意 / デフォルト
  - KABUSYS_ENV: development | paper_trading | live (default: development)
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO（DEBUG/WARNING/ERROR など）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート通知（任意）
  - OPENAI_API_KEY: AI 機能を利用する場合は必須
  - MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）

.env は自動ロードされます（.env.local があれば上書き）。OS 環境変数は .env の上位優先になります。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

## 停止・Kill Switch の仕組み
- 停止フラグ: data/stop_requested.flag（run_execution/run_monitoring が参照）
  - run_execution/run_monitoring はこのファイルの存在を検知すると安全にループを抜けます。
- Kill Switch: data/kill.flag（KillSwitch により書き込まれる）
  - リスク条件（ドローダウンやポジション上限）に達した場合に書き込まれると、ExecutionEngine を停止させるための信号になります。
  - kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START=1 で有効化可能（本番では注意）。

## 注意事項 / 補足
- Paper Trading は本番 DB と分離され、デフォルトで data/paper_trading.db を使用します（settings.is_paper をサポート）。
- psutil を使ってプロセス優先度や CPU affinity を設定します。権限不足により設定できない場合は警告が出ます。
- OpenAI を使う機能（news_nlp / regime_detector）を実行するには OPENAI_API_KEY が必要です。API エラー時はフェイルセーフで処理を続行するよう実装されています（部分失敗の保護やリトライロジックあり）。
- monitoring_db.init は既存 DB に対してマイグレーション（カラム追加）を行います。互換性に配慮した処理が含まれます。

## ディレクトリ構成（抜粋）
リポジトリの主要ファイル／フォルダ構成（src/kabusys 以下）：

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースを LLM でスコアリング
    - regime_detector.py         — 市場レジーム判定
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py           — （未表示のアラート実装）
  - execution/                    — Execution エンジン関連（order, broker 等）
    - order_repository.py
    - order_manager.py
    - execution_engine.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/                         — 実行時に利用するデータ / DB / フラグ（通常は作成する）
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite, paper mode)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - kill.flag
    - stop_requested.flag

（実際のリポジトリには上記以外のファイルや追加モジュールが存在することがあります）

## よく使うコマンドまとめ
- .env 作成ウィザード
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 実行エンジン起動
  ```bash
  python -m kabusys.run_execution
  ```
- 監視ループ起動
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

追加で README に含めたい内容（例: API ドキュメント、設定例、データベーススキーマ詳細、デプロイ手順など）があれば教えてください。必要に応じてサンプル .env のテンプレートや systemd/Windows サービスの起動例も追記できます。