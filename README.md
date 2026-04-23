KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買／リサーチ／監視を目的とした実装群です。  
モジュールは発注エンジン (Execution)、監視 (Monitoring)、ポートフォリオ構築、ファクター計算、AI（ニュースセンチメント / レジーム判定）などで構成されています。

主な特徴
--------
- 実運用を想定した設計（PID / stop フラグ / ログローテーション / 優先度設定）
- 発注エンジンは paper_trading と live を分離（paper_trading は専用 SQLite）
- 監視コンポーネント（System / Trade / Risk）と Kill Switch による自動停止
- DuckDB を使ったオンチェーン研究（ファクター計算、将来リターン、IC 等）
- OpenAI を使ったニュースの NLP スコアリング、マクロセンチメントによる市場レジーム判定
- ペーパートレード検証用レポート生成スクリプト
- 設定ウィザード（.env 生成）と設定検証ツール

必要条件（推奨）
----------------
- Python 3.9+
- pip
- 推奨パッケージ（用途に応じて）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証に使用）
- （任意）仮想環境の利用を推奨

インストール（例）
-----------------
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

設定（.env）
-----------
プロジェクトルートに .env を置くことで環境変数を読み込みます（自動ロード機構あり）。
自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定します。

推奨ワークフロー（対話的ウィザード）
- 初期 .env を対話式で作る:
  - python -m kabusys.config_setup
- 作成後に設定を検証:
  - python -m kabusys.validate_config
    - --strict を付けると警告もエラー扱いにします

主要な環境変数（代表）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL / LOG_DIR: ログ設定
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START: (0/1) Execution 起動時に kill.flag を自動削除するか

起動方法（実行スクリプト）
-------------------------
- ExecutionEngine を起動（実際の発注／ペーパー共通起動ロジック）:
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録します
- Monitoring を起動（ポーリングループ）:
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は環境にかかわらず production 相当の sqlite_path を使用します
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - --db オプションでデータベースパスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- 設定検証:
  - python -m kabusys.validate_config
- 設定ウィザード:
  - python -m kabusys.config_setup

プログラム的 API（利用例）
-------------------------
- 研究 / ファクター計算（DuckDB 接続を渡す）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
- ポートフォリオ構築系（純粋関数）
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- AI スコアリング（ニュース）
  - from kabusys.ai.news_nlp import score_news
    - DuckDB 接続と target_date、api_key を渡して ai_scores テーブルへ書き込みます
- レジーム判定
  - from kabusys.ai.regime_detector import score_regime

ログ / プロセス管理
------------------
- ログ: kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼んで統一的に管理
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション）
- プロセス優先度:
  - kabusys.utils.process_priority.set_process_priority("high") 等
- 停止フラグ / PID:
  - data/kill.flag — Kill Switch による停止指示
  - data/execution.pid — Execution の PID 管理
  - run_monitoring/run_execution は stop フラグを監視して安全に終了します

監視・安全装置
--------------
- 監視用 DB スキーマとユーティリティ:
  - kabusys.monitoring.monitoring_db — テーブル作成・ログ書込（system_status, trade_logs, positions, risk_logs, dashboard）
- Monitor 群:
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度等を監視
  - TradeMonitor: 注文滞留・約定異常等を検出（実装ファイル群に依存）
  - RiskMonitor: ドローダウン・ポジション上限を監視。DD 超過や上限超過時にリスクログ／kill.flag を生成
  - MonitoringEngine: これらを束ねてポーリング・アラート化
- KillSwitch: RiskMonitor 等の結果に基づき data/kill.flag を書き込み ExecutionEngine を停止させる仕組み

データ / ファイル
----------------
- デフォルトロケーション:
  - data/kabusys.duckdb （DuckDB）
  - data/monitoring.db （監視 SQLite）
  - data/paper_trading.db （ペーパートレード用 SQLite）
  - data/kill.flag, data/stop_requested.flag, data/execution.pid などの制御ファイル
- .env は絶対にリポジトリにコミットしないでください（config_setup にもその注意書きがあります）

よく使うコマンド例
-----------------
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ディレクトリ構成
----------------
（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード機構）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py     — マクロ + ETF MA200 で市場レジーム判定
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・資金配分ロジック
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py       — 監視用 DB 作成と永続化 API
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文関連の監視（コードベースに含まれる想定）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — アラート送信管理（LINE 等の実装想定）
    - monitoring_engine.py   — Monitor を束ねるループ
  - execution/               — ExecutionEngine と発注関連（OrderManager 等）
  - utils/
    - logging_setup.py       — 一元的なログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

補足 / 運用上の注意
------------------
- KABUSYS_ENV=live の場合は特に注意して設定を行ってください（validate_config は注意喚起を出します）。
- .env は機密情報（API トークン）を含むため、絶対に Git 管理下に置かないでください。
- OpenAI を使用する機能は API キーと利用コストが必要です。API 失敗時はフェイルセーフ（スコア 0 など）を実装していますが、運用方針を決めてください。
- 監視ループや Execution は stop フラグ / kill.flag を見て安全に停止する仕組みがあります。運用時は data/ ディレクトリのファイルにより起動停止を制御できます。

ライセンス / 貢献
-----------------
リポジトリに LICENSE があればそちらに従ってください。バグ報告・機能改善は Issue / Pull Request を送ってください。

---

問題があれば、どの機能（例: Execution の起動フロー、AI スコアリングの使い方、DuckDB のテーブル定義など）について詳細なドキュメントを作成するか教えてください。必要なら README に記載するサンプル .env を作成します。