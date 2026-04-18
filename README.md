# KabuSys

日本株向け自動売買システムの一部（ライブラリ＋起動スクリプト群）。  
このリポジトリは、実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）等のモジュールを含みます。

以下はこのコードベースの README です。

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成するモジュール群です。主な目的は以下：

- 戦略（シグナル）に基づく銘柄選定・配分・発注
- 発注エンジン（本番・ペーパートレード）と注文履歴の管理
- システム稼働監視とリスク監視（ドローダウン、ポジション上限など）
- ニュースの NLP によるセンチメント評価（OpenAI API を利用）
- 市場レジーム判定（MA とマクロニュースの組合せ）
- リサーチ用ファクター計算（DuckDB を利用したオフライン分析）
- 環境設定ウィザードと起動前設定検証ツール

設計方針として、DB（SQLite / DuckDB）による永続化と、環境変数による設定管理、フェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（本番/ペーパー両対応）
  - BrokerClientFactory（本番は実ブローカー、paper_trading では MockBrokerClient）
  - OrderRepository / OrderManager / Reconciler / RiskManager
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、プロセス生存チェック）
  - TradeMonitor（滞留注文 / 約定異常 等の検出）
  - RiskMonitor（ドローダウン監視、ポジション上限監視）
  - MonitoringEngine（上記を束ねてポーリング）
  - KillSwitch（条件に応じて data/kill.flag を書き込み ExecutionEngine を止める）
  - MonitoringDB（SQLite スキーマ管理＋読み書きユーティリティ）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア加重配分、リスクベース配分、セクター上限適用、ポジションサイズ計算（単元丸め・aggregate cap）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC 計算、統計サマリ
- AI
  - news_nlp: ニュースを OpenAI へ送り銘柄別センチメントを ai_scores に書き込む
  - regime_detector: ETF（1321）の MA とマクロニュースで日次レジームを判定
- ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証ツール（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 事前準備 / セットアップ手順

1. リポジトリをチェックアウト
   - git clone … / または適切にコードを配置

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール  
   必要な主なパッケージ（例）:
   - duckdb
   - psutil
   - openai
   - PyYAML (設定検証で YAML チェックを行う場合)
   - そのほかプロジェクト固有の依存がある場合は requirements.txt を参照してインストール

   例:
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を推奨）

4. ディレクトリ作成（ログ・DB・データ用）
   - mkdir -p data logs

5. 初期設定（.env）を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または .env を手動で作成（.env.example を参照）

6. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

7. データベース初期化
   - run_monitoring または run_execution 実行時に必要テーブルは作成されます（init_monitoring_db が起動時に冪等で作成）。

---

## 主要な環境変数（抜粋・デフォルト）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合必須）
- DUCKDB_PATH: DuckDB ファイルパス — デフォルト: data/kabusys.duckdb
- SQLITE_PATH: SQLite（監視） — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時使用） — デフォルト: data/paper_trading.db
- LOG_LEVEL: ログレベル — デフォルト: INFO
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1） — デフォルト: 0
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒） — デフォルト: 60（run_monitoring はこの環境変数で上書き可能）

注意:
- 自動で .env をロードする仕組みがあります（プロジェクトルートに基づく）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要スクリプト、実行例）

- 監視ループ起動（SystemMonitor をポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path を使用する（環境に関わらず monitoring DB は本番用を想定）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます
  - 停止フラグ: data/stop_requested.flag が存在すると起動を停止・終了します。エンジンは data/execution.pid を書きます。

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - 対話式に .env を生成/更新します

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / レジーム関連
  - ai の関数はモジュール API として利用可能（OpenAI API キーが必要）
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## ログ / ファイル / フラグ

- ログ:
  - デフォルト出力先: stdout と logs/<app_name>.log（日次ローテーション、30日保持）
  - setup_logging を全スクリプトで共通使用しているためログは一貫した形式

- DB:
  - DuckDB: data/kabusys.duckdb（デフォルト）
  - Monitoring SQLite: data/monitoring.db（デフォルト）
  - Paper trading SQLite: data/paper_trading.db（paper_trading 用、分離）

- PID / Stop / Kill フラグ:
  - data/execution.pid — ExecutionEngine が書き込む PID ファイル
  - data/stop_requested.flag — 外部からの「完全停止要求」用フラグ（run_monitoring/run_execution がチェック）
  - data/kill.flag — KillSwitch が書き込む ExecutionEngine 停止フラグ（設定次第で起動時に自動クリア可）

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py         — ログ設定
    - process_priority.py      — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ + 永続化層
    - system_monitor.py
    - trade_monitor.py         — （存在: モニタリングロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — （通知処理：LINE など）
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - tools/
    - paper_verification_report.py

（上記に加えて config/*.yaml などの設定ファイルが存在する想定）

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0（クリアしない）。
- データ鮮度・監視ログは monitoring.db に蓄積されます。バックアップ・ローテーション方針を検討してください。
- OpenAI を利用する処理は API 利用料金が発生するため、テストではモック化をおすすめします（テスト用に _call_openai_api をパッチ可能）。
- Paper trading モードは本番 DB と完全に分離されるよう設計されています。ペーパーデータは PAPER_TRADING_SQLITE_PATH に記録されます。
- プロセス優先度（set_process_priority）や CPU affinity は OS 権限に依存します。権限不足時はログに警告が出ますが処理は継続します。

---

## サンプルワークフロー（起動）

1. .env を作る（ウィザード推奨）
   - python -m kabusys.config_setup

2. 設定チェック
   - python -m kabusys.validate_config

3. 監視プロセスを起動（常駐）
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring &

4. 実行エンジンを起動（デイリー実行など）
   - python -m kabusys.run_execution

5. 必要に応じてツールでレポート作成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 開発 / テスト

- 単体関数群（portfolio, research, ai の内部ロジック）は外部副作用を持たない純粋関数として設計されています。ユニットテストが書きやすい構造です。
- OpenAI 呼び出しや psutil 等外部依存はテスト時にモック化してください（例: unittest.mock.patch）。

---

## ライセンス / バージョン

- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はこのリポジトリに含まれる LICENSE ファイルを参照してください（存在する場合）。

---

README に書かれている内容以外で知りたい箇所（設定項目の詳細、SQL スキーマ、実行エンジンの振る舞い、AI プロンプト調整方法など）があれば教えてください。必要に応じて README の追加セクションを作成します。