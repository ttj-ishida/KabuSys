# KabuSys — README

これは日本株自動売買システム KabuSys のコードベースの概要と利用方法です。以下はリポジトリ内の主要コンポーネント、セットアップ手順、起動方法、ディレクトリ構成の説明です。

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件 / 依存パッケージ
- セットアップ手順
- 使い方（よく使うコマンド例）
- 環境変数（主なもの）
- ログ / PID / フラグファイルについて
- ディレクトリ構成（主要ファイル一覧）
- トラブルシューティング

プロジェクト概要
- KabuSys は日本株の自動売買システムのコードベースです。
- 注文実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算・リサーチ、AI（ニュース NLP / レジーム判定）などのモジュールを含みます。
- DuckDB を分析用 DB、SQLite を監視・履歴用 DB（paper_trading 用に別 DB を使用可能）として利用します。
- 設定は .env ファイル（または環境変数）で提供し、対話ウィザードや検証ツールが用意されています。

主な機能一覧
- Execution
  - 実際のブローカークライアント／モック（paper_trading）を用いた発注処理（run_execution.py）
  - リスク管理（RiskManager）、オーダー管理、照合（Reconciler）等の組み立て
  - paper_trading 時は MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた監視エンジン（MonitoringEngine）
  - 監視ログの永続化（SQLite）とダッシュボード更新、Kill Switch（条件で execution を停止）
  - run_monitoring.py によるポーリングループ
- Portfolio / Strategy
  - 候補選定、重み算出、ポジションサイズ計算、セクターキャップ、レジーム乗数などの純粋関数群
- Research
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC 計算、統計サマリーなど
- AI（OpenAI）
  - news_nlp: raw_news を集約して LLM に投げ、銘柄別センチメントスコアを ai_scores に保存
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して日次レジーム判定
- ツール
  - 設定ウィザード（config_setup.py）で .env 生成 / 更新
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

前提条件 / 依存パッケージ
- Python 3.9+（型注釈の Union 記法等を想定）
- 推奨 / 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の内容検証時）
- SQLite は標準ライブラリで使用可能
- 実環境でのブローカー連携には kabuステーション API の設定が必要

（pip のインストール例）
pip install duckdb psutil openai PyYAML

セットアップ手順
1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成して有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .\.venv\Scripts\activate   # Windows
3. 依存パッケージをインストール
   pip install duckdb psutil openai PyYAML
4. .env の作成
   - 対話ウィザードを使う（推奨）:
     python -m kabusys.config_setup
   - もしくは .env を直接作成（.env.example を参照）
5. 設定検証
   python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い
6. DB ファイル（data ディレクトリ等）は自動作成されるが、パスの親ディレクトリが存在しないと警告が出る場合があります（validate_config で警告確認可能）。

使い方（よく使うコマンド）
- ExecutionEngine を起動（通常・本番 / paper_trading に依存）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録
  - 起動時、data/stop_requested.flag が存在すると起動せず終了
- Monitoring を起動（ポーリング）
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）で間隔を変更可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用（環境に依らず）
- 設定ウィザード
  python -m kabusys.config_setup
- 設定検証
  python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

主な環境変数（抜粋とデフォルト）
- 必須（validate_config でチェック）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 用 DB
- ログ
  - LOG_LEVEL (デフォルト: INFO)
  - LOG_DIR (デフォルト: logs/)
- OpenAI
  - OPENAI_API_KEY（news_nlp / regime_detector で使用）
- モニタ・実行固有
  - MONITOR_POLL_INTERVAL（秒、run_monitoring のポーリング間隔を上書き）
  - PAPER_FILL_MODE（instant / partial / never / reject、paper_trading の MockBrokerClient 挙動）
  - PID / フラグパス（Settings 経由でカスタマイズ可能）
    - PID_FILE_PATH (デフォルト data/execution.pid)
    - KILL_FLAG_PATH (デフォルト data/kill.flag)
    - KILL_FLAG_CLEAR_ON_START (0/1)

ログ / PID / フラグファイルについて
- ログ: kabusys.utils.logging_setup.setup_logging により stdout と日次ローテートファイル（logs/<app_name>.log）へ出力。
- PID: run_execution は data/execution.pid を利用（Settings.pid_file_path）
- 停止フラグ:
  - data/stop_requested.flag: run_monitoring / run_execution はこのファイル存在でループやエンジンを停止
  - Kill Switch: 条件（ドローダウン等）に応じて data/kill.flag を生成し ExecutionEngine に停止シグナルを送る設計
- 注意: 本番環境では KILL_FLAG_CLEAR_ON_START は 0 を推奨（自動クリアは危険）

データベース（監視）スキーマ（主なテーブル）
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (単一行 id=1 を保持。portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 設定読み込み / Settings クラス（.env 自動ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py       — （取引監視。コードベースに含まれる）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信／管理）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - data/ (実行時に生成されるデータ/DB/log 等)
  - config/ (system_config.yaml 等の YAML ファイル群)

トラブルシューティング（よくある項目）
- .env がない / 必須環境変数がない
  - python -m kabusys.config_setup で作成、あるいは validate_config で不足項目を確認
- PyYAML がない
  - validate_config は YAML パース検証をスキップして警告を出します。YAML 検証が必要なら PyYAML をインストール
- OpenAI を使う機能が動かない
  - OPENAI_API_KEY を設定してください。API エラーはフェイルセーフ（多くの箇所で 0.0 やスキップにフォールバック）
- 監視 / 実行がすぐ終了する
  - data/stop_requested.flag や data/kill.flag の存在を確認（存在すると起動しない / 停止します）
- ログファイルが作成されない
  - デフォルトは logs/。書き込み権限や LOG_DIR 設定を確認。ディレクトリ作成に失敗した場合はコンソールに警告が出ます。

補足
- paper_trading モードは実発注を行わず、MockBrokerClient を用いて data/paper_trading.db に記録します。本番 DB と分離されるため安全に検証できます。
- モジュール設計は「DB を参照するパス」と「純粋関数群（DB 参照無し）」を明確に分離しており、リサーチ／ポートフォリオ計算は副作用なしにテスト可能です。
- run_monitoring は MONITOR_POLL_INTERVAL によってポーリング間隔を調整できます（環境変数で秒指定）。

以上が README の概要です。必要であれば、起動例の具体的なコマンドや .env のサンプルテンプレート、より詳しいディレクトリツリーや API 使用例（OpenAI 呼び出し等）を追加で作成します。どの部分を深掘りしますか？