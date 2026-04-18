KabuSys — 日本株自動売買システム
=================================

本ドキュメントはこのリポジトリ（src/kabusys）に含まれる主要なスクリプト・モジュールの概要、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめた README です。

プロジェクト概要
--------------
KabuSys は日本株の自動売買・バックテスト・モニタリングを目的としたシステムです。  
主な責務は以下のとおりです。

- 相場データ・財務データに基づくファクター計算・シグナル生成（research）
- ポートフォリオ構築・銘柄選定・ポジションサイズ計算（portfolio）
- 発注エンジン（ExecutionEngine）とブローカークライアント抽象化（execution）
- システム・注文・リスク監視（monitoring）
- ニュースを LLM で解析する AI モジュール（ai）
- 運用補助ツール（tools）

バージョン
---------
パッケージバージョンは kabusys.__version__ = "0.1.0" です。

主な機能一覧
-------------
- 環境設定ウィザード（config_setup.py）で .env を対話的に作成/更新
- 設定検証 CLI（validate_config.py）で .env や config/*.yaml の基本チェック
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い paper_trading DB に分離
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）で安全停止
- 監視（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして監視ログを SQLite に保存
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き可（デフォルト 60 秒）
- モニタリング DB 層（monitoring_db.py）: system_status / trade_logs / positions / risk_logs / dashboard
- Risk モニタ（risk_monitor.py）: ドローダウン・ポジション上限の検知・アラート記録・Kill Switch 書込み
- AI:
  - news_nlp.score_news(): raw_news を LLM（OpenAI）でセンチメントし ai_scores に書き込み
  - regime_detector.score_regime(): ETF を用いた MA 指標 + マクロニュース LLM を合成して日次レジーム判定
- ツール:
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成
- 研究用ユーティリティ（research）: ファクター計算、IC 計算、特徴量サマリ
- ポートフォリオ構築（portfolio）: 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数

セットアップ手順
----------------
以下はローカルで動かすための一般的な手順の例です。

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低依存例:
     - duckdb
     - psutil
     - openai
   - 検証で YAML を使う場合:
     - pyyaml
   - 例:
     - pip install duckdb psutil openai pyyaml

   （本リポジトリに requirements.txt が無い場合は上記を参考に追加してください）

4. .env の準備
   - 手動で .env を作成するか、対話ウィザードを実行:
     - python -m kabusys.config_setup
   - ウィザード実行後、設定を検証:
     - python -m kabusys.validate_config
     - --strict オプションを付けると警告も FAIL として終了します

5. データディレクトリ
   - デフォルトの DB / ログ パスは .env の指定または次のデフォルトです:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 必要に応じてディレクトリを作成してください（logging_setup が自動で作成を試みます）。

環境変数（主要）
----------------
主な環境変数（Settings で参照）:

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - paper_trading：MockBrokerClient を使用、DB を紙口座用に分離
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE（instant | partial | never | reject、デフォルト instant）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR（ログ保存先）
- KILL_FLAG_CLEAR_ON_START（0/1、デフォルト 0。本番で 1 は危険）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（1 にすると .env 自動読み込みを無効化）

使い方（起動コマンド例）
-----------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 動作: Settings に従って SQLite / DuckDB に接続しエンジンを起動します。
  - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。
  - 停止方法:
    - data/stop_requested.flag を作成すると実行ループが検知して安全停止します
    - Kill Switch（データ由来）で data/kill.flag が書き込まれると ExecutionEngine 停止対象

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用（環境に関わらず本番 DB を想定）

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを上書き可能（例: --db data/paper_trading.db）
  - 簡単な基準（稼働率、成功率、P95 レイテンシ等）に基づく PASS/FAIL レポートを出力

- AI モジュール（プログラムから呼び出す）
  - OpenAI API キー（OPENAI_API_KEY 環境変数）を設定してください。
  - 例: news_nlp.score_news を呼ぶ（Python スクリプトまたは REPL）
    - python -c "from kabusys.ai.news_nlp import score_news; import duckdb, datetime; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date(2026,4,1), api_key='YOUR_KEY'))"
  - regime_detector.score_regime も同様に呼べます。戻り値は書き込み結果等のステータス。

ログ
----
- setup_logging() が提供され、全起動スクリプトはこれを利用して統一的なログ出力を行います。
- デフォルトは logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、30日保持）。
- コンソール出力は stdout に出ます（cron 等での扱いを想定）。

停止・Kill フラグ
-----------------
- run_execution/run_monitoring はプロジェクトの data/stop_requested.flag（または Settings.kill_flag_path の kill.flag）を監視して停止します。
- KillSwitch（monitoring/kill_switch.py）はリスク条件（ドローダウンやポジション上限）を満たしたときに kill.flag を書き、ExecutionEngine に停止シグナルを送る設計です。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要なファイルと簡易説明です。

- __init__.py
  - パッケージ宣言・バージョン

- config.py
  - Settings クラス: 環境変数・.env の読み込みとプロパティ提供
  - 自動 .env ロード機能（プロジェクトルート検出）

- config_setup.py
  - .env 作成・更新の対話式ウィザード

- validate_config.py
  - 起動前の設定検証 CLI

- run_execution.py
  - ExecutionEngine の起動スクリプト（スレッドで実行、stop/flag 監視）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）

- monitoring/
  - monitoring_db.py: SQLite テーブル初期化・CRUD ラッパー（MonitoringDB）
  - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py: （コードベースに含まれる想定の監視ロジック）
  - risk_monitor.py: ドローダウン & position 上限監視
  - kill_switch.py: kill.flag 書込ロジック
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - alert_manager.py: （アラート送信の抽象化）

- execution/
  - execution_engine.py: ExecutionEngine 本体（起動・セッション管理）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    - 発注管理、DB リポジトリ、リスク制御、ブローカ抽象化等

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数算出、単元丸め、aggregate cap 調整
  - risk_adjustment.py: セクター制限、レジーム乗数

- research/
  - factor_research.py: Momentum/Value/Volatility ファクター計算（DuckDB を利用）
  - feature_exploration.py: 将来リターン、IC、統計サマリ

- ai/
  - news_nlp.py: ニュースの LLM センチメント集計と ai_scores への書き込み
  - regime_detector.py: MA + LLM による市場レジーム判定
  - __init__.py: score_news の公開（kabusys.ai.score_news）

- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成 CLI

- utils/
  - logging_setup.py: ログ設定ユーティリティ
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ

注意事項 / 運用上の留意点
------------------------
- 本番環境（KABUSYS_ENV=live）では設定値や kill フラグの扱いを慎重に設定してください（validate_config で警告を出します）。
- .env は秘密情報を含むため Git にコミットしないこと（config_setup でも案内があります）。
- AI 機能は OpenAI API を利用するため API キーが必要で、呼び出しコスト・レイテンシやエラーハンドリングを考慮して運用してください。
- DuckDB / SQLite のパスは Settings で変更可能です。ペーパートレードは本番 DB と完全分離することを想定しています。
- run_monitoring は監視用 DB に本番 sqlite_path を使います（環境にかかわらず本番 path を参照する設計）。

追加情報
--------
- 各モジュールの docstring に詳細な設計方針・アルゴリズム説明が含まれています。実装・拡張の際はそちらを参照してください。
- テストや CI を導入する場合、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env ロードを無効化すると環境依存を切りやすくなります。

お問い合わせ・貢献
-----------------
コードの説明不足や追加のドキュメントが必要な箇所があればお知らせください。Pull Request や Issue でのフィードバック歓迎します。

---  
以上。必要なら各コマンドの実行例や .env のサンプル（.env.example）を追記します。どの情報を追記しましょうか？