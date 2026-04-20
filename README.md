# KabuSys

日本株向けの自動売買システム（プロトタイプ）。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、AI を使ったニュースセンチメント/レジーム判定などのコンポーネントを含むモジュール群です。

主な設計方針:
- モジュール分割により研究（Research）と本番処理（Execution/Monitoring）を分離
- DuckDB を用いた時系列・ファクターデータ分析、SQLite を用いた監視/発注ログ
- Paper Trading（ペーパートレード）用の DB 分離
- OpenAI を用いたニュース NLP（オプション）
- 起動スクリプトはプロセス優先度設定・PID 管理・停止フラグに対応

バージョン: 0.1.0

---

## 機能一覧

- Execution（ExecutionEngine）
  - ブローカークライアント（実口座 or Mock）
  - 注文管理、リスク管理、リコンサイル
  - Paper Trading 時は専用 SQLite（data/paper_trading.db）へ記録

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - TradeMonitor: 注文の滞留や約定異常検出（trade_logs）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止

- Portfolio construction
  - 候補選定、等配分／スコア配分、ポジションサイジング、セクター上限・レジーム乗数など

- Research
  - factor_research: Momentum/Value/Volatility 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン、IC 計算、統計サマリー

- AI
  - news_nlp: OpenAI を用いたニュースセンチメント集約・ai_scores 書き込み
  - regime_detector: ETF MA とマクロニュースを組み合わせた市場レジーム判定

- Utilities / Tools
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 起動前に環境変数・config/*.yaml を検証
  - tools.paper_verification_report: Paper Trading 検証レポート生成

---

## 要件（主な依存）

- Python 3.9+
- 必要ライブラリ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config 検証で YAML 検査を行う場合）
- SQLite（標準ライブラリに含まれる）
- ネットワークアクセス（実運用・API 利用時）

実際のインストール時はプロジェクトの pyproject.toml / requirements ファイルをご参照ください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python の仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
     （必要に応じてプロジェクトの requirements を使ってください）
4. 環境変数設定
   - 対話式で .env を作る:
     - python -m kabusys.config_setup
   - または .env を直接作成（下記「重要な環境変数」を参照）
5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱う
6. データディレクトリ作成
   - デフォルトの DB / ログ保存先は data/、logs/。自動生成されるが権限確認を推奨

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
  - paper_trading の場合、発注はモック。paper_trading 用 DB は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp/regime_detector）で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（上記参照）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログファイル保存先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（開発用、デフォルト 0）

例（.env の一部）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxx

---

## 使い方（起動・各種コマンド）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録
    - プロセス優先度を high に設定
    - data/stop_requested.flag が存在すると起動を中止または停止
    - PID ファイルは data/execution.pid（Settings.pid_file_path）

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数で秒間隔をオーバーライド可能（デフォルト 60）
    - 監視データは sqlite_path（Settings.sqlite_path）へ格納
    - stop_requested.flag を検知し終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数を上書き可能）

- AI 関連（ライブラリ関数として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り内部でテーブルを読み書きします。API キー未設定時は例外になります。

ログ:
- ログは標準出力と logs/<app_name>.log（日次ローテーション）に出力されます。
- app_name は起動スクリプト（execution / monitoring）で指定されています。

停止方法:
- 実行中のプロセスを止めるには stop_requested.flag（data/stop_requested.flag）を作成することで優雅に停止します。
- KillSwitch（データに基づく自動停止）は data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります。

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py
  - パッケージ定義（__version__ 等）
- config.py
  - 環境変数/.env ロードと Settings クラス
  - 自動でプロジェクトルートの .env/.env.local を読み込む（無効化可能）
- config_setup.py
  - 対話式 .env 生成ウィザード
- validate_config.py
  - .env と config/*.yaml の検証 CLI

run_*.py
- run_execution.py
  - ExecutionEngine 起動スクリプト（プロセス優先度設定、DB 接続、PID 管理、停止フラグ）
- run_monitoring.py
  - Monitoring のポーリングループ起動スクリプト

ai/
- news_nlp.py
  - OpenAI を用いたニュースセンチメント集計・ai_scores への書き込み
- regime_detector.py
  - ETF MA とマクロニュースを合成して market_regime に書き込む

monitoring/
- monitoring_db.py
  - SQLite の監視用テーブル作成・CRUD ラッパー（MonitoringDB）
- system_monitor.py
  - システム状態 & データ鮮度監視
- trade_monitor.py (コード断片では省略されているが監視機能あり)
- risk_monitor.py
  - ドローダウン・ポジション上限監視（RiskMonitor）
- kill_switch.py
  - kill.flag の作成/管理（KillSwitch）
- monitoring_engine.py
  - 個別 Monitor を束ねてポーリング・アラートを行う

execution/
- broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - 発注処理・ブローカ抽象化・リスク管理・注文ログ周り（コードベース参照）

portfolio/
- portfolio_builder.py
  - 候補選定・重み計算
- position_sizing.py
  - 発注株数計算（リスクベース／等配分等）
- risk_adjustment.py
  - セクターキャップ・レジーム乗数適用

research/
- factor_research.py
  - Momentum, Value, Volatility 等のファクター計算（DuckDB）
- feature_exploration.py
  - 将来リターン, IC 計算, 統計サマリー

utils/
- logging_setup.py
  - 統一的なログ設定ユーティリティ（stdout + TimedRotatingFileHandler）
- process_priority.py
  - Windows/Linux の差を吸収してプロセス優先度・CPU affinity を設定

tools/
- paper_verification_report.py
  - Paper Trading の検証・合否判定レポート出力

その他:
- data/: デフォルトの DB / PID / フラグを置くディレクトリ（data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag など）
- logs/: デフォルトのログ保存先

---

## 運用の注意点 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にし、LINE 通知などアラート設定を必ず確認してください。
- Paper Trading は本番 DB と完全分離されています。paper_trading モード時は PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI を使う機能は API 呼び出しにコストとレイテンシが発生します。API キー・利用量管理に注意してください。
- ログディレクトリや DB ファイルのディスク容量を監視してください（特に DuckDB のサイズ）。
- PID / フラグファイルのパーミッション・クリア操作には注意。プロセス異常時はこれらのファイルを確認してください。

---

README はプロジェクトの主要な起点情報をまとめたものです。実装の詳細・API の使い方は各モジュールの docstring / ソースコメントを参照してください。追加の説明や別フォーマット（英語版・簡略版など）が必要であれば教えてください。