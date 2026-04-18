README
======

概要
----
KabuSys は日本株向けの自動売買システムおよび関連ツール群です。本リポジトリは以下の機能を持つモジュール群を含みます:

- 発注エンジン（ExecutionEngine）とそれを起動するスクリプト
- システム監視（Monitoring）と Kill Switch（停止フラグ）機構
- ポートフォリオ構築（候補選定・重み計算・株数決定・リスク調整）
- リサーチ用ファクター計算・特徴量解析
- ニュース NLP（OpenAI を使ったセンチメント評価）とレジーム判定
- 各種ユーティリティ（ログ設定・プロセス優先度設定など）
- ペーパートレード検証レポート生成ツール

要点:
- KabuSys は環境変数（.env）で設定を行います。対話式ウィザードと検証 CLI を提供します。
- paper_trading モードでは MockBrokerClient を使用し、本番 DB と分離した data/paper_trading.db に記録します。
- 監視プロセスは環境に関係なく本番用 sqlite_path を参照して監視ログを記録します。

主な機能一覧
--------------
- 実行・監視
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて実際発注 / ペーパートレードを切替）
  - run_monitoring.py: SystemMonitor をポーリングしてシステム状態を記録・アラート評価
  - 停止/Kill Switch 機構（data/stop_requested.flag, data/kill.flag, execution.pid）

- 設定管理
  - .env 対話式生成: config_setup.py
  - 設定検証 CLI: validate_config.py（--strict オプションあり）

- 監視（monitoring）
  - system_monitor: CPU / メモリ / ディスク、データ鮮度、実行プロセス監視
  - trade_monitor: 発注ログの異常検出（滞留注文・約定異常など）
  - risk_monitor: ドローダウン・ポジション上限監視
  - monitoring_db: SQLite スキーマ管理と永続化 API
  - monitoring_engine: 複数 Monitor を束ねてポーリング、Kill Switch 判定・アラート通知

- 発注/実行（execution）
  - BrokerClientFactory / ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager（設計に応じた発注フローを実装）
  - paper_trading 用に MockBrokerClient と独立 DB をサポート

- ポートフォリオ（portfolio）
  - 候補選定（select_candidates）、重み計算（calc_equal_weights / calc_score_weights）
  - ポジションサイジング（calc_position_sizes）
  - セクターキャップ適用 / レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- リサーチ（research）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC 計算、統計サマリ

- AI
  - news_nlp: raw_news をまとめて OpenAI に投げ、銘柄別スコアを ai_scores に保存（バッチ・リトライ・バリデーション実装）
  - regime_detector: ETF とマクロニュースを組み合わせて市場レジームを判定して保存

- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを出力

セットアップ手順
----------------
前提:
- Python 3.9+（ソースの typing による想定）
- システムにより追加で psutil, duckdb, openai, PyYAML（オプション）等が必要

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

2. 依存パッケージのインストール
   - 必要最低限:
     - pip install duckdb psutil openai
   - 開発時・一部機能のために推奨:
     - pip install PyYAML
   （requirements.txt がある場合はそれを使用してください）

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要:
     - KABUSYS_ENV: development | paper_trading | live
     - PAPER_FILL_MODE (paper_trading 時の挙動)
     - DUCKDB_PATH, SQLITE_PATH（デフォルト: data/kabusys.duckdb, data/monitoring.db）

4. 設定検証
   - python -m kabusys.validate_config
   - strict モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

5. ログディレクトリの確認
   - デフォルトログディレクトリ: logs/
   - 環境変数 LOG_DIR で変更可
   - LOG_LEVEL でログレベルを指定（DEBUG/INFO/...）

使い方
------
起動スクリプト（推奨はモジュール実行形式）

- ExecutionEngine を起動（本番 or ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中は data/execution.pid（PID ファイル）を利用
    - 停止は data/stop_requested.flag を作成することで行える

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔秒数を上書き（デフォルト: 60）
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用してログを記録
  - data/stop_requested.flag を置くとループを終了

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルト DB は env もしくは data/paper_trading.db

- AI / レジーム判定等（ライブラリ関数として使用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数か環境変数 OPENAI_API_KEY を使用

環境変数の主な一覧
------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 重要 / 推奨:
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH (例: data/kabusys.duckdb)
  - SQLITE_PATH (例: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
  - LOG_LEVEL (INFO, DEBUG...)
  - OPENAI_API_KEY（AI 機能利用時）
  - MONITOR_POLL_INTERVAL（run_monitoring 用オーバーライド）
  - PID_FILE_PATH / KILL_FLAG_PATH（必要に応じて変更）
  - PAPER_FILL_MODE（instant|partial|never|reject）

停止・Kill Switch
----------------
- 実行中の ExecutionEngine を外部から停止する方法:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して安全終了
  - KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine の停止トリガーとなる
- Kill flag の自動クリアは KILL_FLAG_CLEAR_ON_START 環境変数で制御（本番では無効推奨）

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数・設定読み込みロジック
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定

- monitoring/
  - monitoring_db.py       — SQLite スキーマ / 永続化 API
  - system_monitor.py      — システム / データ鮮度監視
  - trade_monitor.py       — 発注ログ監視（滞留・異常等）
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - kill_switch.py         — kill.flag の書き込み/評価
  - monitoring_engine.py   — 複数 monitor を束ねるエンジン
  - alert_manager.py       — （アラート送信の抽象化／実装は別途）

- execution/
  - execution_engine.py    — 発注セッションを管理するエンジン
  - broker_factory.py      — ブローカークライアント生成（本番 / Mock 切替）
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
  - news_nlp.py            — ニュースセンチメント（OpenAI 呼び出し・バッチ・検証）
  - regime_detector.py     — レジーム判定（ETF MA + マクロセンチメント合成）

- tools/
  - paper_verification_report.py

- monitoring テーブル、ログ、PID/flag は data/ 配下に保存する想定（例: data/monitoring.db, data/execution.pid, data/kill.flag）

開発メモ / 注意点
-----------------
- .env ファイルは絶対に Git にコミットしないでください（機密情報が含まれます）。
- run_monitoring の MONITOR_POLL_INTERVAL は 1 秒以上の整数を渡してください。不正値はデフォルト 60 秒にフォールバックします。
- ペーパートレードは本番データと完全分離して動作するよう実装されています（別 SQLite ファイル）。
- OpenAI への呼び出しにはレート制限・ネットワーク障害を考慮したリトライ処理が組み込まれていますが、API 使用量とコストに注意してください。
- DuckDB 操作は SQL を直接実行します。スキーマやデータの準備（prices_daily, raw_financials, raw_news 等）は事前に整備してください。
- 本 README はコードの現状に基づく概要ドキュメントです。詳細な実装や追加設定はソース内の docstring / コメントを参照してください。

ライセンス / 連絡先
------------------
- 本プロジェクトのバージョン: 0.1.0（src/kabusys/__init__.py）
- 追加情報や問題報告はリポジトリの Issue を利用してください。

以上。必要であればセクションを追記（例: 具体的な .env 例、データベーススキーマ詳細、サンプルコマンド）します。どの情報を追加しますか？