KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買／研究／監視を目的とした Python パッケージです。本リポジトリには以下の主要機能を備えています。

- 発注エンジン（ExecutionEngine）およびペーパートレード実行（MockBroker）
- システム監視（SystemMonitor）・注文／リスク監視（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算（Portfolio モジュール）
- リサーチ（ファクター計算・特徴量解析）
- ニュース NLP（OpenAI を用いたセンチメント評価）
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

この README ではセットアップ手順、使い方、主要機能、ディレクトリ構成を日本語でまとめます。

主な機能
--------
- Execution
  - 実際のブローカークライアント / ペーパートレード用 MockBroker を切り替えて実行可能
  - リスク管理（Position limit、Drawdown、Rate limit 等）
  - 注文ログの永続化（SQLite / DuckDB）
- Monitoring
  - システムリソース（CPU/メモリ/ディスク）・プロセス状態・データ鮮度の監視
  - 注文ログ / リスクログの永続化とアラート連携
  - Kill Switch（特定条件で data/kill.flag を書き込み Execution を停止）
- Portfolio
  - 銘柄候補選定、スコア／等ウェイトの算出、ポジションサイズ決定（lot 単位丸め等）
  - セクター上限やレジーム乗数によるリスク調整
- Research
  - Momentum, Volatility, Value 等のファクター計算（DuckDB を利用）
  - 将来リターン、IC（Information Coefficient）や統計サマリー
- AI
  - ニュース記事のセンチメントを OpenAI API でスコア化（ai_scores テーブルへ）
  - 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ツール
  - .env 対話ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

前提 / 必要環境
---------------
- Python >= 3.10
- 必須ライブラリ（例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config YAML の検証に用いるが必須ではない）
- SQLite は Python 標準ライブラリで使用します。

セットアップ手順
----------------
1. リポジトリをクローン、またはソースを配置します（仮にプロジェクトルートを KabuSys とする）。
2. 仮想環境を作成・アクティベートし、依存パッケージをインストールします（requirements.txt が存在する場合はそれを使用）:

   - 例（手動インストール）:
     pip install duckdb psutil openai PyYAML

3. .env の準備:
   - 対話式ウィザードを使うのが簡単です:
     python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - デフォルトのファイル保存先はプロジェクトルートの .env。デフォルト値や説明はウィザードで表示されます。

4. 設定検証（任意）:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

ログ / データファイル
--------------------
- ログ
  - デフォルト出力先: logs/
  - アプリ名ごとに日次ローテーションされたログファイルが作成されます（例: logs/execution.log, logs/monitoring.log）
  - LOG_DIR 環境変数で変更可能
- DB
  - DuckDB（分析用）: data/kabusys.duckdb（環境変数 DUCKDB_PATH）
  - SQLite（監視用）: data/monitoring.db（環境変数 SQLITE_PATH）
  - Paper Trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時は専用 DB を使用、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

使い方（実行例）
----------------

- 監視ループを起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を設定（デフォルト 60 秒）
  - 実行:
    python -m kabusys.run_monitoring
  - 停止:
    - プロセスに Ctrl+C（KeyboardInterrupt）
    - またはプロジェクトルートの data/stop_requested.flag を作成すると安全にループを終了します
  - 監視は常に「本番」SQLite パス（Settings.sqlite_path）を参照します（KABUSYS_ENV に依らず）。

- 発注エンジンを起動（Execution）
  - KABUSYS_ENV による挙動:
    - development: 開発用（シグナルは生成するが発注なし等、実装依存）
    - paper_trading: MockBrokerClient を使用し、Paper Trading 専用 DB（data/paper_trading.db）に記録
    - live: 実ブローカーを使用（実際に発注されます）
  - 実行:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    または
    python -m kabusys.run_execution  （環境変数で KABUSYS_ENV を設定）
  - 停止:
    - data/stop_requested.flag を作成するとエンジンを停止します
    - KillSwitch による停止: monitoring コンポーネントが条件を満たすと data/kill.flag を書き込み、エンジンはこれを検出して停止します
  - PID ファイル: data/execution.pid（ExecutionEngine 起動時に PID が記録されます）

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- .env ウィザード（初期設定）:
  python -m kabusys.config_setup

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で DB パスを直接指定可能。環境変数 PAPER_TRADING_SQLITE_PATH での指定も可。

主要な環境変数（抜粋）
--------------------
- 必須/重要
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
  - OPENAI_API_KEY: OpenAI を用いる場合に必要（AI 機能）
- データパス・ログ
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_DIR: ログの出力ディレクトリ（デフォルト: logs/）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/…、デフォルト INFO）
- 監視関連
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- Paper Trading 挙動
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）

停止フラグ / Kill Switch
-----------------------
- data/stop_requested.flag:
  - run_monitoring と run_execution はこのファイルの存在を監視し、存在すればループを終了・安全停止します（外部からの停止指示用）。
- data/kill.flag:
  - Monitoring の KillSwitch が条件（例: drawdown 超過やポジション上限超過）を満たすと作成され、ExecutionEngine に停止シグナルを送ります。
  - KillSwitch は冪等に動作し、既存の kill.flag がある場合は再書き込みしません。

開発者向けメモ / 実装ノート
-------------------------
- .env の自動ロード:
  - プロジェクトルートに .env / .env.local があれば自動で読み込みます（ただし OS 環境変数は保護され、.env.local は上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト時に便利）。
- ロギング:
  - 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を起動スクリプトから呼び出してログを統一管理しています。
  - 日次ローテーション・30世代保持。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は起動時にテーブル作成 / 必要カラム追加（簡易マイグレーション）を行います。
- AI 周り:
  - kabusys.ai.news_nlp / kabusys.ai.regime_detector は OpenAI API を使用します。API 呼び出しはリトライや JSON バリデーション等の堅牢化処理を含んでいます。
- Research:
  - DuckDB 接続を受け取り SQL + Python でファクター計算を行います。外部 API へアクセスしない設計です。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys をルートとした構成を抜粋）

- kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings
  - config_setup.py        — .env 対話ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_monitoring.py      — システム監視プロセス起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py     — ログ設定ユーティリティ
    - process_priority.py  — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py     — SQLite 永続層（テーブル定義・CRUD）
    - system_monitor.py    — システム状態・データ鮮度監視
    - trade_monitor.py     — 注文ログ監視（ファイル省略）
    - risk_monitor.py      — ドローダウン等の監視
    - kill_switch.py       — Kill Switch（kill.flag の書き込み）
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py     — （アラート送信ロジック、ファイル省略）
  - execution/             — ExecutionEngine 系（ファイル省略）
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
  - tools/
    - paper_verification_report.py

ライセンス / 注意事項
--------------------
- .env は機密情報（API トークン等）を含みます。絶対に Git にコミットしないでください（config_setup も README にその旨を記載しています）。
- 本番運用（KABUSYS_ENV=live）時は設定値（特に KILL_FLAG_CLEAR_ON_START 等）を十分に注意して確認してください。
- 実口座での発注は取り返しのつかない損失を招く可能性があります。必ずペーパートレードでの検証・監査を行ってください。

お問い合わせ / 開発
-------------------
- 開発者向けにコード内に説明コメントが多数含まれています。新しい設定を追加した場合は config.py と config_setup.py、validate_config.py を併せて更新してください。
- テストや CI に使う場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を適切に設定してください。

以上が KabuSys の概要と使い方です。必要であれば、README にサンプル .env のテンプレートやよくあるトラブルシュート（例: ログディレクトリ権限、psutil の権限エラー）を追加しますか？