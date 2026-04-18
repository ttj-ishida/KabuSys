# KabuSys

日本株向け自動売買システム（KabuSys）  
このリポジトリは、戦略・ポートフォリオ構築・発注エンジン・監視・研究ツールを含む自動売買プラットフォームの実装です。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要機能を備えた日本株自動売買システムです。

- 戦略・ファクター計算（DuckDB を用いた過去データ解析）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算）
- ExecutionEngine（ブローカークライアントを用いた発注管理、ペーパートレード対応）
- 監視（System / Trade / Risk モニタ、Kill Switch による自動停止）
- AI 補助（ニュース NLP によるセンチメント集計、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading レポート）

設計方針として、本番 DB とペーパートレード DB は分離され、LLM（OpenAI）呼び出しは失敗時フェイルセーフとなるよう実装されています。

---

## 主な機能一覧

- config/CLI:
  - .env を対話的に作成する `kabusys.config_setup`（ウィザード）
  - 設定の静的検証 `kabusys.validate_config`

- 実行関連:
  - `run_execution.py`：ExecutionEngine を起動（KABUSYS_ENV=paper_trading では MockBrokerClient を使用し、data/paper_trading.db を使用）
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔設定可能）

- 監視:
  - system_monitor, trade_monitor, risk_monitor：定期チェックとログ記録
  - monitoring_db：SQLite を用いた監視ログ（system_status, trade_logs, risk_logs, positions, dashboard）
  - KillSwitch：閾値超過時に data/kill.flag を作成

- ポートフォリオ構築:
  - 銘柄選定、等配分 / スコア配分、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数の適用

- 研究（research）:
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算・統計サマリ

- AI（OpenAI）:
  - news_nlp.score_news：ニュース記事を LLM でスコアリングして ai_scores に格納
  - regime_detector.score_regime：ETF の MA200 とマクロニュースを合成して市場レジーム判定

- ツール:
  - tools/paper_verification_report.py：ペーパートレード DB を集計して PASS/FAIL を出す検証レポート生成

- ロギング／ユーティリティ:
  - 統一されたログ設定（logs/*.log、stdout 出力）
  - プロセス優先度設定、CPU affinity（psutil 利用）
  - .env の自動読み込み（プロジェクトルート判定に基づく）

---

## 必要環境（推奨）

- Python 3.10+
- SQLite（標準ライブラリで利用可能）
- 外部パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML のパースを行う場合に必要）
- ネットワーク：OpenAI を利用する場合は API キーとネットワーク接続が必要

例（pip）:
pip install duckdb psutil openai PyYAML

※パッケージ群はプロジェクトに requirements.txt があればそちらを利用してください。

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai PyYAML

4. .env の作成（ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードの指示に従って .env を生成してください

   もしくは手動で .env を作成（最低限必須なのは JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD）:

   例（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=your_token_here
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   ```

   ウィザードはデフォルト値や秘密情報のマスク表示に対応しています。

5. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数や config/*.yaml の存在などをチェックします
   - --strict を付けると警告もエラー扱いになります

6. データディレクトリ／ログディレクトリの準備
   - デフォルトでは data/ と logs/ にファイルを出力します。自動作成されますが権限等に注意してください。

---

## 使い方（主要コマンド）

- 実行エンジン起動（ExecutionEngine）
  - 本番/ペーパートレード共通:
    - python -m kabusys.run_execution
  - KABUSYS_ENV 環境変数が `paper_trading` の場合は MockBrokerClient を利用し、データは `data/paper_trading.db` に記録されます。
  - 起動前に `data/stop_requested.flag` が存在すると起動を中止します。
  - 停止するには `data/stop_requested.flag` を作成するか、Kill Switch により `data/kill.flag` が書き込まれます。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視スクリプトは monitoring 用の sqlite DB（Settings.sqlite_path）を使用します（環境にかかわらず本番 sqlite_path を参照する設計）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラムから呼ぶ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは環境変数 OPENAI_API_KEY で渡すか、関数引数で指定します。

---

## 主な環境変数（抜粋・説明）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: ペーパートレードモード（本番 DB と分離）
  - live: 実運用（注意して設定）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill Switch 用フラグファイル（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）

詳細は `kabusys.config.Settings` と `kabusys.config_setup` を参照してください。

---

## 停止・Kill Switch 周り

- 停止フラグ:
  - data/stop_requested.flag を監視用スクリプト（run_monitoring, run_execution）でチェックして、存在時にループを中断します。
- Kill Switch:
  - リスク閾値（ドローダウン超過やポジション上限超過）により `data/kill.flag` を書き込みます。KillSwitch は既存の flag を上書きしません（冪等）。
  - KillSwitch.clear()（プログラム経由）または手動でファイルを削除すると解除できます。

---

## ロギング

- ログ出力はデフォルトで stdout（コンソール）とファイル（logs/<app_name>.log、日次ローテーション）に出力されます。
- ログ設定は `kabusys.utils.logging_setup.setup_logging(app_name="execution")` の呼び出しで統一されます。
- ログレベルは環境変数 LOG_LEVEL、または setup_logging の引数で制御可能です。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要構成です（抜粋）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理
  - config_setup.py           — .env ウィザード CLI
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP (OpenAI) スコアリング
    - regime_detector.py      — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — SQLite 用永続化層
    - system_monitor.py
    - trade_monitor.py        — （実装あり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （通知ロジック）
  - execution/
    - execution_engine.py     — ExecutionEngine（発注セッション管理）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py              — データ取得 / 最終日取得ユーティリティ など
    - stats.py                 — 正規化ユーティリティなど
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/                — 監視関連（上記）
  - tools/                     — 運用ツール（上記）

（実際のリポジトリにはさらにファイルやサブモジュールがあります。全体ツリーは `tree src/kabusys` 等で確認してください。）

---

## 開発・運用上の注意

- KABUSYS_ENV=live のときは設定内容を慎重に確認してください（Kill Switch / LINE 通知設定など）。
- OpenAI など外部 API に依存する機能は、API 失敗時フェイルセーフで動作しますが、本番ではレート制限やコストに留意してください。
- run_execution は paper_trading モード時に発注を完全に分離して記録します。実運用時は paper_trading ではない状態で慎重に試験してください。
- DuckDB / prices_daily / raw_financials 等の初期データロードは別途必要です（このリポジトリはデータ収集パイプラインも含む場合があります）。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 参考・補足

- 設定や挙動の詳細は `src/kabusys/*.py` のドキュメンテーション文字列（docstring）を参照してください。
- DB スキーマやマイグレーションは `kabusys.monitoring.monitoring_db.init_monitoring_db` の定義に従います。
- LLM / OpenAI 関連の呼び出しは `kabusys.ai` 配下に実装されており、テスト時は API 呼び出し関数をモックすることを推奨します。

---

以上。README の補足や特定機能のドキュメント化（例: ExecutionEngine の起動引数、OrderRepository の仕様、DuckDB テーブル定義など）が必要であれば、追加で作成します。