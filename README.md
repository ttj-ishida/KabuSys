# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）などの主要コンポーネントを含むモジュール群で構成されています。実行・運用に必要な設定は .env によって行います。

注意: 本 README はソースコード（src/kabusys 以下）をもとにした概要と利用手順を示しています。

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要要件（依存関係）
- セットアップ手順
- 使い方（主要コマンド / 実行例）
- 環境変数（主なキー）
- ディレクトリ構成（主要ファイルの説明）
- 補足（運用上の注意）

---

プロジェクト概要
- KabuSys は日本株自動売買向けのコンポーネント群です。
- 取引（ExecutionEngine）と監視（Monitoring）は分離され、監視は停止フラグや Kill Switch によって取引エンジンを安全に停止できます。
- DuckDB / SQLite を用いたデータ分析・ログ保存、OpenAI API を用いたニュースのセンチメント解析などをサポートします。
- 設定は .env（自動ロード機能あり）と config/*.yaml（運用設定）で管理します。

主な機能一覧
- ExecutionEngine 起動 / 発注処理（paper_trading モードでは MockBroker を使用）
- Monitoring（SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine）
  - CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度チェック
  - ドローダウン検出・ポジション上限監視・Kill Switch 発動
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約、レジーム乗数）
- リサーチ（ファクター計算: Momentum / Volatility / Value、将来リターン、IC 計算など）
- AI モジュール
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメント（ai_scores へ保存）
  - regime_detector: ETF とマクロニュースの組合せで日次レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト
- 設定関連ツール
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- ユーティリティ
  - 統一ログ設定（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）

必要要件（依存関係）
- Python 3.10+（ソースでの型記法（|）を考慮）
- パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（任意：validate_config の YAML 検証に使用）
- 標準ライブラリ: sqlite3, logging, threading, datetime など

インストール（例）
- 仮想環境を作成してから依存パッケージをインストールしてください。
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
  - pip install duckdb psutil openai PyYAML

セットアップ手順
1. リポジトリをクローンし、仮想環境を有効化
2. 依存パッケージをインストール（上記参照）
3. .env の用意
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参考にファイルを配置（.env は Git にコミットしない）
4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit 1）
5. データディレクトリの作成（デフォルト）
   - data/（SQLite / PID / フラグ等）
   - logs/（ログ）
   多くのスクリプトは起動時にディレクトリを作るが、パーミッション等の確認を推奨します。

主要環境変数（代表）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用・経路
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト data/paper_trading.db）
  - OPENAI_API_KEY: OpenAI 呼び出し用キー（AI モジュール使用時）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/…）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート通知（任意）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の模擬約定挙動）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング秒数（デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

使い方（主要コマンド / 実行例）
- 設定ウィザード（対話式 .env 生成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict
- ExecutionEngine 起動（取引実行）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBroker を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と分離されます。
- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は設定に関わらず本番用 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- AI / プログラムからの呼び出し
  - ニューススコアリング（プログラム的に）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="…")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="…")

運用上のフラグ / PID ファイル
- 停止リクエスト: data/stop_requested.flag（プロセスがこのファイルを検知するとループ終了）
- Kill Switch: data/kill.flag（KillSwitch が書き込むと ExecutionEngine に停止シグナルを送る運用）
- PID ファイル: data/execution.pid（ExecutionEngine が使用）

設計上の挙動（抜粋）
- run_monitoring:
  - プロセス優先度を High に設定し（可能な場合）、監視ループを開始します。
  - MONITOR_POLL_INTERVAL で指定された秒数（デフォルト 60）で monitor.check_once() を実行。
  - stop_requested.flag を検知するとループを抜けて終了。
- run_execution:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、paper_trading.db にログ保存（本番 DB と分離）。
  - プロセス優先度を High に設定してから ExecutionEngine をスレッドで起動し、stop_requested.flag を検知すると engine.stop() を呼んで終了処理。
- monitoring_db:
  - SQLite に system_status / trade_logs / positions / risk_logs / dashboard テーブルを作成・マイグレーション。
  - MonitoringDB クラス経由で読み書き（永続化ロジックのみ、ビジネスロジックは各 Monitor 側）。

ディレクトリ構成（主要）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数自動読み込み（.env / .env.local）、Settings クラス
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - 起動前チェック CLI（.env と config/*.yaml の簡易検証）
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring のポーリングループ起動スクリプト
  - ai/
    - news_nlp.py — ニュースセンチメント取得と ai_scores 保存
    - regime_detector.py — 市場レジーム判定と market_regime への書き込み
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ
    - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / プロセス監視
    - trade_monitor.py — （取引監視。コードベースに存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor をまとめたポーリングエンジン
    - alert_manager.py — （通知ロジック。コードベースに存在）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・投下資金制御
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - tools/
    - paper_verification_report.py — Paper Trading の統合検証レポート生成
  - utils/
    - logging_setup.py — 統一ログ設定（stdout + 日次ローテート）
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - data/（ランタイムで作成される想定）
    - *.db, stop_requested.flag, kill.flag, execution.pid など
  - logs/（ログ出力先、デフォルト）

補足（運用上の注意）
- .env は機密情報（API トークン・パスワード等）を含むため、絶対にリポジトリにコミットしないでください。
- 本番（KABUSYS_ENV=live）での起動前に validate_config を実行して設定を確認してください。
- OpenAI を用いる機能は API コストが発生します。運用時はキー管理と呼び出し頻度に注意してください。
- データベース（SQLite / DuckDB）のバックアップ・権限管理を行ってください。特に本番環境では DB の所在・権限設定が重要です。
- process_priority や CPU affinity の変更は環境により権限が必要になります。権限不足時は警告が出てスキップされます。

---

以上がコードベースの主要な README です。実行方法や追加のドキュメント（例えば StrategyModel.md / PortfolioConstruction.md / API 仕様など）がある場合は、そちらを参照して運用手順を補完してください。必要であれば README を用途別（開発者向け・運用者向け）に分けた詳細版を作成します。どの項目を詳しく追記しましょうか？