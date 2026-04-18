KabuSys
======
日本株向けの自動売買 / リサーチ基盤（モジュール群）です。  
このリポジトリは発注エンジン、監視、ポートフォリオ構築、ファクター計算、LLM を使ったニュース解析などの機能を含む実験的フレームワークを提供します。

主な特徴
------
- ExecutionEngine（発注実行）と Monitoring（監視）を分離して運用可能
- Paper Trading モード（本番 DB と分離）をサポート
- DuckDB を用いたリサーチ用時系列データ処理（factor / research モジュール）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント / レジーム判定機能
- SQLite による監視・トレードログ永続化（monitoring_db）
- 設定ウィザード（.env 生成）と事前検証ツール
- 日次ローテートされるログ出力（logs/<app>.log）

機能一覧
------
- 起動スクリプト
  - run_execution.py : 発注エンジン起動（KABUSYS_ENV により paper_trading / live を切替）
  - run_monitoring.py : システム監視ポーリングループ
- 設定関連
  - config_setup.py : .env を対話式に生成 / 更新するウィザード
  - validate_config.py : .env と config/*.yaml の事前検証 CLI（--strict オプションあり）
  - config.Settings: 環境変数のラップと検証（自動 .env ロード機能あり）
- 監視
  - monitoring/ : SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine
  - monitoring_db.py : SQLite のスキーマ初期化と CRUD ラッパ
- 発注関連（execution/*）
  - BrokerClientFactory（本番 / モック切替）
  - ExecutionEngine, OrderManager, RiskManager, Reconciler, OrderRepository 等
- ポートフォリオ構築（portfolio/*）
  - 候補選定、重み付け、ポジションサイズ計算、セクター制限
- リサーチ（research/*）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算など
- AI モジュール（ai/*）
  - news_nlp.py : ニュース記事を LLM でスコアリングして ai_scores に書き込み
  - regime_detector.py : ETF + マクロニュースから市場レジーム判定を行い DB に保存
- ツール
  - tools/paper_verification_report.py : Paper Trading 結果の検証レポート生成

セットアップ手順
------
前提
- Python 3.9+（パッケージの型アノテーション依存）
- 必要な外部ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証用、必須ではない）
インストール例（pip）
  pip install -r requirements.txt
（requirements.txt が無い場合は上記ライブラリを個別にインストールしてください）

初期設定
1. プロジェクトルートに移動（この README と同階層を想定）
2. .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考に）
3. 設定検証（任意）:
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
4. データディレクトリ（data/）とログディレクトリ（logs/）は自動作成されることが多いですが、権限などに注意してください。

重要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- OPENAI_API_KEY (news_nlp / regime_detector で必要)
- LOG_LEVEL (DEBUG/INFO/...)
- LOG_DIR (ログ保存先)
- MONITOR_POLL_INTERVAL (run_monitoring: ポーリング間隔秒、デフォルト: 60)
- PAPER_FILL_MODE (paper_trading の約定挙動: instant | partial | never | reject)

使い方（典型的なコマンド）
------
- 発注エンジン（Execution）起動
  - 本番/ペーパートレードを .env の KABUSYS_ENV で切り替え
  - 起動:
    python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成すると起動中のループが検出して終了します
    - Kill Switch（リスクトリガ）により data/kill.flag が書かれると Execution 停止が試みられます
  - PID ファイル: data/execution.pid（設定で変更可）

- 監視サービス（Monitoring）起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒指定可能（例: export MONITOR_POLL_INTERVAL=30）
  - 停止: data/stop_requested.flag を作成するとループを抜けます

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

ログ
------
- setup_logging により stdout と 日次ローテーションファイル（logs/<app_name>.log）へ出力されます。
- LOG_DIR 環境変数でログディレクトリを上書き可能。
- ローテーションは日次、30世代保持。

ファイル / フラグの取り扱い
------
- 停止フラグ: data/stop_requested.flag
  - 起動ループはこれを検出して安全終了します
- Kill Switch フラグ: data/kill.flag
  - KillSwitch がトリガーを満たした場合に書き込まれます（ExecutionEngine はこれを検出して停止）
- PID ファイル: data/execution.pid（ExecutionEngine 起動時に使用）

AI（OpenAI）連携
------
- OPENAI_API_KEY を設定して利用します（引数経由でも指定可能）
- news_nlp と regime_detector は LLM 呼び出しを行い、レスポンスのパースやリトライ等を実装済みです
- 本番での使用時は API レートやコスト、エラーハンドリングに注意してください

データベース
------
- DuckDB（分析用）
  - デフォルト: data/kabusys.duckdb（パスは Settings.duckdb_path で上書き可能）
- SQLite（監視 / 発注履歴）
  - 監視用: data/monitoring.db（Settings.sqlite_path）
  - Paper Trading 用: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
- monitoring_db.init_monitoring_db() は必要テーブルを冪等に作成します（スキーママイグレーションを含む）

ディレクトリ構成（抜粋）
------
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み・Settings
  - config_setup.py           — .env ウィザード
  - validate_config.py        — 検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite 操作ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/                 — Execution エンジン関連実装（OrderManager 等）
  - portfolio/                 — ポートフォリオ構築ロジック（builder / sizing / risk）
  - research/                  — factor / feature_exploration（DuckDB ベース）
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - ... その他ユーティリティ

注意事項 / 運用上のヒント
------
- .env は決してリポジトリにコミットしないでください（config_setup でも注意喚起あり）。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します。
- Paper Trading による動作確認を十分に行ってから live 環境に切り替えてください。
- OpenAI API のキー・利用料に注意。大量バッチ処理はコスト発生します。
- プロセス優先度や CPU affinity を設定するユーティリティ（utils.process_priority）を用いて、実運用でのリソース割当を調整できます（権限に依存）。

開発・拡張
------
- research モジュールは DuckDB 接続を受け取り SQL と Python でファクターを計算する構造です。prices_daily / raw_financials 等のテーブルを用意すれば即座に利用できます。
- ai モジュールは OpenAI SDK の返り値に依存します。テスト時は内部の API 呼び出し関数をモックすることを想定しています（unittest.mock.patch 等）。

サンプル .env（最小）
------
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...

最後に
------
この README はコードベースの主要機能と典型的な運用方法をまとめたものです。個別モジュール（execution, monitoring, ai, research, portfolio）の詳細は各ファイルの docstring とソースコードを参照してください。質問や補足が必要であればお知らせください。