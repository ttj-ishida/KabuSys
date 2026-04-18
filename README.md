README
=====

注意: この README はリポジトリ内のソースコードを参照して作成したドキュメントです。実行前に必ず .env を作成し、設定検証を行ってください。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買・研究フレームワークです。  
主要機能は次の通りです：

- 戦略のためのファクター計算・特徴量探索（DuckDB を利用したオフライン分析）
- ポートフォリオ構築（候補選定、重み計算、リスク調整、ポジションサイズ算出）
- ExecutionEngine（発注エンジン）：本番 / ペーパートレードの分離実行
- Monitoring（監視）：システム状態、注文、リスク（ドローダウン等）の定期監視とアラート／Kill Switch
- AI ユーティリティ：ニュース NLP による銘柄別センチメント・市場レジーム判定（OpenAI）
- 運用支援ツール：ペーパートレード検証レポート生成など
- 開発支援 CLI：.env 対話式作成ウィザード、設定検証 CLI

主な設計方針として、データ永続化は DuckDB（分析用） と SQLite（監視・ペーパー用）で分離し、外部 API 呼び出しは明示的に制御（OpenAI 等は API キー必須）されています。

機能一覧
--------
- 設定管理
  - .env の自動ロード（プロジェクトルートに基づく）
  - config_setup（対話式ウィザード）で .env を作成
  - validate_config で起動前に環境・設定ファイルの検証
- 実行系
  - run_execution: ExecutionEngine 起動（KABUSYS_ENV に応じて MockBroker を使用）
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 監視
  - system_monitor: CPU/メモリ/ディスク、Execution プロセス存否、データ鮮度を監視
  - trade_monitor: 注文の滞留・約定異常などを検知（trade_logs）
  - risk_monitor: ドローダウン・ポジション数の監視とログ記録
  - monitoring_engine: 上記をまとめて定期実行、Kill Switch 評価、AlertManager 経由で通知
  - monitoring_db: SQLite スキーマ管理・読み書き（冪等でテーブル作成・マイグレーション）
- ポートフォリオ構築
  - 候補選定（スコアソート）
  - 重み計算（等分／スコア加重）
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（lot 単位丸め、利用可能資金に基づくスケーリング等）
- 研究・分析
  - factor_research: Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC（スピアマンランク相関）など
- AI
  - news_nlp: OpenAI（gpt-4o-mini 等）でニュースを銘柄ごとにスコアリングして ai_scores へ格納
  - regime_detector: ETF の MA とマクロニュースセンチメントを合わせて市場レジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレード結果の検証レポート生成

必要条件（依存）
----------------
主要な Python ライブラリ（代表）：
- Python 3.9+（ソースは型ヒントを使用）
- duckdb
- psutil
- openai (AI 機能を利用する場合)
- sqlite3（標準ライブラリ）
- そのほか、PyYAML は設定ファイル（config/*.yaml）検証時に任意で使用

（プロジェクトに requirements.txt が無い場合は上のパッケージをインストールしてください。）

セットアップ手順
---------------
1. リポジトリをクローン / 展開
   - プロジェクトルートに移動してください（pyproject.toml または .git がある場所）。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install duckdb psutil openai
   - 必要に応じて PyYAML をインストール（validate_config の YAML 検証用）:
     pip install pyyaml

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     -> 対話に従って値を入力し .env を生成します。
   - 主要に設定すべき環境変数:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - KABUSYS_ENV （development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL, LOG_DIR など

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）になります。

環境変数の自動読み込みについて
------------------------------
- 起動時、プロジェクトルートが検出できれば .env を自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- .env.local が存在する場合は .env より優先して上書きされます。ただし OS の環境変数は保護されます。

重要な設定項目（抜粋）
--------------------
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- DUCKDB_PATH: DuckDB ファイルパス（分析用）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（Monitoring は常に sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 実行時のみ使用）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に既存 kill.flag を自動クリアするか（0/1）

使い方（主要コマンド）
--------------------

※ すべてプロジェクトルートで実行してください。

1) 実行エンジン（ExecutionEngine）起動
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid（デフォルト）を作成します。

2) 監視プロセス起動
- python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒です。環境変数 MONITOR_POLL_INTERVAL で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視プロセスは MonitoringDB（sqlite_path）と DuckDB を開き、SystemMonitor.check_once() を定期実行します。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成するか、Ctrl-C（KeyboardInterrupt）。

3) 設定ウィザード
- python -m kabusys.config_setup
  - 対話形式で .env を作成／更新します。

4) 設定検証
- python -m kabusys.validate_config [--strict]
  - 環境変数・DB パス・config/*.yaml の存在などをチェックします。

5) ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ等を評価して PASS/FAIL を出力します。

ログと監視
----------
- ログはデフォルトで logs/<app_name>.log に日次ローテーション（30 日保持）されます。LOG_DIR で変更可能。
- setup_logging() によりコンソール出力（stdout）も有効になります。
- Monitoring の DB（sqlite）は監視用テーブル（system_status, trade_logs, positions, risk_logs, dashboard）を self-contained に作成・マイグレーションします。

Kill Switch / 停止制御
---------------------
- KillSwitch はデータベースの監視結果（ドローダウンやポジション数超過等）により data/kill.flag を作成します。ExecutionEngine は起動時や実行中にこのフラグを検出すると停止します。
- 監視ループの強制停止にはプロジェクトルート/data/stop_requested.flag を用いる設計（run_execution/run_monitoring が参照）。

AI（OpenAI）関連
----------------
- news_nlp と regime_detector は OpenAI API（例: gpt-4o-mini）を利用します。利用には OPENAI_API_KEY が必要です。
- OpenAI 呼び出しはリトライ・バックオフやレスポンス検証（JSON mode）を実装し、失敗はフェイルセーフ（スコア 0 にフォールバック）で処理します。

開発者向けメモ
---------------
- DuckDB 接続を渡してファクター計算や AI スコアリング関数を呼び出せるため、研究用途に便利です。
- 多くのモジュールは DB へ書き込みを行う際にトランザクション（BEGIN / COMMIT / ROLLBACK）を使っています。テスト時はモックや一時 DB を利用してください。
- process_priority と logging のユーティリティが用意されており、起動スクリプト側で統一的に扱います。

ディレクトリ構成（抜粋）
-----------------------
リポジトリ内の主要ファイル・ディレクトリ構成（src/kabusys を基点）:

- src/kabusys/
  - __init__.py                     — パッケージ定義
  - config.py                       — 環境変数 / Settings 管理
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 起動前設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - utils/
    - logging_setup.py              — ログ設定ユーティリティ
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py              — SQLite スキーマ/読み書き層
    - system_monitor.py             — システム状態監視
    - trade_monitor.py              — 注文監視（別ファイル）
    - risk_monitor.py               — ドローダウン等のリスク監視
    - monitoring_engine.py          — 監視エンジン統合
    - kill_switch.py                — kill.flag 管理
    - alert_manager.py              — アラート送信（別ファイル）
  - execution/
    - execution_engine.py           — ExecutionEngine（別ファイル）
    - broker_factory.py             — ブローカークライアント生成（Mock を切替）
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
  - data/                            — 実行時に使用されるファイル群（logs/, sqlite ファイル等を想定）

補足 / 運用上の注意
------------------
- Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（監視 DB）を使用します。ペーパートレード用 DB は ExecutionEngine 側で分離されます（settings.is_paper を参照）。
- MONITOR_POLL_INTERVAL は秒数（正の整数）を期待します。無効な値はデフォルト 60 秒にフォールバックします。
- PAPER_FILL_MODE の有効値: instant | partial | never | reject
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0（無効）にすることを強く推奨します（誤って自動的に Kill Switch をクリアしないため）。

ライセンス / 貢献
-----------------
リポジトリに LICENSE があればそれに従ってください。バグ報告・Pull Request は受け付けます。

問い合わせ
----------
コード内のドキュメンテーション（関数 docstring）を優先して参照してください。特定機能について不明点があれば、問題点（Issue）を作成してください。

以上。