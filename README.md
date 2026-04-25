KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買および運用監視を行うためのモジュール群です。本リポジトリは次の機能を持ちます。

- 発注エンジン（ExecutionEngine）と監視プロセス（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- AI ベースのニュースセンチメント評価・市場レジーム判定（OpenAI API）
- ペーパートレード用の分離された DB と検証レポート生成ツール
- ログ・環境設定ユーティリティ、設定検証・ウィザード

主要な設計方針
- 本番環境とペーパートレードは DB を分離（paper_trading 環境）。
- ルックアヘッドバイアス防止のため、日付処理は外部依存を避ける設計。
- OpenAI や外部 API 呼び出しは失敗時にフォールバックして安全に継続。
- ログは統一的に設定され、日次ローテーションを行う。

主な機能一覧
----------------
- 実行関連
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV によるペーパートレード切替対応。
- 監視関連
  - run_monitoring.py: SystemMonitor ポーリングループ起動。リソース監視・データ鮮度検査等。
  - monitoring/*: RiskMonitor、TradeMonitor、KillSwitch、MonitoringEngine、DB 永続化層 等。
- ポートフォリオ構築
  - portfolio/*: 候補選定、等ウェイト・スコア加重、リスク調整、ポジションサイズ計算。
- 研究 / 分析
  - research/*: ファクター計算（mom/vol/value）、将来リターン、IC 計算、統計サマリ等（DuckDB を利用）。
- AI
  - ai/news_nlp.py: OpenAI を用いたニュースセンチメント評価（ai_scores への書き込み）。
  - ai/regime_detector.py: マクロニュース＋ETF MA を合成した市場レジーム判定と永続化。
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成（期間指定可能）。
- ユーティリティ
  - config.py: 環境変数 / .env 自動読み込み・Settings クラス。
  - config_setup.py: 対話式 .env 作成ウィザード。
  - validate_config.py: 起動前チェック（必須環境変数や config/*.yaml の検証）。
  - utils/logging_setup.py: 共通ログ設定。
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定。

セットアップ手順
----------------

前提
- Python 3.10+ を推奨（型アノテーションに | 記法を使用）。
- Git などでリポジトリを取得済みであること。

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要なパッケージをインストール
   - 基本的に次を入れておくと良いです（プロジェクト固有の requirements.txt があればそちらを使用してください）:
     - duckdb
     - psutil
     - openai
     - pyyaml（validate_config の YAML 検証を有効にするための任意依存）
   例:
   - pip install duckdb psutil openai pyyaml

3. .env の作成
   - 対話形式で作る（推奨）:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成し、必要な環境変数を設定します（下記「重要な環境変数」を参照）。

4. 設定検証
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けて警告も失敗扱いにできます:
     - python -m kabusys.validate_config --strict

5. ディレクトリ（data / logs）を確認
   - ログはデフォルト logs/ に出力されます。必要なら .env の LOG_DIR で変更可能。
   - data/ 以下に DB ファイルや pid/flag ファイルを格納します（自動作成される場合もありますが、パーミッション等を確認してください）。

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。省略時は development。
  - paper_trading の場合は MockBrokerClient を使い、別 DB（PAPER_TRADING_SQLITE_PATH）に記録する。
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- LOG_DIR: ログ保存ディレクトリ
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行・監視に関する設定
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（実行例）
----------------

1) 環境ファイル作成・検証
- python -m kabusys.config_setup
- python -m kabusys.validate_config

2) 監視プロセスの起動
- 簡単起動:
  - python -m kabusys.run_monitoring
- ポーリング間隔を変更する:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 備考:
  - run_monitoring は Settings.sqlite_path（本番用 sqlite_path）を使用します（監視ログは本番 DB を想定）。
  - 停止はプロジェクトルートの data/stop_requested.flag を作成することで次のポーリングで検出して終了します。

3) 実行エンジン（ExecutionEngine）の起動
- 通常（development / live / paper_trading に応じて動作が変わります）:
  - python -m kabusys.run_execution
- ペーパートレード実行例:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ペーパートレード時は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
- 停止:
  - data/stop_requested.flag を作成するとエンジンは安全に停止します。
  - また Monitoring の KillSwitch によって data/kill.flag が書き込まれると ExecutionEngine は停止シグナルとして扱います（詳細は監視設定参照）。

4) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

5) AI 関連（プログラム的利用）
- ai.score_news（ニュース NLP）や ai.regime_detector.score_regime は DuckDB 接続と target_date を与えて呼び出します。OpenAI API キーは OPENAI_API_KEY を環境変数に設定してください。

停止 / Kill Switch の仕組み
- run_execution/run_monitoring は project_root/data/stop_requested.flag を監視しているため、手動でこのフラグを作ることで停止できます。
- Monitoring 側には KillSwitch があり、RiskMonitor 等で条件を満たすと data/kill.flag に理由を書き込み、ExecutionEngine に停止を促します。kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START 設定で制御します（本番では自動クリアを無効化することを推奨）。

ログ
----
- デフォルト: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）。
- ログは日次ローテーションで 30 日分保持されます。
- LOG_DIR 環境変数でログ保存先を変更可能。

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 以下の主な構成です（抜粋）:

- kabusys/
  - __init__.py
  - config.py                 # 環境変数管理（Settings）
  - config_setup.py           # .env 対話式ウィザード
  - validate_config.py        # 設定検証 CLI
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - run_monitoring.py         # Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (警告管理等: 実装に依存)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のリポジトリはさらに細かいモジュール群が含まれます。上は代表的なファイルの一覧です）

補足 / 運用上の注意
------------------
- KABUSYS_ENV=live のときは本番口座に対する発注が行われます。設定（LINE 通知等）・ kill スイッチの有効性を必ず事前に確認してください。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup も同旨を出力します）。
- OpenAI を利用する機能は API 呼び出し回数・コストに注意してください（バッチ化・トークン上限対策が実装済み）。
- DuckDB / SQLite ファイルは定期的にバックアップを推奨します。
- psutil 等でプロセス優先度や CPU affinity を操作します。権限不足で設定に失敗することがあります（警告ログが出ます）。

問い合わせ / 開発メモ
-------------------
- 開発環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的な .env の読み込みを抑止できます（テスト等で便利）。
- validate_config.py は起動前チェックとして CI に組み込むことを推奨します。
- 各モジュールの詳細な使用方法はソース内 docstring に記載しています。必要な場合は該当モジュールの docstring を参照してください。

以上。システムの各コンポーネントを安全に起動・停止し、まずは .env を作成して validate_config で確認することをお勧めします。必要であれば README にサンプル .env（プレースホルダ）や運用チェックリストを追記します。どの情報が欲しいか教えてください。