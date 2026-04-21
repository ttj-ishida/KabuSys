# KabuSys

日本株向けの自動売買・リサーチ基盤ライブラリ／実行スクリプト群です。本リポジトリは以下の機能を提供します：

- 発注エンジン（ExecutionEngine）／監視（Monitoring）
- ペーパートレード用の分離された DB とモックブローカー
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ファクター計算・リサーチユーティリティ（DuckDB を利用）
- ニュース NLP / レジーム判定（OpenAI 経由の LLM を利用可能）
- 監視ログの永続化・アラート・Kill Switch の実装
- 環境設定ウィザードと設定検証ツール
- ペーパートレード検証レポート生成ツール

以下は使い方や構成の説明です。

---

## 主な機能一覧

- Execution
  - run_execution.py: ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、paper_trading 用 DB に記録して本番 DB と分離。
  - リスク管理（RiskManager）、OrderManager、Reconciler 等を組み合わせて実行セッションを制御。

- Monitoring
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを記録。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor を束ねたポーリング実装。
  - KillSwitch: リスク条件に応じて `data/kill.flag` を書き込み、ExecutionEngine 停止を指示。
  - MonitoringDB: SQLite を用いた監視ログ永続化層。

- Portfolio（純粋関数群）
  - 候補選定・重み付け（等金額・スコア重み）
  - セクター制約適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap）

- Research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI 経由）
  - news_nlp: 複数銘柄のニュースをまとめて LLM に投げ、銘柄別センチメント（ai_score）を ai_scores テーブルへ保存
  - regime_detector: ETF（1321）MA200 乖離＋マクロニュースセンチメントを合成して市場レジームを判定・保存

- ユーティリティ
  - config_setup.py: 対話式 .env ウィザード（.env の初期作成・更新）
  - validate_config.py: 起動前の環境・設定ファイル検証（--strict で警告も FAIL 扱い）
  - tools.paper_verification_report: ペーパートレード検証レポート出力

---

## 前提・依存関係

推奨 Python バージョン: 3.10+

主な依存ライブラリ（最低限）:
- duckdb
- psutil
- openai
- PyYAML（validate_config の YAML 検証を有効にする場合）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（本リポジトリに requirements.txt が無い場合は上記を参考にしてください）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・依存をインストールします。

2. .env を作成する
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは `.env` を作成・更新します。生成された .env は絶対に Git にコミットしないでください。

3. 設定を検証する:
   ```
   python -m kabusys.validate_config
   ```
   必須環境変数が設定されているか、DB パスの親ディレクトリ存在、config/*.yaml のパースなどをチェックします。--strict を付けると警告も失敗扱いになります。

4. data / logs ディレクトリの準備（通常は自動作成されますが、権限等で失敗することがあるため手動で作成可能）:
   ```
   mkdir -p data logs
   ```

5. （必要に応じて）DuckDB / SQLite DB を初期化する。多くのスクリプトは起動時に必要なスキーマを自動生成します（例: init_monitoring_db）。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs）
- PID_FILE_PATH: Execution 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch のフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, ai/regime_detector 実行時に必要）

注意: .env を手動で作る場合は .env.example を参考にしてください（本リポジトリの .env.example が存在する想定）。

---

## 使い方（コマンド例）

- 環境設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動:
  - Paper trading（モックブローカーを使用）:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - Live（実売買）:
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  実行中は `data/execution.pid` に PID を書き込み、`data/stop_requested.flag` が存在するとシャットダウンします。Kill Switch が作動すると `KILL_FLAG_PATH`（デフォルト data/kill.flag）へ理由を書き込み、Engine 側で検知して停止します。

- Monitoring 起動:
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔を変更する場合:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  停止はプロジェクトルートの `data/stop_requested.flag` を作成します（Monitoring スクリプトは存在を検知してループを抜けます）。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  DB を指定する場合:
  ```
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI / レジーム判定などをプログラムから呼ぶ場合（OpenAI API key 必須）:
  - ai.score_news を利用して銘柄別 ai_score を生成（DuckDB 接続を渡す）:
    ```py
    from kabusys.ai import score_news
    # conn: duckdb connection, target_date: date, api_key: OPTIONAL
    n_written = score_news(conn, target_date, api_key="sk-...")
    ```
  - regime_detector.score_regime も同様に使用可能（関数は ai/regime_detector.py に実装）。

---

## 停止・Kill Switch の仕組み

- 停止フラグ（監視ループ / エンジン停止）
  - data/stop_requested.flag: 起動スクリプト（run_monitoring / run_execution）はこのファイルの存在を確認して安全に停止します。手動で停止させたい場合はこのファイルを作成してください。
  - data/execution.pid: ExecutionEngine が PID を記録するファイル（起動プロセス管理で利用）。
- Kill Switch
  - RiskMonitor / MonitoringEngine が条件（ドローダウン超過、ポジション上限超過など）を検出すると、KillSwitch が `KILL_FLAG_PATH`（デフォルト data/kill.flag） に理由を記載してファイルを書き込みます。これにより ExecutionEngine は次回のループで停止できます。
  - kill.flag を自動で消去する設定（KILL_FLAG_CLEAR_ON_START=1）は危険なので本番では 0 を推奨します。

kill.flag を手動で消す:
```
rm data/kill.flag
```

---

## ログ設定

共通ユーティリティ `kabusys.utils.logging_setup.setup_logging(app_name=...)` を使用してログを統一的に設定します:

- コンソール（stdout）: StreamHandler
- 日次ローテーションファイル: logs/<app_name>.log（TimedRotatingFileHandler、30日保持）
- LOG_DIR 環境変数で出力先を変更可能

---

## ライブラリ API（簡易）

- kabusys.portfolio
  - select_candidates(buy_signals, max_positions=...)
  - calc_equal_weights(candidates)
  - calc_score_weights(candidates)
  - calc_position_sizes(weights, candidates, portfolio_value, available_cash, ...)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons=None)
  - calc_ic(...)
  - factor_summary(...)

- kabusys.ai
  - score_news(conn, target_date, api_key=None)

- monitoring 用クラス群
  - kabusys.monitoring.monitoring_db.MonitoringDB
  - kabusys.monitoring.system_monitor.SystemMonitor
  - kabusys.monitoring.risk_monitor.RiskMonitor
  - kabusys.monitoring.monitoring_engine.MonitoringEngine

（各関数/クラスの詳細はソースの docstring を参照してください）

---

## ディレクトリ構成

以下は主要ファイル・ディレクトリの概観（src/kabusys 配下）。実際のコードベースに応じて多少異なる場合があります。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数／設定管理（.env 自動ロード・Settings クラス）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数算出・aggregate cap
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計
    - __init__.py
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 経由）
    - regime_detector.py — 市場レジーム判定（MA + マクロ NLP）
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化 / 永続化層
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （取引監視用、該当ファイルがある想定）
    - monitoring_engine.py — 複数モニタを束ねるエンジン
    - kill_switch.py — Kill Switch 実装
    - alert_manager.py — （アラート送信管理、該当ファイルがある想定）
  - execution/
    - execution_engine.py — ExecutionEngine 本体
    - broker_factory.py — ブローカークライアント生成（Mock/実装分岐）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行関連コンポーネント
  - data/ (実行時に生成される想定)
    - monitoring.db, paper_trading.db, kabusys.duckdb, kill.flag, stop_requested.flag, execution.pid
  - logs/ (ログファイル出力先)

ソース内の docstring に各モジュールの設計方針・注意点が記載されています。実装の挙動やパラメータについてはソースを参照してください。

---

## よくある運用・注意点

- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしてください。自動クリアは危険です。
- ペーパートレードは本番 DB と完全分離されるように設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を利用する機能（news_nlp / regime_detector）は API キー（OPENAI_API_KEY）を必要とします。レート制限やネットワーク障害に対しては内部でリトライやフォールバック処理がありますが、API コストに注意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります。ファイル出力に失敗した旨の警告が出ます。

---

README は以上です。より詳しい使い方や運用手順（systemd / supervisor の unit サンプル、バックアップ、DB 管理など）を追加したい場合は用途に合わせて追記できます。必要ならその内容も作成します。