# KabuSys — 日本株自動売買システム

このリポジトリは、日本株向けの自動売買・リサーチ・監視ユーティリティ群をまとめた Python パッケージです。  
本 README はコードベース（src/kabusys 以下）を元に、日本語での概要・セットアップ・使い方・ディレクトリ構成をまとめたものです。

注意: これは実運用向けのシステム設計とコード群を含みます。実際に live 環境で使う場合は設定や権限、テストを十分に行ってください。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要 CLI / スクリプト）
- 環境変数・設定の説明（主要項目）
- 実行時の停止・フラグの扱い
- ディレクトリ構成（ファイル一覧と簡単な説明）

---

プロジェクト概要
- KabuSys は日本株自動売買システムの構成要素（ExecutionEngine、Monitoring、Portfolio構築、Research、AI連携など）を含むライブラリ／実行スクリプト群です。
- DB: Airtable 等はなく、分析には DuckDB、監視・トレードログ等の永続化には SQLite を使用します。
- 本番（live）／ペーパートレード（paper_trading）／開発（development）を環境変数 KABUSYS_ENV により切り替え可能。paper_trading 時はブローカーは MockBrokerClient を使い、本番 DB とは分離された paper_trading 用 SQLite を使用します。

主な機能一覧
- ExecutionEngine 起動（run_execution.py）
  - ブローカークライアントの生成、オーダー管理、リスク管理、調整（Reconciler）、発注処理を行うエンジン起動スクリプト。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録。
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor, TradeMonitor, RiskMonitor を定期ポーリングして system_status、trade_logs、risk_logs、dashboard 等を更新。
  - KillSwitch に基づく ExecutionEngine 停止（kill.flag）機能やアラート送信のフック。
- 設定管理
  - Settings クラス（kabusys.config）で環境変数を集約。自動で .env / .env.local を読み込む仕組みあり（無効化可）。
  - 対話式 .env 作成ウィザード（kabusys.config_setup）。
  - 設定検証 CLI（kabusys.validate_config）。
- Portfolio 構築（kabusys.portfolio）
  - 候補選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数など純関数群。
- Research（kabusys.research）
  - DuckDB を使った因子計算（モメンタム、ボラティリティ、バリュー等）・特徴量解析・IC 計算。
- AI モジュール（kabusys.ai）
  - ニュースの NLP センチメント（OpenAI を利用）と市場レジーム判定（regime_detector）。
  - OpenAI API キーを使用。API 呼び出しはリトライ／フォールバックを備える実装。
- ツール
  - Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）。
- 共通ユーティリティ
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（kabusys.utils.process_priority）
  - Monitoring DB 永続層（kabusys.monitoring.monitoring_db）

---

セットアップ手順（ローカル開発・検証向け）
1. Python 環境
   - Python 3.10+ を推奨（型注釈や pathlib を多用）。
   - 仮想環境作成（推奨）
     - python -m venv .venv
     - source .venv/bin/activate  または  .venv\Scripts\activate

2. 必要パッケージのインストール（最低限）
   - duckdb
   - psutil
   - openai
   - （オプション）PyYAML（validate_config が config/*.yaml を検証する場合）
   例:
     pip install duckdb psutil openai PyYAML

   ※requirements.txt は本リポジトリには含まれていないため、上記を個別にインストールしてください。

3. .env の作成
   - 対話式ウィザードで作る（推奨）:
     python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考に .env を作成してください（.env は Git にコミットしないこと）。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     python -m kabusys.validate_config --strict

5. データディレクトリ作成
   - デフォルトの DB / PID / フラグファイル等は data/ 下に作成されます。必要に応じて .env でパスを変更してください。

---

主要な使い方（コマンド例）
- 環境変数設定（例）
  - KABUSYS_ENV=development
  - JQUANTS_REFRESH_TOKEN=...
  - KABU_API_PASSWORD=...
  - OPENAI_API_KEY=...（AI 機能を使う場合）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB パス、必要なら設定）
  - LOG_LEVEL=INFO
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db

- 対話式 .env 作成
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番／ペーパートレード切替は KABUSYS_ENV で）
  python -m kabusys.run_execution
  動作:
    - 起動時にプロセス優先度を high に設定
    - SQLite / DuckDB に接続
    - paper_trading 環境では MockBrokerClient を使用し paper_trading 用 DB に記録
    - data/stop_requested.flag が存在すれば起動せず終了
    - 実行中に data/stop_requested.flag を検出するとエンジンに stop を送って終了

- Monitoring 起動（ポーリング）
  python -m kabusys.run_monitoring
  動作:
    - プロセス優先度を high に設定
    - Settings に従い sqlite_path（監視 DB）と duckdb を接続
    - SystemMonitor 等を初期化してポーリング
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）
    - data/stop_requested.flag を検出するとループ終了

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db もしくは 環境変数 PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db

- AI 関連（プログラム的に）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡すと、raw_news を集計して OpenAI に送信、ai_scores テーブルへ書き込む。
    - api_key を渡さない場合は環境変数 OPENAI_API_KEY を参照。

---

環境変数・設定（主要項目）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: PID ファイルや Kill Switch の挙動に関する設定

設定の自動読み込み
- .env / .env.local がプロジェクトルートにあれば自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

注意点（運用上のポイント）
- run_execution は起動時に data/stop_requested.flag があれば起動しないため、手動制御が可能です。
- Kill Switch 機能により、RiskMonitor が閾値を超えると data/kill.flag に理由を書き込み、ExecutionEngine 停止をトリガーします。KILL_FLAG_CLEAR_ON_START=1 に注意（本番では 0 推奨）。
- run_monitoring は環境にかかわらず本番 sqlite_path を使用して監視ログを保持します（意図的設計）。
- AI 呼び出し（OpenAI）には API キーとネットワークが必要。失敗時はフォールバック動作（0.0 スコア等）で安全に継続する設計です。

停止・フラグファイル
- data/stop_requested.flag: run_execution / run_monitoring が参照する停止トリガーファイル
- data/kill.flag: KillSwitch が書き込む停止フラグ（Execution 停止要求）
- data/execution.pid: ExecutionEngine の PID 格納先（設定で上書き可）

---

ディレクトリ構成（src/kabusys の主なファイルと役割）
- __init__.py
  - バージョンとパッケージエクスポート定義

- run_execution.py
  - ExecutionEngine 起動スクリプト（スレッドでエンジン実行、stop フラグ監視）

- run_monitoring.py
  - Monitoring ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で調整可）

- config.py
  - Settings クラス：環境変数の読み込み、デフォルト値、バリデーション

- config_setup.py
  - 対話式 .env 作成ウィザード

- validate_config.py
  - .env と config/*.yaml の事前検証ツール

- utils/
  - logging_setup.py : ログ初期化（console + 日次ローテーションファイル）
  - process_priority.py : プロセス優先度／CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py : SQLite に保存するスキーマと DB ラッパー（MonitoringDB）
  - system_monitor.py : システム（CPU/Mem/Disk/データ鮮度/プロセス生存）監視
  - trade_monitor.py : （コード内に含まれた）注文関連監視ロジック
  - risk_monitor.py : ドローダウン・ポジション上限監視
  - kill_switch.py : Kill Switch 書き込みロジック
  - monitoring_engine.py : 各 Monitor を束ねるエンジン
  - alert_manager.py : アラート送信の抽象（実装箇所を参照）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - （実際のエンジン、発注・リスク管理・ブローカー抽象を含む）

- portfolio/
  - portfolio_builder.py : 候補選定・重み計算
  - position_sizing.py : 発注株数計算・集約上限調整
  - risk_adjustment.py : セクター上限・レジーム乗数

- research/
  - factor_research.py : モメンタム／ボラティリティ／バリュー等の因子計算（DuckDB）
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー

- ai/
  - news_nlp.py : ニュースを LLM に投げて銘柄毎センチメントを ai_scores に書き込む
  - regime_detector.py : ETF MA とマクロニュースを組み合わせて市場レジームを判定

- tools/
  - paper_verification_report.py : ペーパートレード検証レポート出力ツール

---

開発・運用時の補足
- DB マイグレーションは簡易にコード内で行われる（monitoring_db.init_monitoring_db がカラム追加等を実施）。
- ログはデフォルト logs/ に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみとなります。
- Process priority / CPU affinity の操作は OS 権限に依存します。権限不足の場合は警告を出してスキップします。
- OpenAI / 外部 API を使用する機能はネットワーク依存であり、API 呼び出し失敗時のフォールバックロジックを備えていますが、実運用では API 利用上限やコスト管理に注意してください。

---

よく使うコマンドまとめ（例）
- 仮想環境作成・依存インストール:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai PyYAML

- .env 作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Monitoring 起動:
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Execution 起動:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの現状（src/kabusys 内の実装）を要約したものです。モジュールの詳細な利用方法や拡張、API の内部仕様は各ファイルのドキュメント文字列（docstring）やソースコードを参照してください。質問や追加で README に含めたい内容があれば教えてください。