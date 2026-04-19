KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株自動売買システムのコアライブラリです。バックテスト／リサーチ用のファクター計算、ポートフォリオ構築、注文サイズ決定ロジック、モニタリングおよび実行エンジンの起動スクリプトや運用支援ツールを含みます。

主な設計方針：
- DuckDB を用いたデータ分析（prices_daily / raw_financials 等）
- SQLite を用いた監視・発注履歴の永続化（monitoring.db / paper_trading.db）
- 環境変数（.env）で構成を管理。config_setup.py による対話式ウィザードを提供
- OpenAI を用いたニュース NLP（任意、API キー必須）
- 実行環境（本番 / ペーパートレード / 開発）に応じた挙動切替

機能一覧
--------
- 環境設定ウィザード（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
- 実行エンジン起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading.db に分離
- 監視ループ起動スクリプト（kabusys.run_monitoring）
  - システム・データ鮮度・注文状況・リスクを定期チェックし kill.flag 発行等を行う
- MonitoringDB（SQLite）ラッパー：system_status / trade_logs / positions / risk_logs / dashboard
- RiskMonitor / SystemMonitor / TradeMonitor / MonitoringEngine（監視ロジック）
- Portfolio 構築ユーティリティ
  - 候補選定、等金額／スコア加重配分、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算（単元丸め・aggregate cap）
- Research: ファクター計算（momentum / volatility / value）、forward return / IC / 統計サマリー
- AI モジュール
  - news_nlp: OpenAI を使ったニュースセンチメント集約・ai_scores 保存
  - regime_detector: マクロニュース + ETF MA200 を組み合わせた市場レジーム判定
- 運用ツール
  - paper_verification_report：ペーパートレード DB から検証レポートを生成

セットアップ手順
----------------
1. リポジトリをチェックアウト
   - この README はパッケージ内のスクリプトやモジュールを前提としています。

2. 依存パッケージをインストール（例）
   - Python 3.9+ を想定
   - 主要依存例:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - pyyaml（config ファイル検証を行う場合）
   - 例:
     pip install duckdb psutil openai pyyaml

3. 環境変数 (.env) を作成
   - 対話式ウィザードで作成できます:
     python -m kabusys.config_setup
   - 主要な環境変数（必須 / 推奨）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（paper_trading 時に使用）。デフォルト: data/paper_trading.db
     - OPENAI_API_KEY — AI 機能を使う場合に必要
     - LOG_LEVEL / LOG_DIR — ログ設定
     - KILL_FLAG_CLEAR_ON_START — 本番での自動 Kill フラグクリアは危険（デフォルト 0）
   - 設定検証:
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict  # 警告もエラー扱い

4. データディレクトリ作成（必要なら）
   - デフォルトでは data/ と logs/ を利用します。スクリプト起動時に自動作成されることが多いですが、権限等で失敗する場合は手動で作成してください。

使い方
------
起動スクリプト
- 実行エンジン（ExecutionEngine）を起動
  - 本番／ペーパーの違いは KABUSYS_ENV で制御されます。
  - 起動:
    python -m kabusys.run_execution
  - 実行中は data/execution.pid に PID が書き込まれ、停止は data/stop_requested.flag または監視側の kill.flag によって行います。

- 監視ループを起動
  - 監視は MonitoringEngine をポーリング実行します。
  - 起動:
    python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
  - 監視は常に本番の sqlite_path を参照します（監視は環境にかかわらず本番 DB を使用）

運用フラグ / 停止
- data/stop_requested.flag
  - run_execution / run_monitoring の起動ループはこのファイルを検知すると終了します（運用側によるソフト停止）。
- Kill Switch: data/kill.flag（パスは Settings.kill_flag_path で指定可能）
  - MonitoringEngine がリスクルール（例: ドローダウン閾値超過）を検出した場合に書き込まれます。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定しない限り自動クリアされません（本番では 0 推奨）。

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
  - 確認指標: 稼働率、注文成功率、送信率、P95 レイテンシ等

AI 機能
- news_nlp.score_news / regime_detector.score_regime は OpenAI API を呼び出します。事前に OPENAI_API_KEY を設定してください。
- API 呼び出しはリトライ／フォールバックを内蔵しており、失敗時は安全にスキップする設計です（例: macro_sentiment=0.0）。

ログ
- ログはデフォルトで stdout と logs/<app_name>.log に日次ローテーションで保存されます（logs/ ディレクトリ）。ログレベルは LOG_LEVEL または setup_logging() の引数で設定可能。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュールと説明（抜粋）です。

- kabusys/
  - __init__.py                 — パッケージ定義（__version__ 等）
  - config.py                   — 環境変数/.env の読み込みと Settings クラス
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py               — ニュース NLP / OpenAI 統合（ai_scores 書込み）
    - regime_detector.py        — マクロ+MA200 によるレジーム判定
  - research/
    - factor_research.py        — モメンタム/ボラティリティ/バリュー等の計算
    - feature_exploration.py    — forward returns / IC / 統計サマリー
  - portfolio/
    - portfolio_builder.py      — 候補選定 / 重み計算
    - risk_adjustment.py        — セクター制限 / レジーム乗数
    - position_sizing.py        — 株数決定・aggregate cap
  - monitoring/
    - monitoring_db.py          — SQLite テーブル初期化・永続化 API
    - system_monitor.py         — システム状態・データ鮮度チェック
    - risk_monitor.py           — ドローダウン・ポジション数監視
    - kill_switch.py            — kill.flag 書き込みユーティリティ
    - monitoring_engine.py      — 各 Monitor を束ねるループ
    - (trade_monitor 等 他モジュールあり)
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成
  - utils/
    - logging_setup.py          — ログ設定ユーティリティ
    - process_priority.py       — プロセス優先度 / CPU affinity 設定

注意事項 / 運用上のヒント
-------------------------
- KABUSYS_ENV=live（本番）では設定に細心の注意を払ってください。validate_config は live 時に警告を出します。
- 本番 DB とペーパートレード DB は分離する設計です（PAPER_TRADING_SQLITE_PATH）。
- .env は絶対にソース管理に含めないでください（config_setup.py のヘッダにも記載あり）。
- ローカル環境や CI で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（config.py の自動ロード制御）。
- OpenAI を利用する機能は API 利用料が発生します。テスト時はモック化（unittest.mock.patch）で外部呼び出しを抑制してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__（デフォルト "0.1.0"）。
- ライセンス情報はリポジトリのルートにある LICENSE を参照してください（存在する場合）。

フィードバック / 貢献
--------------------
バグ報告や機能提案はリポジトリの Issue を利用してください。プルリクエスト歓迎です。

以上。必要であれば README にセットアップの手順（venv、docker-compose、requirements.txt の例）やよくあるトラブルシュートを追加できます。どの情報を詳細化しますか？