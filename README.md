# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ向け README（日本語）

この README はリポジトリ内の主要スクリプト・モジュールを参照して作成しています。実行スクリプトや設定ウィザード、監視・ペーパートレード検証ツールなどを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を備えるモジュール群です。

- 戦略の研究（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算）
- 実行エンジン（ExecutionEngine）と注文管理（実際のブローカ or モック）
- 監視コンポーネント（System / Trade / Risk の定常チェック、Kill Switch）
- AI 支援モジュール（ニュース NLP によるセンチメント、レジーム判定）
- ペーパートレード用 DB と検証レポート出力ツール
- ロギング、環境設定ウィザード、設定検証 CLI

設計方針の一部:
- 本番 DB とペーパートレード DB を明確に分離
- ルックアヘッドバイアスを避ける実装（日時参照の取り扱い）
- 外部 API 呼び出し（OpenAI など）はキー指定で安全に行う（失敗時はフェイルセーフ）
- DuckDB を分析用途に利用、SQLite を監視・発注ログ用に利用

---

## 機能一覧

- 環境設定ウィザード: .env を対話式で作成・更新（python -m kabusys.config_setup）
- 設定検証 CLI: .env および config/*.yaml の基本チェック（python -m kabusys.validate_config）
- 実行エンジン起動: ExecutionEngine の起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db に記録
- 監視ループ起動: SystemMonitor ポーリング（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は環境にかかわらず本番 sqlite_path を参照して永続化
- 監視エンジン: System / Trade / Risk Monitor を束ね、アラートや kill.flag 制御を行う
- Kill Switch: drawdown やポジション上限で data/kill.flag を書き込み Execution を停止
- AI モジュール:
  - ニュース NLP（kabusys.ai.news_nlp）: OpenAI を使った銘柄ごとのセンチメント算出
  - レジーム判定（kabusys.ai.regime_detector）: MA とマクロセンチメントを合成して日次レジーム判定
- ペーパートレード検証レポート: scripts/tools/paper_verification_report（python -m kabusys.tools.paper_verification_report）
- 研究モジュール: ファクター計算、forward returns、IC 計算、統計サマリ等（kabusys.research）
- ポートフォリオ構築ユーティリティ（等重・スコア重み、セクター制限、position sizing）

---

## 必須 / 推奨依存パッケージ（主なもの）

実行環境によりバージョン指定が必要です。requirements.txt がない場合は手動でインストールしてください。主に利用しているパッケージは以下です。

- Python 3.9+
- duckdb
- psutil
- openai （AI 機能を使う場合）
- (任意) PyYAML（config/*.yaml の内容検証を有効にする場合）

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## 環境変数（主要）

※ .env を使って管理することを推奨します（config_setup ウィザードあり）。

必須（最低限）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意 / 推奨変数:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う場合必須
- PAPER_FILL_MODE: paper_trading 時の fill 動作（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring で使用）
- KILL_FLAG_CLEAR_ON_START: 本番での Kill フラグ自動クリア（0 推奨）

詳細は kabusys.config.Settings クラスをご参照ください。

---

## セットアップ手順（最短）

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 依存ライブラリをインストール（上記参照）
4. .env の作成
   - 対話的に作成する:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env.example を参考に手動編集
5. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする:
   python -m kabusys.validate_config --strict
   ```
6. 必要なディレクトリの準備（data, logs などは自動作成されますが手動でも可）
   ```
   mkdir -p data logs
   ```

---

## 使い方（よく使うコマンド）

- 実行エンジン起動（ExecutionEngine）
  - 本番 / 開発 / paper_trading は KABUSYS_ENV による:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 実行中に data/stop_requested.flag を作成するとエンジン停止シグナルになります（停止を検知して安全に終了）。

- 監視ループ起動（SystemMonitor）
  ```
  # MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（デフォルト 60）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は常に sqlite_path（監視 DB）を使用します（KABUSYS_ENV に関係なく本番 DB パスを参照します）。
  - 停止は data/stop_requested.flag を作成することで行えます。

- .env を対話的に作る
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート（SQLite DB を指定可能）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を手動指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、各関数に api_key 引数で渡します。
  - 例（スクリプトから直接呼ぶ場合は、DuckDB 接続を渡して関数を実行）:
    - kabusys.ai.score_news
    - kabusys.ai.regime_detector.score_regime

---

## 実行時のファイル / フラグ

- data/kill.flag: Kill Switch が書き込むフラグ（ExecutionEngine 停止のトリガー）
- data/stop_requested.flag: run_monitoring / run_execution の外部停止フラグ（ループを抜ける）
- data/execution.pid: ExecutionEngine が PID を書き込むファイル
- デフォルトの DB / ログ:
  - data/monitoring.db（SQLite）
  - data/paper_trading.db（ペーパートレード用 SQLite）
  - data/kabusys.duckdb（DuckDB）
  - logs/execution.log, logs/monitoring.log（ログは日次ローテーション）

---

## 主要モジュール概要（抜粋）

- kabusys.config: 環境変数/.env の読み込みと Settings 抽象
- kabusys.config_setup: .env 対話ウィザード
- kabusys.validate_config: 起動前チェック CLI
- kabusys.run_execution: ExecutionEngine 起動スクリプト
- kabusys.run_monitoring: SystemMonitor ポーリング起動スクリプト
- kabusys.monitoring.*: MonitoringDB / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
- kabusys.execution.*: (ExecutionEngine, OrderManager 等 — 実注文ロジック)
- kabusys.portfolio.*: ポートフォリオ構築ユーティリティ
- kabusys.research.*: ファクター計算・解析ツール
- kabusys.ai.*: news_nlp, regime_detector（OpenAI を利用）
- kabusys.tools.paper_verification_report: ペーパートレード検証レポート生成

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py
- utils/
  - logging_setup.py
  - process_priority.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (実装がある前提)
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - risk_manager.py
  - reconciler.py
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
- data/ (run 時に生成されることが多い)
- logs/ (ログ出力先)

（実際の全ファイルはリポジトリ内を参照してください）

---

## 運用上の注意点

- KABUSYS_ENV=live のときは本番扱いです。LINE 通知や kill フラグ設定に注意してください（validate_config で注意喚起あり）。
- ペーパートレードと本番の DB は明確に分離されています。paper_trading の場合は PAPER_TRADING_SQLITE_PATH を使用します。
- OpenAI 等外部 API を使う機能は API キー管理とコストに注意して運用してください。API 失敗時はフェイルセーフ（スコア 0.0 など）で継続する設計です。
- 監視は MONITOR_POLL_INTERVAL により間隔を変更可能ですが、短くしすぎるとリソース負荷が増えます。
- ロギングは logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

## トラブルシューティング

- .env 自動読み込みが問題を引き起こす場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効にできます。
- PyYAML がない場合: validate_config の YAML 検証はスキップされ、警告が表示されます。
- DuckDB / SQLite 接続エラー: パスや権限、ディレクトリの存在を確認してください。

---

必要であれば、README に以下を追加できます:
- 具体的な requirements.txt（バージョン固定）
- サービス化（systemd / Docker / docker-compose）手順
- CI / テストの実行方法
- 各モジュールのより詳細な API ドキュメント

補足や追加して欲しい項目があれば教えてください。