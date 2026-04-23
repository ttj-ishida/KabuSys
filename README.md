KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向け自動売買システム「KabuSys」の主要コンポーネント群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI 補助など）を含んでいます。本 README はプロジェクト概要、主な機能、セットアップ手順、起動方法、ディレクトリ構成をまとめた簡易ガイドです。

プロジェクト概要
----------------
- 自動売買の実行エンジン（ExecutionEngine）とそれを監視する Monitoring コンポーネントを中心に構成されています。
- DuckDB を分析用 DB、SQLite を監視・トレードログ用 DB として利用します。
- 本番（live）・ペーパートレード（paper_trading）・開発（development）を環境変数 KABUSYS_ENV により切り替え可能。
- Paper Trading モードでは MockBrokerClient を使い、実トレード DB と完全に分離して data/paper_trading.db に記録します。
- ニュース NLP（OpenAI）やレジーム判定、ファクター計算、ポートフォリオ構築、ポジションサイズ計算などを含むモジュール群を提供します。

主な機能一覧
-------------
- Execution（発注処理）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading 時は MockBroker を利用し、専用 DB に記録
  - プロセス優先度（high/normal/low）を設定するユーティリティ
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - system_status / trade_logs / risk_logs / positions / dashboard テーブルを持つ監視用 SQLite（init_monitoring_db）
  - Kill Switch（閾値超過時に data/kill.flag を書き込んで Execution を停止）
  - run_monitoring.py によるポーリングループ（MONITOR_POLL_INTERVAL 環境変数で間隔変更可）
- ポートフォリオ関連（pure function）
  - 候補選定、ウェイト計算、単元株・上限・リスクに基づく株数算出
- リサーチ / ファクター計算
  - Momentum / Volatility / Value の各ファクター計算（DuckDB の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（OpenAI）連携
  - ニュース記事の銘柄別センチメントスコア算出（ai.news_nlp）
  - マクロニュース + ETF ma200 乖離から市場レジーム判定（ai.regime_detector）
  - API 呼び出しはリトライ/エラーハンドリングを備え、失敗時はフェイルセーフで進行
- ユーティリティ
  - .env 生成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ（utils.logging_setup）
  - process priority / cpu affinity 設定ユーティリティ（utils.process_priority）
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）

セットアップ手順
----------------
1. Python 環境作成（推奨: 仮想環境）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要な依存パッケージをインストール
   - 本コードベースでは少なくとも以下が必要です:
     - duckdb
     - psutil
     - openai
   - 例:
     - pip install duckdb psutil openai
   - （プロジェクトに requirements.txt があればそれを利用してください）

3. プロジェクトルートに移動して .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 手動編集の場合は .env.example を参考に .env を作成してください。
   - 自動読み込み:
     - 起動時に .env / .env.local が自動ロードされます（OS 環境変数が優先）。
     - 自動ロードを無効にする場合:
       - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. 設定検証
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合は --strict を付与:
     - python -m kabusys.validate_config --strict

5. データディレクトリやログディレクトリの準備（通常は起動時に自動作成されます）
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - PID / kill flag: data/execution.pid, data/kill.flag
     - ログ: logs/<app_name>.log

主要な環境変数（主なもの）
-------------------------
- 必須
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabuステーション API パスワード）
- 実行環境
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- データベース / ファイル
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
  - PID_FILE_PATH（デフォルト data/execution.pid）
  - KILL_FLAG_PATH（デフォルト data/kill.flag）
- ログ
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
  - LOG_DIR（デフォルト logs/）
- Paper Trading 固有
  - PAPER_FILL_MODE（instant / partial / never / reject、デフォルト instant）
- Monitoring 関連
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60）
- OpenAI
  - OPENAI_API_KEY（ai.news_nlp / ai.regime_detector で利用）

起動方法（よく使うコマンド）
---------------------------
- ExecutionEngine 起動（通常はサービスとしてデーモン化して実行）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録
    - 起動時に data/stop_requested.flag が存在すると起動を中止
    - 停止は data/stop_requested.flag を作るか、ExecutionEngine の Kill Switch（data/kill.flag）で行う

- Monitoring 起動（ポーリングを行う）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 停止: data/stop_requested.flag を作成または Ctrl+C

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があると exit code 1 になる

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

停止 / Kill Switch
------------------
- 単純な停止フラグ:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが停止します（両スクリプトとも同様に監視）。
- Kill Switch（安全停止）
  - リスク基準（ドローダウン超過やポジション数上限超過）を満たすと監視モジュールが data/kill.flag に理由を書き込みます。
  - ExecutionEngine は起動時に kill_flag を確認し、自動クリア設定に応じて動作します（設定: KILL_FLAG_CLEAR_ON_START）。

ログ
----
- 共通ログ設定ユーティリティが用意されています（kabusys.utils.logging_setup.setup_logging）。
- ログは標準出力（stdout）と日次ローテートされるファイル（logs/<app_name>.log）へ出力されます。
- ログレベルは LOG_LEVEL または引数から設定可能。

簡単な運用フロー（例）
---------------------
1. .env を作成（config_setup）→ 設定検証（validate_config）
2. DuckDB / SQLite の初期化は起動時に自動で行われます（init_monitoring_db は冪等）
3. まず monitoring を起動して監視を開始:
   - python -m kabusys.run_monitoring
4. 別プロセスで execution を起動:
   - python -m kabusys.run_execution
5. 問題発生時は監視が kill.flag を書き込み、必要に応じて手動で停止フラグを作成して各プロセスを終了

ディレクトリ構成（概略）
----------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/               — 発注エンジン関連（Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — 監視 DB 初期化 / ラッパー
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 発注ログ・滞留検知など（該当ファイル参照）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - alert_manager.py       — 通知管理（LINE 等、存在する場合）
  - portfolio/
    - portfolio_builder.py   — 候補選定・スコア順ソート等
    - position_sizing.py     — 株数計算ロジック
    - risk_adjustment.py     — セクター制限・レジーム調整
  - research/
    - factor_research.py     — Momentum/Volatility/Value ファクター計算
    - feature_exploration.py — IC・統計サマリ等
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py     — 市場レジーム判定（ma200 + マクロセンチメント）
  - monitoring/              — 監視関連（上記）
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成
  - data/                    — 実行時生成ファイル（DB, pid, flags 等）
  - logs/                    — ログ出力先（デフォルト）

補足 / 注意点
-------------
- 本プロジェクトは実トレード機能を含むため、KABUSYS_ENV=live の設定時は実際に発注が行われます。API キーやパスワード、Kill Switch の設定などを十分に確認してください。
- .env は絶対にバージョン管理にコミットしないでください（config_setup でもその旨の注意文を出力します）。
- OpenAI API 呼び出し部分はコストとレイテンシに注意してください（リトライやバッチ化処理が組み込まれていますが、API キーの利用状況に依存します）。
- DuckDB / SQLite のテーブル構成やカラムの互換性確保のため、init_monitoring_db はマイグレーション的な処理（存在しないカラムの追加）を行いますが、重大なスキーマ変更は慎重に扱ってください。

お問い合わせ / 開発
-------------------
- 開発者向け: 各モジュールは比較的小さな責務に分かれているため、ユニットテストの追加や個別モジュールの差し替え（例: OpenAI 呼び出しのモック化）を行いやすく設計されています。
- 変更を加える際は、まず validate_config を実行して環境設定に問題がないか確認してください。

以上が主要な導入・運用ガイドです。必要であれば、起動例や設定ファイル（.env.example / config/*.yaml）の具体的なテンプレート、よくあるトラブルシュートを別途作成します。どの情報を追加しますか？