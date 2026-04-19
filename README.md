# KabuSys

日本株向け自動売買システムのライブラリ群（モジュール単位の実装）。  
このリポジトリは発注エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム検出）などのコンポーネントを含みます。

## プロジェクト概要
- Python パッケージ `kabusys` として実装された自動売買システムのコア機能群。
- DuckDB を分析用 DB、SQLite を監視・発注履歴用 DB に利用する設計。
- 本番 / ペーパートレードを環境変数 `KABUSYS_ENV` により切替可能（`development` / `paper_trading` / `live`）。
- OpenAI を用いたニュースセンチメントおよび市場レジーム判定機能を含む（OpenAI API キー必須）。
- 多数のユーティリティ（ロギング設定、プロセス優先度、設定ウィザード、構成検証等）を提供。

## 主な機能一覧
- 起動スクリプト
  - run_execution: 発注エンジン（ExecutionEngine）起動（KABUSYS_ENV によりペーパートレード用モックを使用可能）
  - run_monitoring: SystemMonitor のポーリングループ起動（監視ログの永続化）
- 設定関連
  - config_setup: .env の対話的生成/更新ウィザード
  - validate_config: .env と config/*.yaml の簡易検証 CLI（--strict あり）
  - Settings クラスで環境変数の取得と検証を提供
- 監視（monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を統合した MonitoringEngine
  - KillSwitch: リスクトリガーで `data/kill.flag` を書き込み ExecutionEngine を停止
  - monitoring_db: 監視用 SQLite スキーマと永続化 API
- 発注・実行（execution）
  - BrokerClientFactory（実ブローカー or Mock を環境で切替）
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（発注ロジック・リスク制御）
- ポートフォリオ構築（portfolio）
  - 候補選定、等重/スコア重み、位置サイズ計算、セクター制約、レジーム乗数
- リサーチ（research）
  - Factor 計算（momentum, volatility, value 等）
  - 将来リターン計算、IC 計算、統計サマリ
- AI（ai）
  - news_nlp.score_news: ニュース記事をまとめて OpenAI に投げ、銘柄ごとのスコアを ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF MA とマクロ記事センチメントを合成して市場レジーム判定、market_regime テーブルへ保存
- ツール
  - tools.paper_verification_report: ペーパートレード DB を集計して検証レポートを出力

## 必要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意（デフォルトあり）
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
  - OPENAI_API_KEY — AI 機能利用時に必要
  - LOG_LEVEL — DEBUG/INFO/…（デフォルト INFO）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — アラート通知（任意）
  - PAPER_FILL_MODE — paper_trading の約定モード（instant/partial/never/reject、デフォルト instant）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、run_monitoring 用。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — 本番で Kill Switch 自動クリアするか（0/1、デフォルト 0）

.env の自動ロード:
- プロジェクトルートに `.env` / `.env.local` があれば自動で読み込みます（OS 環境変数を上書きしない）。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

## セットアップ手順（例）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（requirements.txt がある場合）
   - pip install -r requirements.txt
   - 本リポジトリの主な依存例: duckdb, psutil, openai, PyYAML（config 検証用）

3. .env を作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - あるいは `.env.example` を参考に `.env` を手動で作成

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

5. ディレクトリ作成（ログ / data）
   - ログ出力先（デフォルト: logs/）や DB 保存先（data/）は自動作成されますが、手動で用意することも可能。

## 実行方法（代表例）
- 監視プロセスの起動（ポーリングループ）
  - 環境変数で MONITOR_POLL_INTERVAL を秒で指定可能（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 監視は data/stop_requested.flag の存在を見て終了します（フラグファイル方式）

- 発注エンジンの起動
  - 本番 / ペーパーは KABUSYS_ENV で切替
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が既に存在する場合は起動をスキップ
  - 実行中は PID ファイル (デフォルト data/execution.pid) を生成

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- ペーパー検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db。--db で別パス指定可。

- AI スコア・レジーム判定（プログラム利用例）
  - ニュース NLP（スコア付与）を単体で呼ぶ:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")  # duckdb_conn は duckdb.connect(...)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

注: OpenAI の呼び出しはネットワーク・API レートの影響を受けるため、API キーとレート制御の準備を行ってください。AI 呼び出しはリトライ・フォールバックロジックを備えていますが、API キー未設定では例外を投げます。

## 停止・Kill 操作
- 監視ループ / ExecutionEngine 停止:
  - data/stop_requested.flag を作成すると両プロセスは次のループで検知して終了します。
- 強制停止（Kill Switch）:
  - 監視側のリスク条件が成立すると `data/kill.flag` が書き込まれ、ExecutionEngine はこれを検出して停止する設計です。
- 起動時の Kill Flag 自動クリアは `.env` の KILL_FLAG_CLEAR_ON_START を 1 にすると実行されます（本番では 0 推奨）。

## デフォルトのパス（主なもの）
- DuckDB: data/kabusys.duckdb
- SQLite (monitoring): data/monitoring.db
- Paper trading SQLite: data/paper_trading.db
- PID ファイル: data/execution.pid
- Kill flag: data/kill.flag
- Stop request flag: data/stop_requested.flag
- ログ: logs/<app_name>.log（デフォルト日次ローテーション）

## プログラム API の概要（利用可能な主要モジュール）
- kabusys.config.Settings / settings — 環境変数読み取り・検証
- kabusys.utils.logging_setup.setup_logging(app_name, log_dir, level)
- kabusys.utils.process_priority.set_process_priority(level), set_cpu_affinity(...)
- kabusys.monitoring.monitoring_db.MonitoringDB — 監視ログの永続化 API
- kabusys.monitoring.{SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch}
- kabusys.execution.* — 発注エンジン関連（Engine, OrderManager, RiskManager, BrokerClientFactory）
- kabusys.portfolio.* — 候補選定・重み付け・ポジションサイジング・リスク調整
- kabusys.research.* — ファクター計算・将来リターン・IC 等
- kabusys.ai.news_nlp.score_news, kabusys.ai.regime_detector.score_regime
- kabusys.tools.paper_verification_report.generate_report

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ + DB API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       (アラート周り)
  - execution/
    - execution_engine.py
    - broker_factory.py
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
  - tools/
    - paper_verification_report.py

（上の一覧はリポジトリ内の主要ファイルを抜粋したものです）

## 運用上の注意・ベストプラクティス
- 本番（KABUSYS_ENV=live）では .env の値と通知先 (LINE) を必ず確認すること。
- Kill Switch / Stop Flag の取り扱いに注意（誤って自動クリアしない設定を推奨）。
- DuckDB / SQLite のバックアップ・ローテーションを運用ルールとして整備すること。
- OpenAI 等外部 API 呼び出しのコスト・レート制限に留意すること。
- ログは logs/ に日次ローテーションで吐かれます。ディスク使用量を監視してください。

---

README に記載されていない細かい使い方や API は各モジュール内の docstring を参照してください。必要であれば、起動例や設定例（.env.example など）を追加で作成できます。