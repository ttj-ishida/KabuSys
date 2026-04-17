README
=====

プロジェクト概要
-----
KabuSys は日本株向けの自動売買・研究・監視を想定した Python コードベースです。  
主な目的は以下です。

- 株価データ解析（DuckDB を利用したファクター計算・研究）
- ポートフォリオ構築（銘柄選定・重み計算・ポジションサイズ決定）
- 実行エンジン（紙上・ペーパートレードおよび本番発注インターフェースを想定）
- ランタイム監視（システム稼働状況・注文滞留・リスク監視）とアラート送信
- AI 支援（ニュース NLP による銘柄センチメント、レジーム判定）
- ペーパートレード検証レポート生成

機能一覧
-----
主要な機能（抜粋）:

- 環境設定ウィザード: .env を対話式に生成/更新（kabusys.config_setup）
- 設定検証 CLI: 必須環境変数や設定ファイルのチェック（kabusys.validate_config）
- 実行エンジン起動スクリプト: run_execution（KABUSYS_ENV による paper/live 切替）
- 監視ループ起動スクリプト: run_monitoring（定期ポーリングで監視ログ記録）
- 監視コンポーネント:
  - SystemMonitor: CPU/メモリ/Disk、データ鮮度、実行プロセス検出
  - TradeMonitor: 注文滞留（stale order）、約定価格異常の検出
  - RiskMonitor: ドローダウン／ポジション上限監視、ダッシュボード更新
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書込み・LINE 通知
- データ永続化（SQLite）: monitoring_db モジュールによりテーブルを自動作成・マイグレーション
- 研究モジュール（DuckDB 経由）:
  - ファクター計算（モメンタム、ボラティリティ、バリューなど）
  - 将来リターン、IC 計算、統計サマリ
- ポートフォリオ構築:
  - 候補選定、等重/スコア重み、ポジションサイズ計算（lot 単位、リスク制限、集約キャップ）
  - セクター上限適用、レジーム乗数
- AI モジュール:
  - news_nlp: OpenAI によるニュースセンチメント（ai_scores テーブルへ書込）
  - regime_detector: MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ツール:
  - paper_verification_report: ペーパートレードログを集計して PASS/FAIL レポート生成

前提 / 必要要件
-----
推奨 Python バージョン: 3.10 以上（型ヒントに union 型などを使用）  
主な依存ライブラリ（プロジェクトに requirements.txt は含まれていませんが、少なくとも以下が必要です）:

- duckdb
- psutil
- openai
- requests
- PyYAML （config 検証の YAML パースで任意）

セットアップ手順
-----
1. レポジトリをクローンしてワークディレクトリに入る（パッケージは src 配下を想定）。
2. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows の場合は .venv\Scripts\activate）
3. 依存ライブラリをインストール:
   - pip install duckdb psutil openai requests pyyaml
   - （必要に応じてバージョンを固定する）
4. 環境変数の設定:
   - 対話式で .env を生成する場合:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - その他の主要環境変数（省略可／デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - OPENAI_API_KEY — news_nlp / regime_detector で必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager 用（任意）
     - LOG_LEVEL — default: INFO
     - PAPER_FILL_MODE — paper_trading の MockBroker 動作モード（instant/partial/never/reject）
5. 設定の確認:
   - python -m kabusys.validate_config
   - 問題があれば --strict で警告もエラー扱いにできます。

運用上のファイル / フラグ
-----
- data/stop_requested.flag — run_monitoring / run_execution の外部停止フラグ。存在するとループを終了します。
- data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine に停止シグナルを送る目的）。
- data/execution.pid — 実行エンジンの PID を記録するために使用（system monitor が存在確認する）。

使い方（コマンド例）
-----
- 環境ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - 本番または開発モードを指定して起動:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - paper_trading の場合、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に完全分離して記録されます。
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI モジュール呼び出し（プログラム内利用）:
  - from kabusys.ai import score_news
  - score_news(conn, target_date)  # OPENAI_API_KEY または引数で API キーを渡す
  - regime_detector.score_regime(conn, target_date) も同様

設定値の挙動・注意点
-----
- .env 自動読み込み:
  - パッケージロード時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から .env/.env.local を読み込みます。
  - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB パス:
  - 監視用 SQLite は Settings.sqlite_path（デフォルト data/monitoring.db）。
  - DuckDB は Settings.duckdb_path（デフォルト data/kabusys.duckdb）。
  - paper_trading 時は paper_sqlite_path（デフォルト data/paper_trading.db）へ記録され、本番 DB と分離されます。
- Kill Switch:
  - RiskMonitor が一定条件（ドローダウン、ポジション上限等）を満たすと KillSwitch が data/kill.flag を書き込みます。ExecutionEngine はこのフラグで停止される設計です。
- 実行優先度:
  - run_* スクリプトは起動直後に set_process_priority("high") を試みます（psutil による OS レベルの設定。権限により失敗する場合あり）。

ディレクトリ構成（主要ファイル）
-----
src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 簡易 CLI による設定検証
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト（paper_trading は MockBroker 使用）
- monitoring/
  - monitoring_db.py — SQLite テーブル作成・MonitoringDB クラス（ログ保存用）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE push 通知（requests を使用）
- execution/ (実行関連コンポーネントの参照あり: Engine, BrokerFactory 等 — 一部はここにある想定)
  - order_repository.py, order_manager.py, reconciler.py, risk_manager.py, execution_engine.py (参照元あり)
- portfolio/
  - portfolio_builder.py — 候補選定、重み計算
  - position_sizing.py — 株数計算・集約キャップ
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー等の計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — MA200 + マクロセンチメントでレジーム判定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- その他（execution, data, strategy, etc. は設計上存在する想定）

開発・運用上の注意
-----
- .env は機密情報を含むため絶対に Git 等にコミットしないこと。
- OpenAI API キーを扱う場合、API 呼び出し失敗時はフェイルセーフ（デフォルトのスコアや 0.0）で続行する実装が多く組み込まれていますが、課金や遅延の影響に注意してください。
- monitoring DB（SQLite）は冪等に初期化されます（init_monitoring_db）。既存 DB にスキーマ変更がある場合は簡易マイグレーションを含む処理がありますが、運用前にバックアップ推奨です。
- run_execution は paper_trading モードで本番 DB と完全分離します。ペーパートレードの検証やバックテストを行う際はこのモードを利用してください。

問い合わせ / 貢献
-----
コードの追加や不具合修正提案は Pull Request を送ってください。大きな設計変更を行う場合は Issue を立てて議論を開始してください。

以上。必要があれば README に「サンプル .env」「requirements.txt」「実行例のログ抜粋」などを追記します。どの情報を追加したいか教えてください。