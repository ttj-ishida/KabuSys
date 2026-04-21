# KabuSys

日本株向けの自動売買・研究基盤ライブラリ兼実行フレームワーク（プロトタイプ）。  
このリポジトリには以下の要素が含まれます: 注文実行エンジン、監視（モニタリング）、ポートフォリオ構築ユーティリティ、リサーチ用ファクター計算、AI（ニュースNLP / レジーム判定）連携、各種ユーティリティとコマンドラインヘルパー。

---

## 概要

KabuSys は次の目的を想定したモジュール群です。

- 戦略に基づく銘柄選定、ウェイト計算、ポジションサイジング
- 実行エンジン（ExecutionEngine）を通じた発注管理（本番 / ペーパートレード切替）
- 実行状況・システム状態の定期監視（Monitoring）
- Paper Trading の検証レポート生成ツール
- DuckDB を使ったファクター計算・リサーチ機能
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント解析 / マクロセンチメントによるレジーム判定
- 設定ウィザード（.env 作成）と設定検証ツール

---

## 主な機能一覧

- 実行 / 監視ランタイム
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV による paper_trading 切替）
  - run_monitoring.py: SystemMonitor をポーリング実行（MONITOR_POLL_INTERVAL で間隔指定）
- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/Disk、データ鮮度、Execution プロセスの生存チェック
  - TradeMonitor / RiskMonitor / KillSwitch / AlertManager 組合せによる自動停止判定（kill.flag）
  - monitoring_db: SQLite ベースの監視ログ保存（system_status / trade_logs / risk_logs / positions / dashboard）
- 実行（execution）
  - BrokerClientFactory による本番 / モックブローカーの注入
  - OrderManager / Reconciler / RiskManager による発注制御と安全弁
  - ExecutionEngine: 実行セッション管理（PID ファイル / 停止フラグ監視）
- ポートフォリオ構築（pure functions）
  - 複数の配分方法（等分、スコア加重、リスクベース）
  - セクター集中制限、レジーム乗数、単元株丸め、集約キャップ処理
- リサーチ
  - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 経由）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、要約統計
- AI
  - news_nlp: raw_news を LLM で評価し ai_scores に書き込み
  - regime_detector: ETF (1321) MA200 乖離 + マクロニュースで市場レジーム判定
- ユーティリティ
  - config_setup: 対話式 .env ウィザード（初期設定）
  - validate_config: .env／config/*.yaml 検証 CLI
  - tools/paper_verification_report: Paper Trading 検証レポート生成
  - logging_setup: 統一ロギング設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 必須環境・依存パッケージ（例）

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config *.yaml の内容検証を行う場合）
- sqlite3（標準ライブラリ）
- その他、実行環境に応じた Broker クライアント依存など

（requirements.txt はプロジェクトに含めてください。上記パッケージを pip でインストールしてください）

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は上の必須パッケージを個別にインストール）

4. .env を作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等を入力してください
   - 注意: .env は機密情報を含むため絶対に Git にコミットしないでください

5. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数が足りない場合や config/*.yaml の問題が報告されます
   - --strict オプションを付けると警告もエラー扱いになります

6. データディレクトリの準備（任意）
   - デフォルトの DB / PID / フラグパスは data/ 以下です。必要に応じて作成・権限を確認してください。

---

## 実行方法（使い方）

- 環境変数の主な用途（要設定）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker を使用しデータを data/paper_trading.db に分離
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db） — 監視 DB（monitoring は常に本番 sqlite_path を参照）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - LOG_LEVEL / LOG_DIR
  - OPENAI_API_KEY（AI 機能を使う場合）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）

- ExecutionEngine を起動（デーモン管理や systemd 等で運用）
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid に PID を書き込みます
  - KABUSYS_ENV=paper_trading の場合は paper DB に書き込み（本番 DB と分離）
  - 停止: data/stop_requested.flag を作成（run_execution はこのフラグを見て停止）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は実行に関わらず monitoring の sqlite_path（本番パス）を使用します（環境に依存しない）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（--db オプションでも指定可）

- AI 機能（プログラムから）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

- 設定検証（CLI）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

---

## ログ・監視・停止機構

- ログ
  - kabusys.utils.logging_setup.setup_logging(app_name="...") を各起動スクリプトで呼び出します
  - コンソール出力（stdout）と logs/<app_name>.log に日次ローテートで出力（30 日分保持）

- 優先度・CPU affinity
  - run_* 起動時に set_process_priority("high") を呼び出して優先度を高く設定します（psutil を使用）

- Kill Switch / 停止フラグ
  - KillSwitch は監視結果に基づき data/kill.flag を書き込み、ExecutionEngine 停止のトリガーとします
  - run_execution / run_monitoring は data/stop_requested.flag を検出して graceful shutdown します
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動クリアされるため本番では 0 を推奨

---

## 主要モジュール / API 概要

- kabusys.config
  - Settings クラスで環境変数の取得・妥当性検査を提供
  - 自動でプロジェクトルートの .env/.env.local を読み込む（無効化可）

- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（等分 / スコア / リスクベース）
  - apply_sector_cap, calc_regime_multiplier

- kabusys.research
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（data.stats 由来）

- kabusys.ai
  - news_nlp.score_news: raw_news -> ai_scores 書き込み（OpenAI API を利用）
  - regime_detector.score_regime: マクロ + ETF MA200 を合成して market_regime に書き込み

- kabusys.monitoring
  - MonitoringDB（SQLite への読み書き）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine

- kabusys.utils
  - logging_setup.setup_logging
  - process_priority.set_process_priority / set_cpu_affinity

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor.py, alert_manager.py 等の関連ファイルがある想定)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - portfolio/, research/, ai/, monitoring/（それぞれの実装）

- data/                  — デフォルトの DB / PID / flag を格納（実行時自動作成）
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - kill.flag
  - stop_requested.flag

- logs/                  — ログファイル（ログ設定で作成）

---

## 注意点・運用上のアドバイス

- .env には API キーやパスワードなど機密情報を含みます。Git にコミットしないでください。
- 本番環境（KABUSYS_ENV=live）は十分に注意して設定してください。validate_config は live 用のガードルールを出します。
- Monitoring は監視 DB（SQLITE_PATH）へ常に本番パスを使う仕様です。監視は環境に依存せず本番 DB を参照するため運用時のパスに注意してください。
- Paper Trading は paper_trading 用の SQLite に完全分離されるので、検証時は KABUSYS_ENV=paper_trading を利用してください。
- OpenAI など外部 API を利用する機能は API キーが必要で、API 呼び出しに失敗した場合はフェイルセーフ（スコア 0 等）で動作する実装が多いですが、運用時のレート制限やコストに注意してください。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します（設定参照）。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

もし README に加えたい追加の情報（例: requirements.txt の中身、systemd ユニットの例、より詳細な API ドキュメント、自動テスト手順など）があれば教えてください。必要に応じて追記・整備します。