KabuSys — 日本株自動売買システム
================================

以下はこのコードベースの簡易READMEです。開発・運用に必要な概要、セットアップ、起動方法、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
---------------
KabuSys は日本株自動売買システムのコアライブラリ群です。主な目的は以下のとおりです。

- シグナル生成→ポートフォリオ構築→発注までの ExecutionEngine（本番 / ペーパートレード対応）
- システム稼働監視・アラート・Kill Switch（自動停止）機能
- ポートフォリオ構築・ポジションサイズ計算・リスク調整の純粋関数群
- ファクター計算や特徴量探索（DuckDB を用いた研究用モジュール）
- ニュースを LLM でスコアリングする AI モジュール（OpenAI 利用）
- 設定ウィザード / 設定検証ツール / ペーパートレード検証レポート生成ツール

主な機能一覧
-------------
- Execution
  - ExecutionEngine：ブローカクライアント・OrderManager・RiskManager を組み合わせて発注を行う
  - Paper trading モード：`KABUSYS_ENV=paper_trading` で MockBroker を使用し、`data/paper_trading.db` に記録して本番 DB と分離
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を統合した MonitoringEngine（ポーリング）
  - KillSwitch によるフラグファイル書き込みで Execution の自動停止
  - 監視ログの永続化（SQLite）
- Portfolio
  - 候補選定、等配分・スコア加重配分、リスク調整、ポジションサイジング（lot 単位対応）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリなど
- AI
  - ニュース NLP（OpenAI）で銘柄ごとにセンチメント（ai_score）を算出し DB に書込
  - レジーム判定（ETF ma200 + マクロセンチメントの融合）
- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（tools.paper_verification_report）

セットアップ手順
----------------
1. 前提
   - Python 3.10 以降を推奨
   - system パッケージ: psutil, duckdb, openai（AI機能を使う場合）など

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) / .venv\Scripts\activate (Windows)

3. 依存パッケージのインストール
   - requirements.txt があれば: pip install -r requirements.txt  
     （無い場合は少なくとも `psutil`, `duckdb`, `openai`, `PyYAML`（設定検証用） をインストール）

4. 初期設定 (.env) の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参照して .env を作成すること
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数の例:
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=（AIを使う場合）
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0（本番では 0 を推奨）

5. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード（警告を失敗扱いにする）: python -m kabusys.validate_config --strict

6. ディレクトリ作成（必要に応じて）
   - data/ と logs/ は自動作成されますが、権限等で失敗する場合は手動で作成してください

使い方（起動方法・運用）
-----------------------
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 動作:
    - `KABUSYS_ENV` が `paper_trading` の場合は MockBrokerClient を使い `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）へ記録して本番 DB と分離
    - 起動時に data/stop_requested.flag が存在する場合は起動を行わずに終了
    - 実行中に data/stop_requested.flag が作成されると安全に停止
    - Execution 用 PID ファイル: data/execution.pid（設定により変更可能）
    - Kill Switch（data/kill.flag）は Monitoring 側が書き込み、Execution 側はそれを検出して停止する（設定により起動時に自動クリア可能）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 動作:
    - 監視ループをポーリングして SystemMonitor.check_once() を定期実行
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）で上書き可能
    - 監視は常に本番 sqlite_path を使用（環境に依らず）
    - 停止: data/stop_requested.flag を作成するか Ctrl+C

- 停止・Kill Switch
  - KillSwitch が条件を満たすと `data/kill.flag` を書き込み、Execution に停止信号を送る
  - `KILL_FLAG_CLEAR_ON_START=1` にすると起動時に kill.flag を自動でクリアする（本番では推奨しない）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`
  - レポートは稼働率、注文成功率、レイテンシ等を算出し PASS/FAIL 判定する

- AI モジュール（ニュース NLP / レジーム判定）
  - 環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に api_key を渡す
  - プログラム的に呼ぶ例:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)

ディレクトリ構成（主要ファイル）
------------------------------
（パッケージルート: src/kabusys/ 以下）

- __init__.py
  - パッケージメタ情報（バージョン等）
- config.py
  - 環境変数読み込み・Settings クラス（.env の自動ロード、必須チェック）
- config_setup.py
  - .env を対話式に作るウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 切替等）
- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL）
- execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
  - 発注・オーダー管理・リスク制御の実装
- monitoring/
  - monitoring_db.py：SQLite テーブル初期化 / 永続化層
  - system_monitor.py：CPU/メモリ/ディスク・データ鮮度チェック
  - trade_monitor.py：トレードログの監視（滞留・異常）
  - risk_monitor.py：ドローダウン・ポジション上限監視
  - kill_switch.py：フラグファイルによる停止制御
  - alert_manager.py：LINE 等への通知（実装箇所）
  - monitoring_engine.py：各 Monitor を束ねる
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py：ポートフォリオ構築とリスク処理
- research/
  - factor_research.py：ファクター計算（momentum/value/volatility）
  - feature_exploration.py：将来リターン・IC 等
- ai/
  - news_nlp.py：ニュースを LLM でスコアリングし ai_scores に書き込む
  - regime_detector.py：市場レジーム判定（ETF MA + マクロセンチメント）
- tools/
  - paper_verification_report.py：ペーパートレード検証レポート生成
- utils/
  - logging_setup.py：統一ロギング設定
  - process_priority.py：プロセス優先度・CPU affinity 設定
  - その他ユーティリティ

運用上の注意
-------------
- .env を絶対にリポジトリにコミットしないこと（config_setup.py も警告があります）
- 本番では `KABUSYS_ENV=live` を慎重に扱い、`KILL_FLAG_CLEAR_ON_START` を 0 にすること
- AI モジュールは OpenAI API に依存します。コストやレート制限を考慮して運用してください
- monitoring は常に本番の sqlite_path（監視 DB）を参照します。間違った DB を参照しないよう .env を確認してください

追加の参照
------------
- 各モジュールの docstring に設計方針や注意点が詳述されています。具体的なパラメータや閾値を変更する場合は該当ファイルを参照してください。

必要であれば、README に具体的な .env のテンプレートや systemd / supervisor 用の起動ユニット例、運用手順（ログローテーション・バックアップ）などを追記します。必要な形式・詳細を教えてください。