# KabuSys

日本株向け自動売買システム（ライブラリ + 起動スクリプト群）

このリポジトリは、シグナル生成 → ポートフォリオ構築 → 発注（実環境 / ペーパートレード） → 監視・アラートまでを含む総合的なシステム実装の一部です。モジュールはテスト可能な純粋関数と、実行時に使うエンジン／ユーティリティ群で構成されています。

バージョン: 0.1.0

---

## 概要（Project overview）

- 株価データの分析・ファクター計算（research）
- ポートフォリオ構築・ポジション決定ロジック（portfolio）
- 発注エンジン（ExecutionEngine）と MockBroker（paper_trading 対応）
- 監視（System / Trade / Risk）と Kill Switch、アラート管理
- ニュース NLP（OpenAI）を用いたセンチメントスコア（ai）
- ユーティリティ（設定読み込み・ログ設定・プロセス優先度など）
- 運用支援ツール（config ウィザード・設定検証・紙トレ検証レポート）

設計方針の一例:
- 本番用の DB/ファイルパスは環境変数で切り替え可能
- ペーパートレードは本番 DB と分離（data/paper_trading.db）
- ルックアヘッドバイアスを避ける設計（date.today() 等を直接参照しない）

---

## 主な機能一覧（Features）

- 設定管理
  - .env 自動読み込み（.env / .env.local）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 発注・実行
  - ExecutionEngine（run_execution.py から起動）
  - Broker クライアントファクトリ（実口座 / Mock 切替）
  - リスク管理（利用率・ポジション上限・サーキットブレーカー）
- 監視
  - SystemMonitor, TradeMonitor, RiskMonitor の定期ポーリング
  - Kill Switch（条件成立で data/kill.flag を書き込み Execution を停止）
  - monitoring.db (SQLite) に監視ログを永続化
- 研究・分析
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン / IC 計算等の統計解析ツール
- AI（任意）
  - ニュース記事を OpenAI に投げて銘柄毎のセンチメントを計算（ai.news_nlp）
  - 市場レジーム判定（ai.regime_detector）
- 運用ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- ロギング・運用ユーティリティ
  - 統一的ログ設定（logs/ 日次ローテーション）
  - プロセス優先度／CPU affinity 設定ユーティリティ

---

## 必要環境（Requirements）

- Python 3.10 以上（注: 型注釈に `X | Y` を使用）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証時に YAML の内容検査を行う場合）
- 例: pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がある場合はそれを利用してください。）

---

## セットアップ手順（Setup）

1. リポジトリを取得
   - git clone … && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai PyYAML

4. 初期設定ファイルを作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参照）

5. 設定検証（起動前に必ず確認）
   - python -m kabusys.validate_config
   - 厳密モード（警告があれば失敗扱い）:
     - python -m kabusys.validate_config --strict

6. データディレクトリ等の準備
   - デフォルト SQLite / DuckDB ファイルは `data/` 配下（自動作成されることが多い）
   - ログ出力は `logs/`（設定で変更可）

---

## 使い方（Usage）

### 環境変数（主要）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading 時は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能を有効化する場合に必須
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant/partial/never/reject）
- LOG_LEVEL / LOG_DIR: ログ設定

自動読み込みはデフォルトで .env / .env.local を拾います。自動読み込みを無効にする:
- export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

### 実行スクリプト

- ExecutionEngine を起動（通常はデーモンや supervisor から実行）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、ログは data/paper_trading.db に記録されます（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在する場合は起動を行いません。
    - エンジンの PID は data/execution.pid に書き込まれます。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 特記事項:
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使って監視データを永続化します
    - 停止はプロジェクトルート/data/stop_requested.flag を作成すると検知して終了

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db path/to/paper_trading.db
    - 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能

### 停止 / Kill Switch

- Kill Switch（自動停止）:
  - 条件を満たすと monitoring 側で data/kill.flag を書き込み、ExecutionEngine の起動中にそれを検知すると停止します。
- 手動停止
  - プロジェクトルートの data/stop_requested.flag を作成すると run_execution/run_monitoring のループが安全に終了します。

---

## 主要モジュール説明（短い紹介）

- kabusys.config: 環境変数/.env 読み込みと Settings クラス
- kabusys.config_setup: .env を対話式に作るウィザード
- kabusys.validate_config: 起動前の設定検証ツール
- kabusys.run_execution: ExecutionEngine 起動スクリプト
- kabusys.run_monitoring: SystemMonitor 等をポーリングする監視スクリプト
- kabusys.monitoring.*: MonitoringDB, SystemMonitor, RiskMonitor, TradeMonitor, KillSwitch, MonitoringEngine, Alert 管理
- kabusys.execution.*: 発注関連コンポーネント（BrokerFactory, Engine, OrderManager, RiskManager 等）
- kabusys.portfolio.*: 銘柄選定 / ウェイト計算 / リスク調整 / 建玉計算
- kabusys.research.*: ファクター計算・特徴量探索（DuckDB 経由で prices_daily などを参照）
- kabusys.ai.*: ニュース NLP（OpenAI）・レジーム判定
- kabusys.utils: logging_setup（統一ログ設定）、process_priority（優先度設定）等
- kabusys.tools: 運用補助スクリプト（紙トレ検証レポートなど）

---

## ディレクトリ構成（Directory structure）

（一部抜粋）

- src/
  - kabusys/
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
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - tools/
      - paper_verification_report.py
  - (その他ライブラリ・スクリプト)

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

- data/
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパートレード)
  - kill.flag
  - stop_requested.flag
  - execution.pid

- logs/
  - execution.log
  - monitoring.log
  - ...（日次ローテーション）

---

## 運用上の注意（Notes / Best practices）

- 本番環境（KABUSYS_ENV=live）では .env の管理・秘密情報の扱いを厳格にしてください（.env は絶対にコミットしない）。
- validate_config を起動前に必ず実行して、必須環境変数やパスをチェックしてください。
- Paper trading は本番 DB と切り離されていますが、ファイルパスは環境変数で上書き可能です。
- OpenAI を利用する機能は API キーの漏洩やコストに注意してください。API 失敗時はフェイルセーフとしてスコア 0 やスキップする実装が入っていますが、運用ポリシーを決めてください。
- ロギングはデフォルトで stdout と logs/ に出力します。ログディレクトリが作成できない環境ではコンソールのみになります。

---

## 貢献 / 開発

- 新しい設定項目を追加する際は config_setup.py / validate_config.py / config/*.yaml を更新してください。
- DB スキーマ変更は monitoring_db.init_monitoring_db にマイグレーション処理を追加してください（既存 DB を壊さないこと）。
- テストを書く際は環境依存を切り離し、Settings の読み込みを制御するか KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

もし README に追記してほしい内容（API の詳細な使い方、ユースケース別の起動例、依存関係の exact versions など）があれば教えてください。