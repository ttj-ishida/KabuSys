# KabuSys

日本株自動売買システムのライブラリ兼実行スクリプト群です。本リポジトリは戦略・ポートフォリオ構築、実行エンジン、監視・アラート、研究用ファクター計算、そして OpenAI を利用したニュース NLP 等のコンポーネントから構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は次の目的を持つモジュール群を提供します。

- 自動売買の Execution Engine（発注管理・リスク管理・再調整等）
- 監視（System / Trade / Risk）と Kill Switch（危険時に Execution を停止する仕組み）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用ファクター計算・特徴量解析（DuckDB を用いたオフライン分析）
- Paper Trading 用の分離された DB と検証レポート生成ツール
- ニュースの LLM ベース・センチメント評価及びレジーム判定（OpenAI 使用）

設計方針の一部:
- 環境変数 / .env による設定管理（Settings クラス）
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- 監視は SQLite にログを永続化（monitoring.db）
- ロギングは統一されたセットアップ（ログは stdout と日次ローテートファイルに出力）

---

## 主な機能一覧

- 実行系
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - Broker の抽象化（本番 / Mock 切替）
  - リスク管理（最大ポジション比・利用率・ドローダウン等）
- 監視系
  - SystemMonitor, TradeMonitor, RiskMonitor（src/kabusys/monitoring/*）
  - MonitoringEngine によるポーリングループ（run_monitoring.py）
  - kill.flag による ExecutionEngine 停止シグナル
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- 研究（Research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ
- AI
  - ニュースのセンチメントスコアリング（OpenAI, gpt-4o-mini 想定）
  - レジーム判定（MA200 とマクロニュースを組み合わせる）
- ツール
  - Paper Trading 検証レポート生成（src/kabusys/tools/paper_verification_report.py）
- 設定支援
  - 対話式 .env 生成ウィザード（src/kabusys/config_setup.py）
  - 設定検証 CLI（src/kabusys/validate_config.py）
- ユーティリティ
  - 統一ロギングセットアップ（src/kabusys/utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（src/kabusys/utils/process_priority.py）

---

## 動作前提（推奨）

- Python 3.9+（typing の一部に新しい構文を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に YAML のパースを行う場合に推奨）
- SQLite（標準ライブラリで利用）

パッケージはプロジェクトに requirements.txt があればそれを使ってください。ない場合は上記を pip で個別インストールしてください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / 配布コードを展開

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - 主要項目（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等

5. 設定検証（任意、起動前推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告を FAIL 扱い（exit 1）

6. data/ ディレクトリ・ログディレクトリ等の作成は起動時に自動作成されますが、権限等で失敗する場合があるため確認してください。

---

## 使い方（主要コマンド例）

- ExecutionEngine を起動（デーモン化等は環境に応じて管理してください）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録します。

- Monitoring を起動（ポーリング）
  - MONITOR_POLL_INTERVAL 環境変数で秒間隔を上書き可能（デフォルト: 60）
  - python -m kabusys.run_monitoring
  - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用して監視ログを残します。

- .env を対話で作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db でデータベースパスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH で代替）

- AI スコアリング（プログラム的に呼び出し）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")

- レジーム判定（プログラム的に呼び出し）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key="...")

注意: AI 機能は OpenAI API キー（OPENAI_API_KEY 環境変数または引数）が必要です。

---

## 主要な環境変数（抜粋とデフォルト）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL — デフォルト: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用（任意）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- LOG_LEVEL: ログレベル（INFO 等）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の fill モード（instant / partial / never / reject）

詳細は src/kabusys/config.py と src/kabusys/config_setup.py の定義を参照してください。

---

## 停止・制御フラグ

- data/kill.flag: Kill Switch が書き込むファイル。存在すると ExecutionEngine 停止指示となります。
- data/stop_requested.flag: run_monitoring / run_execution の外部停止判定に使われます（存在するとループを抜けます）。
- data/execution.pid: 実行エンジンの PID ファイル（Execution 起動時に使用）。

Execution 起動時に kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）を設定できますが、本番では 0 を推奨します。

---

## ロギング

- 共通のセットアップ関数: kabusys.utils.logging_setup.setup_logging(app_name="execution" 等)
- ログ出力先:
  - stdout（StreamHandler）
  - 日次ローテートファイル: <LOG_DIR>/<app_name>.log（デフォルト LOG_DIR=logs/）
- ログのローテーションは 30 日分保持

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリの主要モジュールと配置の概略です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照のみ)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照のみ)
  - execution/
    - broker_factory.py (参照)
    - execution_engine.py (参照)
    - order_manager.py (参照)
    - order_repository.py (参照)
    - reconciler.py (参照)
    - risk_manager.py (参照)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/  ※実行時に生成されることが想定
  - logs/  ※ログ出力先（デフォルト）

（上の listing は抜粋です。実際のファイルはリポジトリ全体を参照してください。）

---

## 開発者向けのメモ / 安全上の注意

- Paper Trading は実環境と DB を分離する設計です。KABUSYS_ENV=paper_trading を正しく設定することで本番資金への発注を防げますが、設定ミスには注意してください。
- 本番（live）での起動前に必ず python -m kabusys.validate_config を実行し、設定を確認してください（LINE トークンや kill flag の設定等）。
- OpenAI 等の外部 API キーは絶対に .env をリポジトリにコミットしないでください。
- process_priority は psutil を使って優先度を上げますが、権限不足で失敗する可能性があります（警告ログでスキップされます）。
- ローカルでの検証や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます。

---

## 参考コマンドまとめ

- .env を作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

README に書かれている以上の詳細実装や追加の CLI はソースコード中の各モジュール（特に src/kabusys/*）を参照してください。質問や補足が必要であれば、どの部分について詳しく知りたいか教えてください。