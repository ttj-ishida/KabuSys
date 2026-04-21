# KabuSys

日本株自動売買システムの軽量フレームワーク（ライブラリ兼実行スクリプト群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネント群を提供するプロジェクトです。  
主な機能は以下の通りです：

- 注文の作成・管理・約定処理を行う ExecutionEngine（発注エンジン）
- システム稼働状況・注文ログ・リスク監視を行う Monitoring
- ポートフォリオ構築・銘柄選定・ポジションサイジングのユーティリティ群
- DuckDB を用いたリサーチ/ファクター計算モジュール
- ニュースを LLM（OpenAI）で評価する NLP / 市場レジーム判定モジュール
- 環境設定ウィザード、設定検証ツール、Paper Trading 検証レポート等のユーティリティ

設計方針として、データ永続化（SQLite / DuckDB）を明確に分離し、本番とペーパートレードを分けて運用できるようになっています。

---

## 主な機能一覧

- Execution
  - 実際のブローカークライアント／Mock クライアント（ペーパートレード）を切り替え可能
  - 注文管理（OrderManager / OrderRepository）
  - リスク管理（RiskManager）
  - Reconciler による注文照合
- Monitoring
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - SystemMonitor, TradeMonitor, RiskMonitor を束ねる MonitoringEngine
  - Kill Switch によるフラグファイル（data/kill.flag）を書き込んで ExecutionEngine を安全停止
  - ポーリング間隔を環境変数で指定可能（MONITOR_POLL_INTERVAL）
- Portfolio（純粋関数群）
  - 銘柄選定（select_candidates）
  - 重み計算（等分配・スコア加重）
  - セクター制約・レジーム乗数
  - ポジションサイズ算出（lot 単位丸め・aggregate cap）
- Research
  - DuckDB 経由でファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算 / IC 計測 / ファクター統計
- AI（OpenAI）
  - ニュースのセンチメント評価（ai.news_nlp.score_news）
  - マクロニュース + ETF MA による市場レジーム判定（ai.regime_detector.score_regime）
- ツール
  - .env 対話ウィザード（config_setup）
  - 設定検証（validate_config）
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）
- ユーティリティ
  - 統一的なログ設定（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）

---

## 前提 / 推奨環境

- Python 3.10 以上（PEP 604 の型記法などを利用）
- 必要な Python パッケージ（主要）:
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML - validate_config の YAML 検証に使用
- 標準で SQLite3 は利用

（プロジェクトに requirements.txt がない場合は上記パッケージを pip で個別インストールしてください）

---

## インストール（例）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. リポジトリのルートで以下を確認（data, logs ディレクトリは自動生成される場合があります）:
   - data/: デフォルト DB / flag / pid ファイル格納先
   - logs/: ログ出力先（utils.logging_setup が生成）

---

## 環境変数（重要）

主な必須/推奨環境変数：

必須
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（デフォルトあり）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - paper_trading の場合、発注は MockBrokerClient を使用し data/paper_trading.db に記録します
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- LOG_LEVEL: INFO 等
- LOG_DIR: ログ格納ディレクトリ
- OPENAI_API_KEY: OpenAI の API キー（AI モジュールを利用する場合）

その他
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（注意: 本番では 0 推奨）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant | partial | never | reject）

.env の初期作成は次節のウィザードを推奨します。

---

## .env 作成 / 設定検証

1. 対話型ウィザードで .env を作成:
   - python -m kabusys.config_setup
   - 指示に従って値を入力してください（シークレット項目はマスク表示されます）

2. 設定検証:
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

validate_config は .env の他に config/*.yaml の存在や DB パスの親ディレクトリ有無等をチェックします。PyYAML がインストールされていると YAML のパースも行います。

---

## 実行方法

注意: 本番で実行する前に必ず validate_config で設定を確認してください。KABUSYS_ENV=live の場合は慎重に設定を確認してください。

1. ExecutionEngine（発注エンジン）を起動
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録します
     - 起動時に data/stop_requested.flag が存在すると起動しません
     - 起動中に data/stop_requested.flag を作成するとエンジンを停止します
     - 実行時に data/execution.pid が作成されます

2. Monitoring（監視ループ）を起動
   - python -m kabusys.run_monitoring
   - 挙動:
     - MONITOR_POLL_INTERVAL（秒）で SystemMonitor.check_once() を呼び続けます（デフォルト 60 秒）
     - 監視は設定にかかわらず本番（settings.sqlite_path）を使用して monitoring DB に書き込みます
     - data/stop_requested.flag を検知すると監視ループを終了します

3. Paper Trading 検証レポート（1回レポート出力）
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで別 DB を指定可能（優先度: --db > 環境変数 > デフォルト data/paper_trading.db）

4. AI / リサーチ関数の利用（プログラムから呼び出す）
   - ai.news_nlp.score_news(conn, target_date, api_key=None) — OpenAI API キーは api_key 引数か OPENAI_API_KEY 環境変数から取得
   - ai.regime_detector.score_regime(conn, target_date, api_key=None)

（これらはライブラリ関数なので、DuckDB 接続オブジェクトを作成して呼び出します）

---

## 停止・Kill Switch の扱い

- ExecutionEngine 停止要求:
  - data/stop_requested.flag を作成すると run_execution のスレッドループが停止します（stop_requested.flag は run_* スクリプトが参照）
- Kill Switch:
  - リスク監視により条件を満たすと kill.flag を作成します（Settings.kill_flag_path、デフォルト data/kill.flag）
  - kill.flag が存在すると ExecutionEngine 停止や再起動の制御に利用されます
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）

---

## ログ

- 標準出力（stdout）と日次ローテーションファイル（logs/<app_name>.log）に出力されます
- ログ設定は kabusys.utils.logging_setup.setup_logging(app_name="...") で統一されています
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で指定可能

---

## デフォルトファイルパス（主なもの）

- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db
- PID: data/execution.pid
- stop flag: data/stop_requested.flag
- kill flag: data/kill.flag
- Logs: logs/<app_name>.log

これらは Settings クラス（kabusys.config.Settings）で取得・上書きが可能です。

---

## ディレクトリ構成

（src/kabusys 配下を抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定管理
    - config_setup.py           — .env 対話ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py
    - execution/                — 発注関連（Engine, OrderManager, BrokerFactory, Reconciler, RiskManager 等）
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

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください）

---

## 開発 / 拡張のポイント

- DuckDB を使ったリサーチ系モジュールは副作用がない純粋関数として設計されています（テストが容易）
- MonitoringDB（SQLite） はシンプルな CRUD 層に集中しており、ビジネスロジックは監視モジュール側にあります
- OpenAI 呼び出しは再試行・バリデーション等を行うよう設計され、部分的失敗が他データを破壊しないよう配慮されています
- 本番（live）動作時は KILL_FLAG_CLEAR_ON_START 等の設定に十分注意してください

---

## 注意事項（重要）

- KABUSYS_ENV=live にした場合は実際に発注が行われます。設定・資金・API アクセス権を慎重に確認してください。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- OpenAI API キーなど外部サービスの利用はコスト・レート制限を考慮してください。
- 本リポジトリは運用ツール群を想定しており、運用監視・アラート回路は必ず導入してください。

---

必要であれば、README にサンプル .env のテンプレート、コマンド例（systemd / supervisor 用のサービス定義例）、開発用ユニットテストの実行方法なども追記できます。どの情報を追加しますか？