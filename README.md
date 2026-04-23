KabuSys
=======

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）の簡易 README です。  
このリポジトリはトレーディングエンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI を使ったニュース解析などの機能を含みます。

要点
----
- Python パッケージ名: kabusys（src/kabusys 配下）
- DB:
  - DuckDB: 分析・リサーチ用（デフォルト: data/kabusys.duckdb）
  - SQLite: 監視・ペーパートレード用（デフォルト: data/monitoring.db / data/paper_trading.db）
- 環境管理: .env を読み込み（自動読み込み、無効化可）
- ログ: logs/<app_name>.log（日次ローテーション、デフォルト 30 日保管）
- 実行環境切替: KABUSYS_ENV = development | paper_trading | live

主な機能一覧
-------------
- execution
  - 実際の注文発行を行う ExecutionEngine（本番/ペーパー両対応）
  - ブローカークライアントのファクトリ（環境に応じてモックを使用）
  - リスク管理（Rate limit、最大ポジション比率、ドローダウン等）
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常等の検出
  - RiskMonitor: ドローダウン／ポジション上限監視（kill flag 発動）
  - MonitoringEngine: 各モニタをまとめてポーリング、アラート連携
  - MonitoringDB: SQLite ベースの監視ログ永続化（テーブル作成／マイグレーション含む）
- portfolio
  - 候補選定・重み算出（等金額、スコア加重）
  - セクター上限適用・レジームに応じた乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap 対応）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
  - DuckDB 接続ベースで記述（外部 API なし）
- ai
  - news_nlp: OpenAI を用いてニュースを銘柄別にセンチメント評価し ai_scores テーブルへ書き込む（ペーパー検証やレジーム判定に利用）
  - regime_detector: ETF 等の MA とマクロニュース（LLM）を合成して market_regime を更新
- tools
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL 判定レポートを生成

セットアップ手順
----------------
1. Python 環境を用意（推奨: pyenv / venv）
   - Python 3.9+ を想定
2. 依存ライブラリをインストール
   - 必須例: duckdb, psutil, openai
   - YAML 検証を行う場合は PyYAML
   - 例:
     pip install -r requirements.txt
     （requirements.txt がない場合は個別インストール: pip install duckdb psutil openai PyYAML）
3. プロジェクトルートに .env を作成
   - 対話式ウィザードで作る場合:
     python -m kabusys.config_setup
   - 主要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 時の専用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL, LOG_DIR 等
   - 自動読み込みを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
4. 設定検証（起動前チェック）
   python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     python -m kabusys.validate_config --strict

使い方（主要スクリプト / コマンド）
---------------------------------
- 監視ループ起動（SystemMonitor をポーリング）
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き（正の整数）。
    注意: 1 未満・0 は無効（ログで警告してデフォルトに戻る）。
  - 実行:
    python -m kabusys.run_monitoring
  - 監視は常に settings.sqlite_path（本番 sqlite_path）を使います（環境に関わらず）。
  - 停止シグナル:
    - プロジェクトルート/data/stop_requested.flag を作成するとループが終了します。

- 実行エンジン起動（ExecutionEngine）
  - paper_trading モードでは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と分離されます。
  - 実行:
    python -m kabusys.run_execution
  - 停止／起動制御:
    - 起動時に data/stop_requested.flag が既にあると起動せず終了します。
    - 実行中に data/stop_requested.flag を作るとループ内で検出して engine.stop() が呼ばれます。
  - PID ファイル: data/execution.pid（Settings.pid_file_path による）

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で明示的に SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / レジームスコア等（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り DB を更新します。API キーは引数または OPENAI_API_KEY に設定。

- 設定ウィザード
  python -m kabusys.config_setup
  - .env の初期作成・更新を対話式に行います。生成後は validate_config の実行を推奨。

運用上のポイント
----------------
- KABUSYS_ENV による挙動差:
  - development : ローカルテスト用（発注なし）
  - paper_trading: ペーパートレード（モック発注・専用 DB を使用）
  - live       : 本番（実注文）
- kill flag / stop flag:
  - KillSwitch はリスク条件（ドローダウン等）で data/kill.flag を生成し ExecutionEngine に停止シグナルを送ります。
  - stop_requested.flag は run_* スクリプトを安全に停止させるためのフラグ（管理者手動でファイル作成/削除）
- ログ:
  - default: logs/<app_name>.log（日次ローテート）
  - ログディレクトリ作成に失敗した場合はコンソール出力のみ継続
- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動読み込みします
  - テスト等で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ディレクトリ構成（抜粋）
------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化レイヤ（テーブル作成/マイグレーション）
    - system_monitor.py
    - trade_monitor.py       — （コードベースにある想定モジュール）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信の責務を持つ想定モジュール）
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - tools/
    - paper_verification_report.py

補足（実装上の注意）
------------------
- MONITOR_POLL_INTERVAL は run_monitoring のポーリング間隔を秒で指定。正の整数でない場合はデフォルト 60 秒にフォールバックします。
- SystemMonitor は監視用 DB と DuckDB の両方に接続します（データ鮮度チェック等）。
- ExecutionEngine は paper_trading モード時に MockBroker を使用し、ペーパートレード DB に完全分離して記録します。
- OpenAI 呼び出し周りはリトライ・バリデーション処理を備え、失敗時はフォールバック（部分的にスキップ）します。
- settings モジュールはプロジェクトルートを基に自動で .env を読み込みます（必要に応じて無効化可）。

ライセンス / バージョン
-----------------------
- パッケージバージョン: src/kabusys/__version__ = "0.1.0"
- ライセンス情報はリポジトリのトップレベルの LICENSE を参照してください（存在する場合）。

連絡先・貢献
-------------
- バグ報告や改善提案は Issue を立ててください。プルリク歓迎です。

以上。必要であれば README に記載する具体的な .env.example、サンプルコマンドや systemd / supervisor 用の起動ユニット例、CI テスト手順なども追記できます。どの情報を追加しますか？