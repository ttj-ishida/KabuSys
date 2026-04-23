# KabuSys

日本株向け自動売買 / 研究プラットフォーム（ライブラリ＋運用スクリプト群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買、モニタリング、研究（ファクター計算 / 特徴量解析）、およびニュースベースの AI スコアリングを支援する Python コードベースです。  
主要コンポーネントは以下を含みます。

- ExecutionEngine（発注エンジン：実マーケット / ペーパートレード対応）
- Monitoring（システム・注文・リスク監視、Kill Switch）
- Portfolio construction（候補選定・重み付け・枚数決定）
- Research（ファクター計算、IC 計算、特徴量サマリ）
- AI（OpenAI を用いたニュースセンチメント、レジーム判定）
- ユーティリティ（logging 設定、プロセス優先度設定、設定ウィザード、検証ツール 等）
- Tools（ペーパートレード検証レポート等のユーティリティスクリプト）

本 README は、セットアップ方法、主要な機能と使い方、ディレクトリ構成をまとめたものです。

---

## 機能一覧（抜粋）

- Execution
  - 本番 / ペーパートレード切替（環境変数 `KABUSYS_ENV`）
  - BrokerClientFactory 経由でブローカー抽象化
  - RiskManager / OrderManager / Reconciler による発注管理
  - ExecutionEngine をデーモン相当で起動（PID 管理、停止フラグ監視）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス監視、データ鮮度チェック
  - TradeMonitor: 発注ログ・滞留注文・約定異常の検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: リスクトリガーにより `data/kill.flag` を作成して ExecutionEngine 停止
  - MonitoringEngine: 上記モニターを束ねて定期実行、アラート通知連携
- Portfolio construction
  - 候補選定（スコア順）、等重・スコア加重、リスクベースのポジション決定
  - セクターキャップ適用、レジーム乗数（bull/neutral/bear）
- Research
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value）
  - 将来リターン算出、IC（Spearman）計算、特徴量サマリ
- AI
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（ai_scores）生成
  - マクロニュース + ETF MA200 を使った市場レジーム判定（market_regime）
  - API リトライ・バリデーション・スコアクリップ等の堅牢な実装
- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成スクリプト（tools.paper_verification_report）
- その他ユーティリティ
  - 統一ログ設定（TimedRotatingFileHandler、stdout 出力）
  - プロセス優先度 / CPU affinity セット

---

## 前提 / 必要依存パッケージ

以下は主な実行時依存です（環境により他パッケージが必要になる場合があります）。

- Python 3.9+（型アノテーションに Path 等を使用）
- duckdb
- psutil
- openai (AI 関連機能を使う場合)
- PyYAML（設定ファイル検証を行う場合は推奨）
- その他: sqlite3（標準ライブラリ）、logging（標準）、threading など

pip インストール例（仮の requirements）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作る
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

3. .env ファイルの用意
   - 対話式で作成: python -m kabusys.config_setup
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV = development | paper_trading | live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（例: INFO）
     - KILL_FLAG_CLEAR_ON_START（起動時の kill.flag 自動クリア: 1=クリア）

   - 参考: .env.example（プロジェクトに同梱されている想定）

4. ディレクトリ作成
   - data/ および logs/ は自動作成されますが、アクセス権などに応じて手動で作成しておくと安全です。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit 1）

---

## 実行方法（主要スクリプト）

Python モジュールとして実行します（プロジェクトルートから）。

- ExecutionEngine（注文エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード DB を使用（PAPER_TRADING_SQLITE_PATH）。
    - 起動前に data/stop_requested.flag があれば起動せず終了します。
    - エンジンはスレッドで run_session を実行し、data/stop_requested.flag の作成で停止する仕組みです。
    - PID ファイル: data/execution.pid（Settings.pid_file_path に依存）

- Monitoring（常駐監視）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - 監視ループを開始（デフォルト 60 秒間隔）
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視テーブルを永続化します
    - 停止は data/stop_requested.flag の作成で検知しループ終了

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

---

## 運用上の注意 / フラグファイル

- stop flag
  - data/stop_requested.flag を作成すると run_execution / run_monitoring が起動中ループ内で検知して安全に停止します。
- kill switch
  - KillSwitch がリスク閾値を満たすと data/kill.flag（デフォルト）を作成し、ExecutionEngine を停止する運用上の緊急停止トリガになります。
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に自動クリアされますが、本番では 0 を推奨します。
- DB の分離
  - paper_trading モードは本番監視 DB と分離された PAPER_TRADING_SQLITE_PATH を用います（data/paper_trading.db がデフォルト）。
- ログ
  - ログは logs/<app_name>.log に日次ローテーションで出力されます（デフォルト保管 30 日）。
  - LOG_DIR, LOG_LEVEL でカスタマイズ可能。
- MONITOR_POLL_INTERVAL
  - 監視間隔を秒で指定。環境変数 MONITOR_POLL_INTERVAL を使えば run_monitoring のポーリング間隔を変更できます（デフォルト 60）。

---

## 環境変数一覧（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用 / オプション
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading モード DB、デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY（AI 機能）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR（ログ保存先）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔）
  - KILL_FLAG_CLEAR_ON_START（起動時 kill.flag をクリアするか: 0/1）

---

## 開発時のヒント

- DuckDB はデータ分析用のローカル DB として prices_daily / raw_financials / raw_news などを保持します。research モジュールは DuckDB 接続を受け取り純粋関数で計算します（本番 API へはアクセスしません）。
- AI 関連機能（news_nlp, regime_detector）は OpenAI API に依存します。API キーは安全に管理してください。
- 設定検証（validate_config）は .env と config/*.yaml の存在や簡易パースを行います。PyYAML がインストールされていない場合は YAML 検証をスキップします。

---

## 主要ディレクトリ構成

（src 内をルートとした簡易ツリー）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード機能あり）
  - config_setup.py          — .env 対話式ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - execution/               — 発注エンジン関連（Engine, OrderManager, BrokerFactory 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
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
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

---

## よくある運用フロー（例）

1. .env を作る / 更新
   - python -m kabusys.config_setup
2. 設定検証
   - python -m kabusys.validate_config
3. データ投入（DuckDB / prices_daily 等のセットアップは別途）
4. 監視プロセス起動（サーバでデーモン化）
   - python -m kabusys.run_monitoring &
5. Execution 起動（本番または paper_trading）
   - python -m kabusys.run_execution &
6. ペーパートレード検証
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## ライセンス / 注意事項

- .env は絶対にリポジトリにコミットしないでください（README 内 config_setup も警告あり）。
- 本システムは投資助言を目的とするものではありません。実資金での運用は自己責任で行ってください。
- KABUSYS_ENV=live を設定する場合は全ての設定を慎重に確認してください（validate_config は警告を出します）。

---

必要であれば、README に入れるサンプル .env テンプレート、service (systemd) ユニットや Docker の起動手順、より詳細な運用手順（バックアップ、DB マイグレーション方針等）を追記します。どの情報を優先して追加しますか？