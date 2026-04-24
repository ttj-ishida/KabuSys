# KabuSys

日本株自動売買システムのサブセット実装。  
本リポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AIベースのニュース解析などを含むモジュール群を提供します。

> この README はソースコード中の docstring / コメントを基に作成しています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・研究基盤です。主な目的は以下です。

- 戦略に基づく発注（ExecutionEngine）
- 稼働監視とアラート（Monitoring）
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイジング）
- 研究用ファクター計算（DuckDB を用いた時系列処理）
- ニュースの NLP によるセンチメント評価（OpenAI API）
- ペーパートレード用機能と検証レポート作成

設計方針として、DB（SQLite / DuckDB）をデータ永続化・解析に用い、LLM 呼び出しは必要箇所のみ行いフェイルセーフ（API失敗時はフォールバック）を採用しています。

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカー選定（paper_trading 時は Mock）
  - OrderManager / RiskManager / Reconciler を含む実行パイプライン
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor: 発注ログの異常検出（滞留注文、約定異常など）
  - RiskMonitor: ドローダウン、ポジション数監視およびリスクログ記録
  - KillSwitch: 条件に応じた停止フラグ (data/kill.flag) の書き込み
  - MonitoringEngine: 各モニタを束ねたポーリングループ
- Portfolio
  - 候補選定、等分配・スコア加重、セクターキャップ適用、レジーム乗数
  - ポジションサイジング（リスクベース・等分配など）、単元数丸め・aggregate cap
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI
  - news_nlp: OpenAI を用いたニュースごとのセンチメントスコア生成（ai_scores テーブル書込）
  - regime_detector: ETF（1321）MA200乖離 + マクロニュースの LLM センチメントで日次レジーム判定
- ユーティリティ
  - 設定ウィザード（config_setup.py）: .env の対話的生成
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
  - 統一的なログ設定・プロセス優先度設定ユーティリティ

---

## セットアップ手順（開発・試用向け）

※ 実行はプロジェクトルート（pyproject.toml または .git があるパス）で行ってください。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低依存（必須 / 明示的に利用されているもの）:
     - duckdb
     - openai
     - psutil
   - 任意 / 検証用:
     - PyYAML（config/*.yaml の検証に使用）
   - 例:
     - pip install duckdb openai psutil pyyaml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用してください）

4. .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（下の「環境変数」を参照）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 重要: 本番環境では --strict を使うと警告も FAIL 扱いになります。

6. データディレクトリ
   - デフォルトで以下のファイル/ディレクトリが使用されます。必要に応じて .env で上書きしてください。
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
     - Kill / Stop フラグ: data/kill.flag, data/stop_requested.flag
     - PID ファイル: data/execution.pid

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（デフォルトあり / 任意で上書き）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- OPENAI_API_KEY: OpenAI 呼び出しに必要（news_nlp / regime_detector）
- PAPER_FILL_MODE: ペーパートレードの執行モード（instant, partial, never, reject）

実行時パラメータ（短期的な上書き）:
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

注意:
- .env は決して Git にコミットしないでください（config_setup でも同様に注意喚起あり）。
- validate_config によるチェックでは本番環境（KABUSYS_ENV=live）に関する追加警告が行われます（LINE 通知等）。

---

## 使い方（コマンド例）

- 設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

  実行の特徴:
  - Monitoring は常に settings.sqlite_path（本番 monitoring DB）を使用します（KABUSYS_ENV に依らず）。
  - 停止はデータディレクトリ内の data/stop_requested.flag を作成すると次ポーリングで検出して終了します。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution

  実行の特徴:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が既にある場合は起動を行いません。
  - 実行中に data/stop_requested.flag を作成すると安全に停止を試みます。
  - PID ファイルは data/execution.pid（デフォルト）に格納されます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: env PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- ライブラリ的利用（研究・ユーティリティ）
  - Python から各モジュールをインポートして使用できます。例:
    - from kabusys.research import calc_momentum
    - from kabusys.ai.news_nlp import score_news
  - OpenAI を使う関数は OPENAI_API_KEY の設定（または引数で api_key を渡す）を必要とします。

---

## 代表的なファイル / ディレクトリ構成

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み、Settings クラスを提供
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading モードをサポート）
  - utils/
    - logging_setup.py: 一貫したログ設定（stdout + 日次ローテーションファイル）
    - process_priority.py: プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py: SQLite の永続化層（テーブル作成・CRUD）
    - system_monitor.py: CPU/メモリ/ディスク、プロセス、データ鮮度監視
    - trade_monitor.py: trade_logs の監視（滞留注文、約定異常等）
    - risk_monitor.py: ドローダウン／保有数監視、リスクログ出力
    - monitoring_engine.py: 各モニタの束ね・ポーリング
    - kill_switch.py: data/kill.flag の作成（Execution 停止シグナル）
    - alert_manager.py:（アラート送信管理、コード上では参照箇所あり）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      - 発注ロジック・リスク管理・ブローカー抽象化
  - portfolio/
    - portfolio_builder.py, risk_adjustment.py, position_sizing.py
      - 候補選定、セクター上限、ポジションサイズ計算
  - research/
    - factor_research.py: momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py: 将来リターン・IC 等の研究補助
  - ai/
    - news_nlp.py: ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py: ETF MA200 + マクロニュースで日次レジーム判定
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート生成スクリプト

---

## 運用上の注意点 / ベストプラクティス

- .env は絶対にソース管理に含めないこと（config_setup でも注意表示あり）。
- KABUSYS_ENV=live を設定する際は validate_config の警告を必ず確認する（LINE 通知設定や Kill Switch 設定など）。
- OpenAI API や外部 API のキーは安全に管理する（環境変数 / シークレット管理ツールを利用）。
- Monitoring は本番監視用の DB（settings.sqlite_path）を使用します。監視ログは環境に依らず本番用パスで保存されるため、テスト時は注意して設定を分離してください（PAPER_TRADING_SQLITE_PATH は Execution 側で分離されますが、monitoring は分離されません）。
- 監視・実行を停止したい場合はプロジェクトルートの data/stop_requested.flag を作成すると安全に終了処理が走ります。KillSwitch（data/kill.flag）は ExecutionEngine 停止のためのより強いシグナルです。

---

## 参考コマンドまとめ

- 仮想環境作成・パッケージインストール:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb openai psutil pyyaml

- ウィザード・検証:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - python -m kabusys.run_execution

- レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

README はここまでです。必要があれば以下の点について README に追記します：
- 依存パッケージの具体的なバージョン提案（requirements.txt 生成）
- 各 CLI のより詳細なオプション説明
- 開発用テスト手順（ユニットテスト / モックの使い方）
どれを追加したいか教えてください。