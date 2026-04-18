# KabuSys

日本株自動売買システムの一部コンポーネント群（モニタリング / 実行エンジン / 研究・ポートフォリオ・AIユーティリティ等）。  
このリポジトリは各種起動スクリプト、環境設定ウィザード、検証ツール、および主要モジュール群を含みます。

主な目的
- ExecutionEngine（発注ロジック）とその補助コンポーネント
- Monitoring（システム・注文・リスク監視）
- 研究用モジュール（ファクター計算、特徴量解析）
- AI ラッパー（ニュース NLP / レジーム判定）
- ペーパートレード用検証ツール、環境設定ウィザード

---

## 機能一覧

- 実行・発注周り
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading と live を切り替え）
  - BrokerClientFactory により実運用／モックを切替可能
  - ペーパートレード時は専用 SQLite（デフォルト: data/paper_trading.db）に記録

- 監視
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可）
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor を束ねる
  - KillSwitch: データ/フラグファイルで ExecutionEngine 停止シグナルを送信
  - monitoring_db: system_status / trade_logs / positions / risk_logs / dashboard 等の永続化

- 研究・ポートフォリオ
  - research.factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 使用）
  - research.feature_exploration: 将来リターン計算、IC 計算、統計サマリー
  - portfolio: 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数

- AI 関連
  - ai.news_nlp: OpenAI を使ったニュースのセンチメントスコア算出と ai_scores への書き込み
  - ai.regime_detector: ETF の MA とマクロニュースを合成して市場レジーム判定、market_regime への書き込み

- ユーティリティ
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 環境変数・設定ファイルの事前検証 CLI
  - tools.paper_verification_report: ペーパートレード結果の期間レポート生成
  - utils.logging_setup: 統一的なログ設定（console + 日次ローテートファイル）
  - utils.process_priority: プロセス優先度 / CPU affinity 設定

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.9+（typing 機能を使うため推奨。実際の要件はプロジェクトに合わせて調整してください）
- SQLite は標準ライブラリで利用可能
- 必要な Python パッケージ（例示）:
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（validate_config の YAML 検証用）

推奨手順
1. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール（requirements.txt が無い場合は個別に）
   ```
   pip install duckdb psutil openai
   # YAML 検証を使う場合:
   pip install pyyaml
   ```

3. プロジェクトルートに `data/` と `logs/` を作成（自動で作られることもありますが手動で作成しておくと権限問題が減ります）
   ```
   mkdir -p data logs
   ```

4. .env を作成
   - 対話式ウィザードを使う：
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `config_setup` で生成された .env を手作業で編集してください。

5. 設定の検証
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

6. OpenAI を利用する機能を使う場合は環境変数 `OPENAI_API_KEY` を設定してください。

---

## 使い方（起動・主要コマンド）

- 実行エンジン（ExecutionEngine）を起動
  - 本番（live）／ペーパーは環境変数 KABUSYS_ENV により切り替え
  - 例（通常）:
    ```
    export KABUSYS_ENV=development
    python -m kabusys.run_execution
    ```
  - ペーパートレードに切り替える例:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 起動時に data/stop_requested.flag や data/kill.flag の有無で挙動が変わります。execution は paper_trading 時に専用 DB（PAPER_TRADING_SQLITE_PATH）を使います。

- 監視ループを起動（SystemMonitor）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60）
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db
  ```

- AI / 研究関数はモジュール API を直接インポートして使用します（例: kabusys.ai.score_news、kabusys.research.calc_momentum など）。

---

## 主要な環境変数

（.env で管理することを推奨）

必須例
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要なオプション
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで必要）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

---

## 停止・Kill Switch の動作

- KillSwitch（kabusys.monitoring.kill_switch）は条件（ドローダウンやポジション上限など）が満たされると、`data/kill.flag` を書き込みます。ExecutionEngine 側はこのフラグを検出して安全に停止します。
- 手動で停止フラグを立てる場合は `data/stop_requested.flag` を作成すると各ランナーが検知して終了することがあります。
- Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` が設定されていると自動で kill.flag を削除します（本番では 0 推奨）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定読み込みロジック、Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py — ニュースを OpenAI でスコア化するロジック（score_news）
    - regime_detector.py — マクロ + ETF MA を用いたレジーム判定（score_regime）
  - monitoring/
    - monitoring_db.py — SQLite のテーブル定義・永続化 API
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねる
    - (その他: alert_manager, trade_monitor 等が想定される)
  - execution/ （発注ロジック関連。BrokerFactory, ExecutionEngine, OrderManager 等）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数計算・スケール調整
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value の計算
    - feature_exploration.py — 将来リターン・IC等の解析
  - monitoring/
    - monitoring_db.py, system_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度設定、CPU affinity
  - data/ （実行時生成想定）
    - kill.flag, stop_requested.flag, execution.pid, monitoring.db 等

（上記はリポジトリの抜粋です。実際の実装にはさらにファイル・モジュールが存在します。）

---

## 開発・運用時の注意

- .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。
- validate_config.py で起動前に必須環境変数やファイルパスをチェックすることを推奨します。
- run_monitoring は Monitoring 用の SQLite（デフォルト data/monitoring.db）を利用します。モニタリングは環境にかかわらず本番の sqlite_path を使用する設計になっているため、本番 DB でのテストは慎重に。
- run_execution は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し本番 DB と分離された PAPER_TRADING_SQLITE_PATH に記録します。
- OpenAI API を使うモジュールは外部ネットワーク・API課金が発生するため稼働環境での扱いに注意してください。API エラーやタイムアウト時はフェイルセーフ挙動により継続する実装になっていますが、設定の確認は必要です。

---

## よくある操作例

1. 初期セットアップ（.env 作成 → 検証）
   ```
   python -m kabusys.config_setup
   python -m kabusys.validate_config
   ```

2. 監視プロセスをデバッグ実行（間隔 30 秒）
   ```
   export MONITOR_POLL_INTERVAL=30
   python -m kabusys.run_monitoring
   ```

3. ペーパートレードで実行エンジン起動
   ```
   export KABUSYS_ENV=paper_trading
   python -m kabusys.run_execution
   ```

4. Paper Trading レポート作成
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```

---

必要に応じて README に例となる .env テンプレートやより詳細な運用手順（systemd ユニット例、スーパーバイザ設定、バックアップ方針）を追加できます。追加したい内容があれば教えてください。