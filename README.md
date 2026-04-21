# KabuSys

日本株自動売買システムのリポジトリ（軽量なプロダクション／リサーチ共存型実装）。  
この README はコードベースの主要コンポーネントの説明、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム（発注エンジン、監視、ポートフォリオ構築、ファクター計算、ニュース NLP 等）を含むモジュール群です。  
設計方針の要点：

- 本番（live）／ペーパートレード（paper_trading）／開発（development）環境を区別可能
- 設定は .env で管理（config_setup によるウィザード生成）
- DuckDB を分析・リサーチ用 DB として利用、SQLite を監視や発注ログ保存に利用
- OpenAI（gpt-4o-mini） を使ったニュースセンチメントやレジーム判定機能（任意）
- プロセス優先度・ログ設定など運用面のユーティリティを備える

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine（発注エンジン）を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し DB を分離。
  - run_monitoring.py: SystemMonitor をポーリングしてシステム状態を監視・ログ化。

- 設定関連
  - config.py: 環境変数／.env の読み込み・管理（自動読み込み機能あり）。
  - config_setup.py: .env を対話的に作成/更新するウィザード。
  - validate_config.py: 起動前チェック（必須環境変数や config/*.yaml の存在/パース検証）。

- 監視（Monitoring）
  - monitoring_db.py: SQLite スキーマ初期化・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）。
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 各種監視ロジック（システム状態、注文滞留、ドローダウン等）。
  - monitoring_engine.py: 複数モニタを束ねるポーリングエンジン。
  - kill_switch.py: 条件に応じて data/kill.flag を書き込み ExecutionEngine 停止を促す。

- 実行（Execution）
  - execution_engine 等（execution パッケージ）: Broker 統合、注文管理、リスク管理、約定調整等（run_execution.py から起動）。

- ポートフォリオ構築（Portfolio）
  - portfolio_builder.py: 候補選定・スコアソート等。
  - position_sizing.py: 株数計算、単元丸め、資金配分ロジック。
  - risk_adjustment.py: セクター制限、レジーム乗数。

- リサーチ（Research）
  - factor_research.py: Momentum / Value / Volatility 等のファクター計算（DuckDB を利用）。
  - feature_exploration.py: 将来リターン計算、IC（Information Coefficient）計算、統計サマリー。

- AI 関連
  - ai/news_nlp.py: raw_news を OpenAI に投げて銘柄別センチメント（ai_scores）を生成。
  - ai/regime_detector.py: ETF の MA200 とマクロニュースを用いた市場レジーム判定。

- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定（コンソール stdout + 日次ローテートファイル）。
  - utils/process_priority.py: Windows/Linux の差を吸収してプロセス優先度・CPU affinity を設定。

- ツール
  - tools/paper_verification_report.py: Paper Trading 結果の検証レポート生成（稼働率・約定率・レイテンシ等）。

---

## 前提・依存関係

最低限必要な主要パッケージ（開発環境に応じてインストールしてください）：

- Python 3.9 以上 推奨（現行コードは型ヒントに Python 3.10+ の書式を使っている箇所あり）
- pip install:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合、必須ではない）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib 等

（実運用では requirements.txt を作成して依存を固定することを推奨します）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
   - git clone ... && cd <repo>

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージのインストール
   - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（以下は主なキー）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=...（AI 機能を使う場合）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 必要なら厳格モード: python -m kabusys.validate_config --strict

6. データディレクトリ等の準備（必要に応じて）
   - デフォルトで使用するパス（logs/, data/）は自動で作成されますが、権限や配置ポリシーを確認してください。

---

## 使い方（主要スクリプト）

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録される（本番 DB と分離）。
    - PID ファイルや data/stop_requested.flag を監視して安全に停止可能。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor のポーリングループを開始（デフォルト 60 秒間隔）。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視ログを書き込む。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）

- ライブラリとしての利用（開発者向け）
  - portfolio: kabusys.portfolio.select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  - research: kabusys.research.calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  - ai: kabusys.ai.score_news, regime_detector.score_regime
  - monitoring DB API: kabusys.monitoring.monitoring_db.MonitoringDB（log_system_status, log_trade_event, upsert_dashboard 等）

---

## 運用上の注意

- 環境分離:
  - paper_trading モードでは発注ログ等が paper_trading 用 DB に分離されます（PAPER_TRADING_SQLITE_PATH）。
  - 監視ロギング（monitoring）は常に Settings.sqlite_path（本番監視 DB）を使用します。運用設計に注意してください。

- Kill Switch:
  - KillSwitch は risk 条件（ドローダウンやポジション上限）に応じて data/kill.flag を作成します。ExecutionEngine はこのフラグを検出して安全停止します。
  - 本番環境で自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0。

- OpenAI API:
  - news_nlp や regime_detector は OPENAI_API_KEY が必要です。API 呼び出しはリトライやフェイルセーフを備えていますが、API 費用・レート制限に留意してください。
  - LLM 出力のパースや得られたスコアは必ずバリデーションされていますが、実運用前に十分なテストを行ってください。

- ログ:
  - logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR を設定すると保存先を変更できます。

- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。OS の権限によっては変更できない場合があります（警告のみ出力）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要構成（ツリー形式の抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - data/                (データファイル配置想定: data/*.db, pid/flag 等)
  - logs/                (ログ出力ディレクトリ)
  - execution/           (Execution エンジン関連)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py

（リポジトリのルートに pyproject.toml や .git/ がある前提で config.py はプロジェクトルートを検出します）

---

## 開発・拡張のヒント

- DuckDB 接続を渡す設計により、研究・分析機能は本番発注ロジックと分離してテストできます。
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
- ai モジュールの API 呼び出し部は内部でラップされているため unittest.mock で差し替えてテストできます。
- monitoring_db.init_monitoring_db は既存 DB に対してマイグレーション（カラム追加）を行うので、スキーマ変更はここを拡張してください。

---

この README はコードベースの要点をまとめたものです。細かい API や実装の詳細は各モジュールの docstring を参照してください。必要であれば、導入手順（systemd / supervisor の unit サンプル、Docker 化、CI 設定など）を別途作成できます。