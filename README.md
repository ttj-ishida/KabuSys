# KabuSys

日本株自動売買システムの参照実装ライブラリ (v0.1.0)

このリポジトリは自動売買のコア機能（ポートフォリオ構築、ポジションサイズ計算、監視、実行エンジン、研究・ファクター計算、LLM を使ったニュース解析など）を含むモジュール群を提供します。実運用を想定した設計（監視／Kill Switch、ペーパートレード分離、ログローテーション、設定ウィザード等）が取り入れられています。

---

主な特徴
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- リスク調整（セクターキャップ、レジーム乗数）
- 監視サブシステム（System / Trade / Risk モニタ、Kill Switch、永続化）
- 実行エンジン起動スクリプト（本番 / ペーパートレード分離）
- 設定ウィザード（.env 生成）と設定検証 CLI
- 研究用モジュール（ファクター計算、前方リターン、IC 等）
- LLM を使ったニュースセンチメント評価（OpenAI）
- データ永続化に SQLite（監視用）と DuckDB（時系列・分析用）
- ログは stdout と日次ローテーション（logs/<app>.log）で管理

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動／ツール）
- ディレクトリ構成（主要ファイルの説明）
- 重要な環境変数・ファイル

---

プロジェクト概要
- パッケージ名: kabusys
- 目的: 日本株向けの自動売買システムのコンポーネント群を提供。研究・検証から本番稼働までを想定した設計。
- 永続化:
  - DuckDB: 分析・ファクタ計算用（デフォルト: data/kabusys.duckdb）
  - SQLite: 監視ログ・ペーパートレード用（デフォルト: data/monitoring.db / data/paper_trading.db）

---

機能一覧（要点）
- kabusys.portfolio
  - 銘柄候補選び（select_candidates）
  - 等重／スコア重み計算（calc_equal_weights / calc_score_weights）
  - ポジション数計算（calc_position_sizes）
  - セクターキャップとレジーム乗数（apply_sector_cap / calc_regime_multiplier）
- kabusys.research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC・統計サマリ（calc_forward_returns / calc_ic / factor_summary）
- kabusys.monitoring
  - DB 層（monitoring_db.py）: テーブル作成・マイグレーション、ログ永続化
  - SystemMonitor / TradeMonitor / RiskMonitor（監視ロジック）
  - KillSwitch（data/kill.flag により ExecutionEngine を停止）
  - MonitoringEngine（モニタを束ねるポーリングエンジン）
  - 起動スクリプト: run_monitoring.py（定期ポーリング）
- kabusys.execution
  - ExecutionEngine（エンジン起動ロジック）
  - Broker クライアントファクトリ（paper_trading 時は Mock を使用）
  - OrderManager / OrderRepository / Reconciler / RiskManager
  - 起動スクリプト: run_execution.py（停止フラグやペーパートレード DB の扱いを考慮）
- kabusys.ai
  - news_nlp: OpenAI を使ったニュースセンチメント集計と ai_scores への書き込み
  - regime_detector: ma200 とマクロニュースを合成して市場レジーム判定
- ユーティリティ
  - config_setup.py: .env 対話式ウィザード
  - validate_config.py: 起動前検証 CLI
  - logging_setup: 一貫したログ設定（stdout + 日次ローテーション）
  - process_priority: プロセス優先度設定（Windows / POSIX 対応）

---

セットアップ手順（開発 / 実行）
前提: Python 3.10 以上を推奨（typing の | 演算子など）。適宜仮想環境を作成してください。

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate   # Unix
   .venv\Scripts\activate      # Windows

3. 必要パッケージをインストール
   pip install duckdb psutil openai
   # 便利ツール: PyYAML（config 検証で YAML 検査を有効にする）
   pip install pyyaml

   （requirements.txt がある場合はそれを利用してください）

4. .env の準備
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - あるいはルートに .env を直接配置。デフォルトは data/ 以下に DB を作成します。
   - 自動ロード: package の起動時に .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

5. 設定検証（必須項目の確認）
   python -m kabusys.validate_config
   本番環境で厳格にしたい場合:
   python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   mkdir -p data logs

---

重要な環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution モード（development | paper_trading | live）（デフォルト: development）
  - paper_trading 時は Broker はモックを使い、データは data/paper_trading.db に書き込まれる
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector で使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔秒（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1）

---

使い方（主要コマンド例）

- 環境ウィザード（.env を作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループを起動（SystemMonitor をポーリング）
  python -m kabusys.run_monitoring
  # ポーリング間隔を変更:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（ExecutionEngine）を起動
  python -m kabusys.run_execution
  # KABUSYS_ENV=paper_trading の場合は MockBroker を使用して data/paper_trading.db に記録
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- LLM を使ったニューススコア付け（コードから呼び出す）
  from kabusys.ai.news_nlp import score_news
  score_news(duckdb_conn, target_date, api_key="...")

- レジーム判定（コードから）
  from kabusys.ai.regime_detector import score_regime
  score_regime(duckdb_conn, target_date, api_key="...")

停止フラグ
- 実行系（ExecutionEngine）を外部から停止したい場合:
  data/kill.flag に理由文字列を書き込むと KillSwitch により Engine 停止を誘発します（監視経由で評価される）。
- run_monitoring / run_execution は data/stop_requested.flag の存在を見てループを終了します。運用スクリプトはこれらのフラグファイルを用いて停止制御できます。

ログ
- setup_logging により stdout と logs/<app_name>.log（midnight ローテーション、30 日保持）に出力されます。
- ログディレクトリは LOG_DIR 環境変数、またはデフォルト logs/ を使用します。

---

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み。Settings クラス）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（ペーパートレード分離）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ファイル）
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブル初期化・永続化 API（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （注文監視ロジック）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — Kill Switch 制御
    - alert_manager.py — （アラート送信ロジック: LINE 等）
  - execution/
    - execution_engine.py — 実際のセッション起動・管理
    - broker_factory.py — Broker クライアントの生成（Mock / 実ブローカ）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（ロット丸め・aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — forward returns / IC / 統計サマリ
  - ai/
    - news_nlp.py — OpenAI を使ったニューススコアリング（ai_scores 書き込み）
    - regime_detector.py — ma200 + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール

ルートディレクトリ（リポジトリトップ）
- data/         — デフォルトの DB / フラグファイルを配置（監視・実行で使用）
  - monitoring.db (デフォルト: SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kill.flag / stop_requested.flag / execution.pid
- logs/         — ログファイル出力先（デフォルト）
- config/       — YAML ベースの各種設定テンプレート（system_config.yaml 等）
- pyproject.toml / .git / README.md（本ファイル）

---

注意事項 / 運用上のヒント
- KABUSYS_ENV=live を指定する場合は特に注意（validate_config による警告あり）。LINE 通知等の設定を確認してください。
- データの永続化パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）は .env で明示的に設定できます。絶対パスやユーザーディレクトリ指定も可能（expanduser 処理あり）。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必要。API エラーはリトライやフェイルセーフによりシステムを停止させない設計ですが、キー未設定だと呼び出しは失敗します。
- run_execution はペーパートレード時に本番 DB と分離して動作します（重要: 実取引とデータ分離）。
- ログディレクトリ作成やファイル書き込みに失敗した場合、ログは stdout のみで動作し続けます（エラーを起こさないフォールバック実装）。

---

貢献・拡張案
- 銘柄別 lot_size の導入（現在は共通 lot_size）
- レバレッジや複雑なコスト推定を組み込んだ position sizing
- monitoring のアラート先（Webhook / PagerDuty 等）追加
- research モジュールを pandas / numpy に最適化して高速化
- OpenAI 呼び出しの一括バッチ化や非同期化によるスループット改善

---

ライセンス
- 本リポジトリに含まれるコードのライセンスはリポジトリルートの LICENSE を参照してください（存在しない場合は著者に確認してください）。

---

必要に応じて README を補足します（例: 詳細な設定項目一覧、SQL スキーマ、実行時ログ例、運用手順書など）。必要な追加情報を教えてください。