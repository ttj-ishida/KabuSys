# KabuSys

日本株向け自動売買システムのライブラリ群・起動スクリプト群です。  
このリポジトリはバックテスト／ペーパートレード／本番（ライブ）で使うためのモジュール群（シグナル生成、ポートフォリオ構築、発注実行、監視、AI 補助など）を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境設定ウィザード（.env）
  - 設定検証
  - 実行エンジン起動（Execution）
  - 監視デーモン起動（Monitoring）
  - ペーパートレード検証レポート
  - AI 関連処理（ニュース NLP / レジーム判定）
- ディレクトリ構成（主要ファイル説明）
- 運用に関する注意点

---

プロジェクト概要
- 日本株自動売買に必要な要素（ファクター計算、特徴量探索、ポートフォリオ構築、ポジションサイジング、発注・リスク制御、監視、AI 補助）をモジュール化した Python パッケージです。
- 起動スクリプトは package モジュール経由で呼び出し可能（例: python -m kabusys.run_execution）。
- 環境変数 / .env による設定管理を想定しています（Settings クラス）。

機能一覧
- 環境読み込み・管理（kabusys.config）
  - .env 自動ロード（プロジェクトルート検出）
  - 必須 / 任意設定の取得ラッパー
- 環境設定ウィザード（kabusys.config_setup）
  - 対話式で .env を生成 / 更新
- 設定検証ツール（kabusys.validate_config）
  - 起動前に環境変数や config/*.yaml の妥当性をチェック
- 実行エンジン起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときはペーパートレード用 DB / MockBroker を使用
  - 停止フラグ (data/stop_requested.flag, data/execution.pid) に対応
  - プロセス優先度設定、DB 初期化、ExecutionEngine の起動制御
- 監視デーモン起動スクリプト（kabusys.run_monitoring）
  - SystemMonitor を定期ポーリング（環境にかかわらず本番 sqlite_path を使用）
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 停止フラグによりループを終了
- 監視フレームワーク（kabusys.monitoring）
  - MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
  - Kill Switch（data/kill.flag）で Execution を安全に停止できる仕組み
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等配分・スコア加重、セクターキャップ、レジーム乗数、株数計算（単元丸め）
- 研究用モジュール（kabusys.research）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI 補助機能（kabusys.ai）
  - news_nlp: OpenAI（gpt-4o-mini）でニュースセンチメントを算出して ai_scores テーブルへ格納
  - regime_detector: ma200 とマクロニュースの LLM 評価を合成し market_regime を生成
- ユーティリティ
  - ロギング設定（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（kabusys.utils.process_priority）
  - 各種 DB 初期化・マイグレーション用コード

---

セットアップ手順（開発 / 実行環境）
1. Python と依存ライブラリ
   - Python 3.9+（型注釈や一部 API に依存）
   - 必須ライブラリ（少なくとも）:
     - duckdb
     - psutil
     - openai
   - 任意 / 機能限定:
     - PyYAML（config/*.yaml の構文チェックを行う場合）
   - 例（pip 使用）:
     pip install duckdb psutil openai
     pip install PyYAML  # optional

2. リポジトリ配置（パッケージとしてインストールするか PYTHONPATH に追加）
   - 開発時: プロジェクトルートをカレントにして実行
   - 配布: pip install -e .（setup 配下がある場合）

3. 環境変数 / .env の準備
   - 対話式ウィザードを推奨:
     python -m kabusys.config_setup
   - 必須環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な設定例（.env）
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     KABUSYS_ENV=development  # development | paper_trading | live
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     OPENAI_API_KEY=sk-...
   - 自動ロード:
     - .env と .env.local はプロジェクトルート（.git や pyproject.toml のあるディレクトリ）から自動で読み込まれます。
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. DB ディレクトリ作成
   - data/ や logs/ ディレクトリを作成しておくと起動時の権限エラーを避けやすい:
     mkdir -p data logs

---

使い方

1) 環境設定ウィザード
   - .env を対話的に生成 / 更新:
     python -m kabusys.config_setup
   - 終了後は python -m kabusys.validate_config で検証してください。

2) 設定検証
   - 設定の事前チェック:
     python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります:
     python -m kabusys.validate_config --strict

3) 実行エンジン起動（Execution）
   - 起動:
     python -m kabusys.run_execution
   - 動作:
     - KABUSYS_ENV によって挙動が分岐します。
       - paper_trading: MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録。実取引と完全に分離。
       - live / development: 本番設定に従います（Settings 参照）。
     - 起動時にプロセス優先度を "high" に設定し、PID ファイル（data/execution.pid）を利用します。
     - 停止フラグ（data/stop_requested.flag）を検知するとエンジンを停止します。

4) 監視デーモン起動（Monitoring）
   - 起動:
     python -m kabusys.run_monitoring
   - 動作:
     - SystemMonitor を定期的に poll して system_status などに記録します。
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定できます（例: MONITOR_POLL_INTERVAL=30）。
     - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します。
     - stop_requested.flag を検出するとループを終了します。

5) ペーパートレード検証レポート
   - ペーパートレード DB（デフォルト data/paper_trading.db）から簡易検証レポートを作成:
     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション --db で DB ファイルパスを指定できます。

6) AI（ニュース NLP / レジーム判定）
   - news_nlp.score_news と regime_detector.score_regime が主要な公開 API。
   - 両方とも OpenAI API キー（OPENAI_API_KEY 環境変数または明示的引数）を必要とします。
   - 例（スクリプトから呼ぶ）:
     from kabusys.ai.news_nlp import score_news
     from kabusys.ai.regime_detector import score_regime
     # duckdb_conn は duckdb.connect(...) で取得
     score_news(duckdb_conn, target_date, api_key="sk-...")
   - 注意: API 失敗時はフェイルセーフ（スコア 0.0 等）で進める設計。ただし API キー未設定時は ValueError を送出。

7) ログ設定
   - 汎用関数: kabusys.utils.logging_setup.setup_logging(app_name="execution")
   - デフォルトは logs/ に日次ローテートでログを出力します（30 日保持）。
   - 環境変数 LOG_DIR / LOG_LEVEL で上書き可能。

---

重要な設定 / 環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 主要:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH 等（Settings を参照）

---

ディレクトリ構成（主要ファイルと役割）
- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数読み込みと検証
    - .env の自動ロードロジック
  - config_setup.py
    - .env を対話式に生成/更新する CLI
  - validate_config.py
    - 起動前に設定の妥当性を検査する CLI
  - run_execution.py
    - ExecutionEngine を起動するスクリプト（スレッドで実行し stop フラグを監視）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py: ロギング初期化ユーティリティ
    - process_priority.py: プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py: SQLite のテーブル作成・操作ラッパー（MonitoringDB）
    - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py
    - kill_switch.py, alert_manager.py (アラート基盤)
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, broker_factory.py, reconciler.py, risk_manager.py
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/
    - factor_research.py, feature_exploration.py
  - ai/
    - news_nlp.py: ニュースセンチメント算出（OpenAI 使用）
    - regime_detector.py: 市場レジーム判定（ma200 + マクロニュース）
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート生成ツール

---

運用に関する注意点 / 推奨事項
- 本番環境（KABUSYS_ENV=live）では設定を慎重に確認してください。validate_config は live の警告を出します。
- .env は絶対に Git にコミットしないでください（秘密情報が含まれるため）。
- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）は ExecutionEngine を安全に停止させる重要な手段です。運用ルールを明確にしてください。
- run_monitoring は監視用 DB（SQLITE_PATH）を使用します。監視 DB は本番 DB と分離して使うことを推奨しますが、実装上は環境にかかわらず sqlite_path を使う設計になっています（監視は本番 DB を想定）。
- OpenAI など外部 API を使う機能は API キーと料金が必要です。レートリミットやエラー対策はコード内で基本的なリトライが組み込まれていますが、運用時の監視を行ってください。
- ログディレクトリは権限の確保とディスク容量管理を行ってください（TimedRotatingFileHandler により日次ローテートします）。

---

追加情報 / 開発者向けヒント
- DuckDB は分析処理（research / ai の一部）で使われます。DuckDB 接続オブジェクト（duckdb.connect(path)）を関数に渡して利用してください。
- MonitoringDB は冪等に DB スキーマを初期化します（init_monitoring_db）。既存列のマイグレーションも一部組み込まれています。
- テスト時に環境読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ローカル開発では KABUSYS_ENV=development を使い、実際の発注 API との接続は無効化またはモック化してください。

---

この README はコードベースから自動的に要点を抽出して作成しています。実運用時には config/*.yaml（存在する場合）や ExecutionEngine の具体的な設定、ブローカ実装（BrokerClientFactory）などを合わせて確認してください。README に不足・誤記があれば差し戻してください。