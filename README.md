# KabuSys

日本株向けの自動売買システム用ライブラリ / 実行スクリプト群です。  
このリポジトリには、戦略の研究用ユーティリティ、ポートフォリオ構築ロジック、監視・アラート、実行エンジン起動スクリプト、Paper Trading 検証ツール、LLM を使ったニュース NLP／レジーム検出などが含まれます。

概要・機能・セットアップ・使い方・ディレクトリ構成を以下にまとめます。

---

## プロジェクト概要
- 自動売買システムのコアロジック（ポートフォリオ構築、ポジションサイジング、リスク調整など）を提供する Python パッケージ。
- 実運用を想定した監視（SystemMonitor / TradeMonitor / RiskMonitor）と、条件に応じて ExecutionEngine を停止させる Kill Switch を備えています。
- Paper Trading 用に実運用 DB と分離された振る舞い（MockBroker 等）をサポート。
- DuckDB を用いたリサーチ / ファクター計算、SQLite を用いた運用ログ・監視データの永続化。
- OpenAI API（gpt-4o-mini 等）を用いたニュースセンチメント評価・マクロセンチメントによるレジーム判定機能あり（任意）。

---

## 主な機能一覧
- 実行・監視スクリプト
  - run_execution.py: ExecutionEngine 起動（Paper Trading 時は MockBroker を利用）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（監視ログを SQLite に保存）
- 設定管理 / 検証
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env / config/*.yaml の起動前検証 CLI
- 監視・リスク管理
  - monitoring_engine, system_monitor, risk_monitor, trade_monitor, kill_switch, monitoring_db
- ポートフォリオ構築
  - portfolio_builder, position_sizing, risk_adjustment（等金額／スコア加重／リスクベースの配分）
- リサーチ
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン計算、IC（Information Coefficient）など
- AI / NLP
  - ai.news_nlp: raw_news を LLM に投げて銘柄ごとのセンチメントスコアを ai_scores に保存
  - ai.regime_detector: ma200 とマクロセンチメントを合成して市場レジーム判定・保存
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成
- ユーティリティ
  - utils.logging_setup: 統一ログ設定（コンソール + 日次ローテート）
  - utils.process_priority: プラットフォーム依存を吸収したプロセス優先度設定

---

## セットアップ手順（開発環境向け）
1. リポジトリをクローンして Python 仮想環境を用意します。
   - 推奨 Python: 3.10+
2. 必要ライブラリをインストールします（少なくとも以下が必要）。
   - duckdb
   - psutil
   - openai（AI 機能を使う場合）
   - PyYAML（validate_config で YAML 検証を行う場合に任意）
   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```
   ※ requirements.txt が無い場合は上記を個別にインストールしてください。
3. .env を準備します（プロジェクトルートに配置）。
   - 対話式で作成するには:
     ```
     python -m kabusys.config_setup
     ```
   - 作成したら設定を検証:
     ```
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
     ```
4. データディレクトリ等は自動作成されますが、ログ出力先（既定: logs/）や data/ を手動で用意してもよいです。

---

## 主要な環境変数（抜粋）
- 必須（起動前に .env に設定してください）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境指定
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker を使用し、Paper 専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録
- データベース
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- OpenAI
  - OPENAI_API_KEY: ai.news_nlp / ai.regime_detector で使用
- ログ
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- 監視関連
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）（デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア、デフォルト: "0"）
  - PID_FILE_PATH / KILL_FLAG_PATH: 各種パス（Settings で確認）

その他、PAPER_FILL_MODE（instant/partial/never/reject）などが設定可能です。詳細は kabusys.config.Settings を参照してください。

自動的な .env 読み込み:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` と `.env.local` を自動読み込みします。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（代表的なコマンド）
- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- ExecutionEngine（取引エンジン）起動
  - 本番 / ペーパートレードは KABUSYS_ENV に従います
  ```
  python -m kabusys.run_execution
  ```
  - 起動では data/execution.pid（デフォルト）に PID を書きます。停止は data/stop_requested.flag を作成するか、Kill Switch の場合は data/kill.flag を書きます。
- Monitoring（SystemMonitor ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60）。
  - 停止はプロジェクトルート data/stop_requested.flag を作成して検知されます。
- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # SQLite パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
- AI スコア / レジーム判定（ライブラリ関数）
  - ai.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、DB に書き込みます。OPENAI_API_KEY を環境変数でセットするか、api_key を引数で渡してください。

注意:
- Paper Trading 時は本番監視 DB と分離して `data/paper_trading.db` を使います（Settings.is_paper に依存）。
- run_execution は内部で BrokerClientFactory を使い、KABUSYS_ENV=paper_trading の場合は MockBrokerClient を生成して実際の発注を行いません。

---

## ログ
- ロギングは kabusys.utils.logging_setup.setup_logging で統一的に設定されます。
- デフォルトで stdout に出力し、ファイルは daily ローテーションで logs/<app_name>.log に保存（30日分保持）。
- 起動スクリプトは setup_logging(app_name="execution" | "monitoring") を呼んでいます。

---

## 停止・Kill Switch の仕組み
- 実行中の ExecutionEngine を外部から停止する方法としてフラグファイルを使用します。
  - data/stop_requested.flag: run_execution/run_monitoring のループを止める単純な停止フラグ（スクリプトによって参照されます）
  - data/kill.flag: KillSwitch が検知条件（ドローダウン超過など）に合致した際に作成され、Execution を停止するシグナルとなります
- kill.flag の自動クリアは `KILL_FLAG_CLEAR_ON_START=1` で有効化できますが、本番では危険なのでデフォルトは 0（クリアしない）を推奨します。

---

## ディレクトリ構成（抜粋）
以下は src/kabusys 以下の主な構成です（重要ファイルの説明付き）。

- src/kabusys/
  - __init__.py (パッケージ定義、バージョン)
  - config.py (Settings クラス: 環境変数読み取り・自動 .env ロード)
  - config_setup.py (対話式 .env 作成ウィザード)
  - validate_config.py (起動前の設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリングループ起動スクリプト)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート)
  - ai/
    - news_nlp.py (ニュースを LLM でスコアリングし ai_scores に書き込む)
    - regime_detector.py (ma200 + マクロセンチメントでレジーム判定)
  - portfolio/
    - portfolio_builder.py (候補選定・重み計算)
    - position_sizing.py (株数決定・上限・ロット丸め)
    - risk_adjustment.py (セクターキャップ・レジーム乗数)
    - __init__.py
  - research/
    - factor_research.py (Momentum / Volatility / Value 等のファクター計算)
    - feature_exploration.py (将来リターン / IC / 統計サマリー)
    - __init__.py
  - monitoring/
    - monitoring_db.py (SQLite 永続化層 / DB 初期化)
    - system_monitor.py (システム状態・データ鮮度チェック)
    - risk_monitor.py (ドローダウン・ポジション上限監視)
    - trade_monitor.py (発注ログ監視 等)  ※実装ファイルあり（本リストでは抜粋）
    - monitoring_engine.py (各 Monitor の統合ポーリング)
    - kill_switch.py (Kill Switch 実装)
    - alert_manager.py (アラート送信管理)  ※実装ファイルあり（本リストでは抜粋）
  - utils/
    - logging_setup.py (ロギング初期化)
    - process_priority.py (プロセス優先度 / CPU affinity)
    - __init__.py
  - data/ (実行時に生成されることが想定)
    - *.db, *.pid, stop_requested.flag, kill.flag など

（注）この README はコードベースの主要モジュールを要約したものです。詳細は該当ソースファイルの docstring / コメントを参照してください。

---

## 開発時の注意点 / 補足
- DuckDB と SQLite の使い分け:
  - DuckDB: 研究・分析用（prices_daily, raw_financials 等）。高性能な集計やファクター計算に使用。
  - SQLite: 監視・発注ログ・ダッシュボード等の運用ログ（軽量永続化）に使用。
- Paper Trading:
  - KABUSYS_ENV=paper_trading を設定すると ExecutionEngine は MockBroker を使い、記録は paper_trading 用 DB に分離されます。
- OpenAI 呼び出し:
  - ネットワークエラーや 429/5xx は再試行ロジックを持ちますが、API キー未設定時は例外が上がる箇所があります。環境変数 OPENAI_API_KEY の設定を忘れないでください。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化できます。

---

必要であれば、README に実際の .env.example のサンプル、Docker / systemd 用の起動例、より詳細なアーキテクチャ図や各モジュールの API 使用例（関数シグネチャと簡単なコードスニペット）を追記できます。どの情報を追加したいか教えてください。