# KabuSys

日本株向け自動売買システムのバックエンドライブラリ群・実行スクリプト集です。  
このリポジトリはトレード用の Execution Engine、監視用 Monitoring 、リサーチ／ポートフォリオ構築、AI を利用したニュース解析などのコンポーネントで構成されています。

注意: 本ドキュメントはコードベース（src/kabusys/**）の内容に基づく README です。

---

## プロジェクト概要

- ExecutionEngine：発注・注文管理・リスク管理・調整（paper_trading を含む）
- Monitoring：システム稼働・データ鮮度・注文ログの監視、Kill Switch によるエンジン停止
- Research：DuckDB を用いたファクター計算・特徴量解析
- Portfolio：候補選定、重み計算、ポジションサイジング、セクター制約適用
- AI：OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価・市場レジーム判定
- Tools：Paper Trading の検証レポート生成などユーティリティ

主要な考え方：
- 設定は .env または環境変数で管理（自動ロード機能あり）
- paper_trading（ペーパートレード）は本番 DB から完全に分離（専用 SQLite）
- DuckDB は分析用（prices_daily / raw_financials 等）
- 監視ログや簡易な永続化は SQLite（monitoring.db）で管理

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成・更新）
  - kabusys.config_setup.run_wizard / python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の検証）
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動スクリプト
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し data/paper_trading.db に記録
- 監視（ポーリング）起動スクリプト
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL で間隔上書き（デフォルト 60s）
- 監視永続層（SQLite） — monitoring_db: system_status / trade_logs / positions / risk_logs / dashboard
- Kill Switch（data/kill.flag）による安全停止
- RiskMonitor（ドローダウン監視・ポジション上限監視）
- TradeMonitor／SystemMonitor（遅延・プロセス死活・データ鮮度チェック）
- AI ニュース NLP（OpenAI）：銘柄ごとのセンチメントを ai_scores テーブルへ書き込み
- Regime Detector：ETF（1321）の MA + マクロニュースで市場レジーム判定、market_regime に書込
- Research：momentum / volatility / value 等のファクター計算、IC 計算、統計サマリ
- Portfolio：候補選定、等金額／スコア加重、リスクベースの株数算出、セクターキャップ・レジーム乗数
- Tools：Paper Trading の検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提
- Python 3.10 以上（型記法に `X | Y` を使用しているため）
- git, pip など

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - PyYAML は設定ファイル検証（validate_config の YAML パース）で任意：pip install pyyaml
   - （将来的な依存を追加する場合は requirements.txt を参照してください）
4. .env の初期化（ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants / kabuAPI パスワードなどを対話式に聞きます
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 便利な環境変数（一部、デフォルトあり）
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - LOG_LEVEL (default: INFO)
     - OPENAI_API_KEY — AI 機能を使う場合必須
     - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading 用
     - KILL_FLAG_CLEAR_ON_START (0|1) — Execution 起動時の kill.flag 自動クリア
     - その他は .env.example を参照してください
5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにするには --strict を付与
6. ディレクトリ作成（ログ / data 等は自動作成されることが多いですが事前作成推奨）
   - mkdir -p data logs

注記:
- 自動で .env を読み込む機能はデフォルトで有効。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- Monitoring/Execution は起動時に DB 初期化（監視用テーブル）を行うため、明示的なマイグレーション手順は基本不要です。

---

## 使い方（代表的なコマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
    - 起動時に data/execution.pid を書き、停止は data/stop_requested.flag か data/kill.flag により行います（KillSwitch の評価で kill.flag を書くことがあります）
    - 実行はバックグラウンドスレッドで行われ、メインループで stop flag を監視します

- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を参照し、system_status / trade_logs 等へ記録します
  - 停止は data/stop_requested.flag を作るか Ctrl+C（KeyboardInterrupt）

- Kill Switch
  - KillSwitch（kabusys.monitoring.kill_switch）は RiskMonitor / SystemMonitor / TradeMonitor の結果から条件に合致すれば data/kill.flag を書き込み、ExecutionEngine 側が停止処理を行います
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（または --db オプション）

- AI 機能
  - OpenAI を利用するため OPENAI_API_KEY を環境変数に設定
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して ai_scores / market_regime を更新

---

## 重要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（デフォルトあり/推奨値）:
- KABUSYS_ENV: development | paper_trading | live  (default: development)
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- OPENAI_API_KEY: OpenAI 呼び出しに必須（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の約定挙動）
- KILL_FLAG_CLEAR_ON_START: 0 or 1（起動時に kill.flag を自動クリアするか）

設定読み込み:
- プロジェクトルートの .env, .env.local を自動で読み込み（OS 環境変数優先）
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ログ

- ログセットアップは kabusys.utils.logging_setup.setup_logging を通して行われます
- コンソール（stdout）出力 + 日次ローテーションファイル（logs/<app_name>.log、30 日分保持）
- ログレベルは引数・環境変数 LOG_LEVEL で制御

---

## 主要モジュールの概要

- kabusys.config: 環境変数読み込み、Settings クラス（設定値の取得・バリデーション）
- kabusys.config_setup: .env 対話式ウィザード
- kabusys.validate_config: 起動前の設定検証 CLI
- kabusys.run_execution: ExecutionEngine 起動スクリプト
- kabusys.run_monitoring: SystemMonitor ポーリングループ起動スクリプト
- kabusys.monitoring:
  - monitoring_db: SQLite 永続化層（テーブル作成・Upsert 等）
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / alert_manager
- kabusys.execution: Execution エンジン関連（broker factory, order manager, risk manager, reconciler 等）
- kabusys.portfolio: 選定・重み付け・ポジションサイズ・リスク調整
- kabusys.research: ファクター計算・特徴量解析ユーティリティ（DuckDB 前提）
- kabusys.ai: news_nlp（ニュースセンチメント）, regime_detector（市場レジーム）
- kabusys.tools: 紙トレードレポート等ユーティリティ
- kabusys.utils: logging_setup, process_priority（プロセス優先度 / CPU affinity）

---

## ディレクトリ構成（抜粋）

（リポジトリの src/kabusys 配下を示します）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に使用するディレクトリ)
    - monitoring.db (デフォルト SQLite)
    - paper_trading.db (paper_trading 用)
    - kill.flag / stop_requested.flag / execution.pid
  - logs/ (ログファイル出力先、デフォルト)

---

## 運用上の注意・ベストプラクティス

- KABUSYS_ENV=live の場合は設定ミスが致命的になる可能性があります。validate_config の警告を必ず確認してください。
- kill.flag や stop_requested.flag などのフラグファイルによる停止制御は慎重に扱ってください。KILL_FLAG_CLEAR_ON_START を本番で1にするのは危険です。
- OpenAI API キーや外部トークン等は .env を Git に含めないでください（.gitignore へ追加）。
- DuckDB / SQLite のパスはバックアップ・保全を行ってください。paper_trading は本番データと分離されていますが、運用前にパスを念入りに確認してください。
- プロセス優先度や CPU affinity は環境により設定に失敗することがあります（権限不足）。ログを確認してください。

---

## 追加情報 / 開発者向け

- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って環境依存の自動読み込みを無効化できます。
- モジュールはできるだけ副作用が少ない純粋関数（research / portfolio 等）と I/O を行うコンポーネント（monitoring_db, execution engine 等）に分離されています。
- DuckDB を使った分析モジュールは SQL を直接実行する設計です。大規模データやパフォーマンス改善時はクエリ最適化やインデックス化を検討してください。

---

必要であれば、README に「設定ファイル例（.env.example）」や各モジュールの詳細な API 使用例（関数リファレンスやコードサンプル）を追加します。どのセクションをより詳しく補足しますか？