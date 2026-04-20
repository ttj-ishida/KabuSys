# KabuSys — README

日本株向け自動売買 / 研究用ライブラリ群の軽量コアです。  
このリポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター研究、AI（ニュースNLP / レジーム判定）などの主要コンポーネントを含みます。

以下はコードベースの概要・セットアップ・使い方・ディレクトリ構成です。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を提供します。

- 実行（ExecutionEngine）: ブローカークライアントを通じた発注管理、リスク管理、約定の調停等
- 監視（Monitoring）: システムプロセスの監視、滞留注文やドローダウン検出、Kill Switch 制御
- ポートフォリオ構築: 候補選定・重み計算・ポジションサイズ計算・セクター制約
- 研究（Research）: DuckDB を用いたファクター計算・前方リターン・IC 計算など
- AI ツール: ニュースの LLM ベースセンチメントなど（OpenAI API を利用）
- ユーティリティ: ロギング設定、プロセス優先度設定、設定読み込み / ウィザード等

設計上のポイント:
- .env および環境変数から設定を読み込む（自動読み込みは無効化可能）
- Paper Trading と Live を分離（paper_trading は専用 SQLite を利用）
- DuckDB を分析用 DB として利用
- ログはコンソール＋日次ローテートファイル（logs/<app>.log）に出力

---

## 主な機能一覧

- 実行関連
  - BrokerClientFactory を経由したブローカークライアント生成（KABUSYS_ENV によって Mock/実ブローカー切替）
  - ExecutionEngine によるセッション管理、OrderManager / Reconciler / RiskManager の統合

- 監視関連
  - SystemMonitor: CPU / メモリ / ディスク、Execution プロセス存在チェック、データ鮮度チェック
  - TradeMonitor: 発注ログの監視（滞留注文・約定異常等）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件成立時に data/kill.flag を書き込み Execution を停止させる
  - MonitoringEngine: これらをまとめてポーリング、AlertManager 経由で通知

- ポートフォリオ構築
  - 候補選定（スコア降順）、等重/スコア重み、リスクベースの株数決定、セクターキャップ、レジーム乗数

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等ファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- AI（OpenAI）
  - ニュースの銘柄単位センチメントスコアリング（gpt-4o-mini を想定）
  - マクロニュースを用いた市場レジーム判定（regime）

- スクリプト / ツール
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - 監視起動: python -m kabusys.run_monitoring
  - 実行エンジン起動: python -m kabusys.run_execution
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順

1. Python バージョン
   - Python 3.9+ を推奨（ソース内型ヒント / 機能を前提）

2. 依存パッケージ（例）
   - duckdb
   - psutil
   - openai
   - （任意）PyYAML（設定 YAML 検証のため）
   - 標準ライブラリ: sqlite3, logging, argparse, pathlib など

   例: pip によるインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. プロジェクトルートに移動して .env を作成
   - 対話式ウィザードを使う（推奨）:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env.example を参考に手動作成。重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB、デフォルト: data/paper_trading.db）

   - 自動読み込み:
     Settings モジュールはプロジェクトルート（.git または pyproject.toml）を探索し、`.env` / `.env.local` を自動読み込みします。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告を FAIL 扱い
   ```

5. ディレクトリパーミッションとログディレクトリ
   - ログは既定で `logs/` に出力します。書き込み権限を確認してください。
   - SQLite / DuckDB の保存先ディレクトリ（data/ など）も書き込み可能にしてください。

---

## 使い方（実行例）

- 監視プロセスを起動
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  - 監視は data/stop_requested.flag を検知すると停止します（スクリプト内の STOP_FLAG）。KillSwitch は別に data/kill.flag を生成します（Execution 停止のため）。

- 実行エンジン（Execution）を起動
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient が使われ、`data/paper_trading.db` に記録されます（本番DBと完全分離）。
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  - 起動時、`data/execution.pid` に PID が書き込まれます。停止は data/stop_requested.flag で指示できます。

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または環境変数で DB を指定
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db python -m kabusys.tools.paper_verification_report
  ```

- AI 系（OpenAI）を使う
  - 必要: OPENAI_API_KEY を環境変数に設定
  - news_nlp.score_news / regime_detector.score_regime を呼び出して ai_scores / market_regime などを更新できます（DuckDB 接続を渡して使用）。

---

## 重要な環境変数一覧（抜粋）

- KABUSYS_ENV: execution モード
  - development / paper_trading / live
  - paper_trading では MockBroker を使い、paper_trading 用の SQLite を使用

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY: AI 機能（news_nlp / regime_detector）で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、default 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" で有効）

---

## Kill Switch / 停止フラグ

- Kill Switch: 条件成立時（例: ドローダウン超過・ポジション上限超過）に `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送る仕組みがあります。`Settings.kill_flag_path` がフラグのパスです（デフォルト `data/kill.flag`）。
- 停止フラグ: `data/stop_requested.flag` を書くと run_monitoring / run_execution が検知して安全に終了します。
- Execution の起動時に kill.flag を自動で消去したい場合は `.env` に `KILL_FLAG_CLEAR_ON_START=1` を設定できます（注意: 本番では推奨されません）。

---

## ログ設定

- 共通関数: `kabusys.utils.logging_setup.setup_logging(app_name="execution")`
- 出力先:
  - stdout（StreamHandler）
  - 日次ローテーションファイル: `<LOG_DIR or logs>/<app_name>.log`（デフォルト `logs/`、30日分保持）
- ディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみになります。

---

## 開発者向けヒント / トラブルシュート

- .env 自動読み込みを無効化するには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- PyYAML がインストールされていない場合、`validate_config` は YAML のパース検証をスキップします（警告）。
- DuckDB や SQLite のパスはデフォルトで `data/` 配下に設定されています。初回起動時にディレクトリが自動作成されますが、パーミッションを確認してください。
- psutil を利用してプロセス優先度 / CPU affinity を設定します。権限不足等で設定に失敗した場合はログで警告されますが、実行自体は継続します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定読み込み
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — 監視ポーリングループ起動スクリプト
  - run_execution.py — 実行エンジン起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化層
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （滞留注文などの監視）※実装ファイルあり
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — 通知管理（LINE 等）
  - execution/
    - execution_engine.py — ExecutionEngine 実装
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py 等
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み
    - position_sizing.py — 株数計算
    - risk_adjustment.py — セクター制約 / レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 利用）
    - regime_detector.py — レジーム判定（OpenAI 利用）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity

- data/ (実行時に生成される)
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 時)
  - kabusys.duckdb (デフォルト)
  - execution.pid
  - kill.flag / stop_requested.flag

---

## ライセンス / バージョン

- パッケージバージョンは `kabusys.__version__` に定義されています（例: 0.1.0）。
- ライセンスはリポジトリ内の LICENSE を参照してください（本 README には含まれていません）。

---

この README はコード内の docstring / コメントをもとに作成しています。実運用や本番稼働前には必ず `python -m kabusys.validate_config` による設定検証および一連のテストを行ってください。必要であれば本 README をベースにさらに導入手順や Systemd ユニット、Dockerfile などを追加支援します。