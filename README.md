# KabuSys

日本株向け自動売買システムのコアライブラリ群です。戦略・ポートフォリオ構築、発注実行、監視、AI（ニュース NLP / レジーム判定）、リサーチ用ユーティリティを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動・ユーティリティ）
- 環境変数一覧（主要）
- ファイル・ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買に必要なコンポーネント群を提供します。
  - 発注エンジン（ExecutionEngine）
  - 監視（System / Trade / Risk Monitor）
  - ポートフォリオ構築（候補選定、重み付け、ポジションサイズ）
  - リサーチ（ファクター計算、特徴量探索）
  - AI 補助（ニュースのセンチメント評価、レジーム判定）
  - 各種ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、設定検証）
- 設計方針として、外部 API（kabuステーション / J-Quants / OpenAI 等）へのアクセスは設定で切替可能。paper_trading 環境ではモックブローカーと専用 DB を使用して本番 DB と分離します。

---

機能一覧
- Execution
  - ExecutionEngine：注文の管理・執行・リスク管理・和解処理（Reconciler）
  - BrokerClientFactory により本番 / ペーパートレード切替
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、実行プロセス死活監視
  - TradeMonitor / RiskMonitor：滞留注文・約定異常・ドローダウン・ポジション上限監視
  - KillSwitch：条件により停止フラグを書き、ExecutionEngine を停止
  - MonitoringDB：SQLite に監視ログを永続化
- Portfolio
  - 候補選定、等金額・スコア加重、セクター制限、レジーム乗数、ポジションサイジング（単元丸め）
- Research
  - ファクター計算（Momentum/Volatility/Value 等）、forward returns、IC 計算、統計サマリ
  - DuckDB を用いて高速に集計・演算
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント集計 → ai_scores に保存
  - regime_detector: MA とマクロニュースを合成して市場レジーム判定
- ユーティリティ
  - config_setup: .env の対話式ウィザード生成
  - validate_config: 起動前の設定検証 CLI（--strict オプションあり）
  - tools.paper_verification_report: ペーパートレードの検証レポート生成
  - logging_setup: 一貫したログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし仮想環境を作成
   - 推奨: Python 3.10+
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install --upgrade pip
     ```
2. 必要なパッケージをインストール
   - 主要依存:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（validate_config の YAML 検証に使用）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - （requirements.txt がない場合は上記を個別にインストールしてください）

3. 環境変数設定（.env）
   - 対話式ウィザードで .env を作成できます:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env を手動作成してください（.env.example を参照）。
   - 重要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - KABUSYS_ENV は以下のいずれか: development / paper_trading / live
     - paper_trading の場合、発注はモックとなりデータは data/paper_trading.db に記録されます（本番 DB と完全分離）。

4. DB・ディレクトリ
   - デフォルトで次を使用（必要に応じて .env で上書き）
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - logs ディレクトリは起動時に自動作成されます（権限がない場合はコンソール出力のみにフォールバック）。

---

使い方（主要コマンド）
- 設定ウィザード（.env を生成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
  ```

- ExecutionEngine を起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 起動時に data/execution.pid（デフォルト）に PID を書きます。停止には data/stop_requested.flag を作成するか、KillSwitch が data/kill.flag を書きます。
  - 起動直後に KILL_FLAG_CLEAR_ON_START=1 を有効にすると既存の kill.flag を自動でクリアします（本番では推奨しません）。

- Monitoring を起動（監視ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に関わらず同一の monitoring DB を参照します）。
  - 停止は data/stop_requested.flag を作成することで検知されます。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプション、あるいは環境変数 PAPER_TRADING_SQLITE_PATH で DB ファイルを指定可能。

- AI モジュール（ニュース NLP / レジーム判定）
  - OpenAI を使うため、環境変数 OPENAI_API_KEY を設定してください（または関数引数で渡す）。
  - news_nlp.score_news / regime_detector.score_regime を呼び出して利用します。

ログの出力
- logs/<app_name>.log に日次ローテーションで出力（backupCount: 30 日分）。
- コンソール出力は stdout に出力されます。

プロセス優先度
- 起動スクリプトは起動直後に set_process_priority("high") を試みます（プラットフォームに依存）。

停止フラグ / Kill Switch
- 手動停止フラグ:
  - data/stop_requested.flag — run_execution / run_monitoring がループ内で検知して終了します
- 自動停止（リスクトリガ）:
  - KillSwitch は条件により data/kill.flag を書き込み、ExecutionEngine の安全停止を促します
  - KILL_FLAG_CLEAR_ON_START 環境変数 = "1" で起動時に kill.flag を自動クリアできます（本番は推奨しない）

---

主要環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- オプション / 重要
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR（デフォルト INFO）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant|partial|never|reject）

設定ファイルの自動読み込み
- プロジェクトルート（.git または pyproject.toml がある場所）から .env を自動読み込みします:
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

---

ディレクトリ構成（主要）
- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — Monitoring ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py   — ペーパートレード検証ツール
  - execution/                       — 発注関連（BrokerFactory, Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py              — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/                       — portfolio_builder, position_sizing, risk_adjustment
  - research/                        — factor_research, feature_exploration, etc.
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - logging_setup.py               — ログ設定ユーティリティ
    - process_priority.py            — プロセス優先度 / affinity
  - data/ (実行時に使用・生成されることが多い)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - execution.pid
    - kill.flag / stop_requested.flag

---

補足・注意事項
- paper_trading モードは本番 DB／ブローカーとは分離されるよう設計されています。実運用では KABUSYS_ENV=live を慎重に扱ってください。
- OpenAI API を使う機能は外部通信とコストを伴います。API キーと利用上限を適切に管理してください。
- validate_config や config_setup を使って起動前に設定をチェックしてください。validate_config は PyYAML がインストールされている場合に config/*.yaml の構文チェックも行います。
- ログディレクトリの作成やファイル書き込みに失敗した場合、ログはコンソール（stdout）のみになります。

---

開発者向け
- テストでは環境依存の自動読込を無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使えます。
- AI 呼び出し部は _call_openai_api 等が分離されているため、ユニットテスト時はモック置換が可能です（unittest.mock.patch を推奨）。

---

お問い合わせ / 参考
- この README はコードベース（src/kabusys 以下）の実装から生成されています。追加の操作手順や運用手順（デプロイ、サービス化、監視アラートの運用フロー等）は別途ドキュメント化してください。