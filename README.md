KabuSys
=======

日本株向けの自動売買・研究プラットフォーム（プロトタイプ実装）。
このリポジトリは、発注実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI を使ったニュースセンチメント評価などのコンポーネントで構成されています。

主な設計方針
- 本番とペーパートレードの分離（環境変数で切替）
- DuckDB を使ったリサーチ（prices_daily / raw_financials 等）
- SQLite を使った監視 / 発注ログの永続化
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定（オプション）
- .env による設定管理と対話式ウィザード / 検証 CLI を提供

機能一覧
- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）
  - 本番 / ペーパー両対応。paper_trading 環境では MockBrokerClient を使用し、専用 SQLite（data/paper_trading.db）へ記録。
  - プロセス優先度の設定、PID ファイル管理、停止フラグ監視。
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねたポーリングエンジン。
  - リスク（ドローダウン / ポジション上限）やデータ鮮度、プロセス停止検知。
  - kill.flag（Kill Switch）による ExecutionEngine 停止シグナル発行。
- 監視データ永続化（monitoring_db）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを提供。マイグレーション対応あり。
- ポートフォリオ構築ユーティリティ
  - 候補選定、等重・スコア重み付け、ポジションサイズ計算、セクター上限・レジーム乗数の計算。
- リサーチ / ファクター計算
  - momentum / volatility / value 等のファクター計算（DuckDB を用いた SQL 実装）。
  - 将来リターン計算や IC（Information Coefficient）などの統計ユーティリティ。
- AI モジュール
  - news_nlp: raw_news を LLM へ渡し銘柄別センチメントを ai_scores に書き込む。
  - regime_detector: ETF（1321）の MA200 とマクロニュースの LLM 評価を組み合わせて市場レジーム判定・保存。
  - OpenAI API 呼び出しはエラーに強く、リトライやフェイルセーフを実装。
- ツール
  - ペーパートレード検証レポート生成スクリプト（tools.paper_verification_report）
- 設定管理
  - .env 対話式ウィザード（config_setup.py）
  - 起動前検証 CLI（validate_config.py）

セットアップ手順（概要）
1. Python を用意
   - Python 3.10 以上を推奨（型ヒントの構文などで 3.10+ を想定）

2. 依存パッケージをインストール
   - 例:
     pip install duckdb psutil openai
   - optional:
     pip install pyyaml  # config/*.yaml の内容検証に必要
   - （requirements.txt がある場合はそれを使用）

3. プロジェクトルートに移動し .env を準備
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に .env を作成
   - 必須環境変数（最小）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な設定例:
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=（AI 機能利用時に必要）
     - LOG_LEVEL=INFO

4. 設定の検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit 1）

5. ログ・データディレクトリ
   - デフォルトで logs/ にアプリ別ログを出力（logs/execution.log, logs/monitoring.log 等）
   - data/ を使用して pid/flag/db を管理（.env にてパス上書き可）

使い方（主なコマンド）
- 環境設定ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（本番 / paper_trading は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 動作:
    - PID ファイルを書き出し（data/execution.pid デフォルト）
    - 停止フラグ: data/stop_requested.flag を作成すると安全に停止
    - paper_trading 時は settings.paper_sqlite_path を使用（本番 DB と分離）

- 監視プロセス起動
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（秒、デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用（監視 DB は常に本番対象）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可

設定（環境変数・重要項目）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 選択 / 主要:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - OPENAI_API_KEY: AI 機能利用時に必要
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用（任意）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - KILL_FLAG_CLEAR_ON_START: 0|1（本番で 1 は危険）
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒（run_monitoring 用、デフォルト 60）
  - PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject）

停止 / kill フラグ
- data/kill.flag — KillSwitch が作成するファイル。存在すると ExecutionEngine の起動や継続が制御されます。
- data/stop_requested.flag — run_execution, run_monitoring のループを終了させるための外部停止ファイル。手動で作成するとループが終了します。
- PID ファイル: data/execution.pid（Engine 起動時に書き出し）

ログ
- 標準出力に StreamHandler（stdout）で出力し、logs/<app_name>.log に日次ローテーションで出力します（デフォルトは logs/ ディレクトリ）。
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で制御可能。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（自動 .env ロード機能含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - execution/                — 実行エンジン関連（broker_factory, execution_engine, order_manager 等）
  - monitoring/
    - monitoring_db.py        — 監視 DB 層（SQLite）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - data/                     — （runtime）data/ 以下に DB / pid / flag を置く想定
  - logs/                     — ログ出力先（デフォルト）

設計上の注意点 / 運用メモ
- paper_trading 環境は「本番 DB と完全分離」を意図しています。PAPER_TRADING_SQLITE_PATH を正しく設定してください。
- OpenAI API を利用する機能は API キー（OPENAI_API_KEY）が必須。API 呼び出しはリトライ・フェイルセーフ実装済みですが、コストとレイテンシ管理は運用側で注意してください。
- validate_config は起動前の必須環境変数やファイルの存在チェックに便利です。CI / デプロイ前に利用することを推奨します。
- ログディレクトリ作成に失敗した場合、ファイルハンドラはスキップされ stdout のみで継続します（warning を出力）。

開発・拡張ポイント（今後の案）
- stocks マスタによる銘柄別 lot_size など発注ロジックの拡張
- 外部ブローカー実装の追加
- バックテスト用の独立したシミュレーションモード
- モニタリングのアラート送信先（LINE / Slack 等）の追加設定強化

参考コマンドまとめ
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---
必要に応じて README に含めたい追加情報（依存関係の正確な一覧、CI / デプロイ手順、設定例の .env.example、テーブル定義ドキュメント等）があれば教えてください。README をその内容に合わせて拡張します。