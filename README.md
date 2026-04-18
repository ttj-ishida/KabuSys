# KabuSys

日本株自動売買システムのコアライブラリ / 実行スクリプト群です。  
本リポジトリはトレーディングエンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・サイズ計算、研究用ファクター計算、AI を使ったニュースセンチメント評価などを含みます。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド / 実行方法）
- ディレクトリ構成（主なモジュール説明）
- 環境変数 / 設定の概略
- 運用上の注意

---

## プロジェクト概要

KabuSys は日本株自動売買向けのモジュール群です。主な目的は以下：

- 日次/秒次でのポートフォリオ構築・発注ロジック（ExecutionEngine）
- システム稼働監視、データ鮮度チェック、リスク監視（Monitoring）
- Paper Trading（模擬発注）を本番 DB と分離して安全に試験可能
- DuckDB を使った研究用ファクター計算・特徴量探索
- OpenAI を使ったニュースの NLP スコアリング & レジーム判定
- 簡易 CLI ツール（設定ウィザード / 設定検証 / 検証レポート）

---

## 機能一覧

- Execution
  - ExecutionEngine を起動して注文発行・管理を行う（本番/ペーパートレード切替対応）
  - BrokerClientFactory により実ブローカー or MockBroker を選択
  - リスク管理（RiskManager）、OrderManager、Reconciler 等の連携

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス稼働、データ鮮度を監視し SQLite に記録
  - TradeMonitor：トレードログの滞留・約定異常検出（trade_logs に記録）
  - RiskMonitor：ドローダウンやポジション数上限などを判定してアラート/ログ保存
  - KillSwitch：重大事象で data/kill.flag を書き込んで ExecutionEngine を停止させる
  - MonitoringEngine：複数モニタを束ねてポーリング

- Portfolio（純粋関数群、DB参照なし）
  - 候補選定、等金額／スコア加重配分、リスク調整（セクター上限）、ポジションサイズ計算（単元株考慮）

- Research
  - DuckDB 接続を受けてファクター（モメンタム/バリュー/ボラティリティ）を計算
  - 将来リターン、IC 計算、ファクター統計サマリ等

- AI
  - news_nlp: OpenAI（gpt-4o-mini 等）でニュースをスコアリングして ai_scores に書き込み
  - regime_detector: ETF（1321）MA とマクロニュースセンチメントを合成して market_regime に書き込み

- ユーティリティ
  - 設定ウィザード（.env 生成支援）
  - 設定検証 CLI（必須環境変数 / config/*.yaml 存在確認 等）
  - Paper Trading 検証レポート出力ツール

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を作成
   - 推奨: Python 3.10+
   - 例:
     ```
     git clone <repo>
     cd <repo>
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     ```
   - requirements.txt が無い場合、少なくとも以下パッケージが必要になります:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config YAML 検証用）

2. .env の作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - または直接 `.env` を作成。最低必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 例（最小）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     ```

3. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   # 警告もFAILにしたい場合:
   python -m kabusys.validate_config --strict
   ```

4. データディレクトリ作成（自動で作られることが多いですが事前確認）
   - デフォルトの SQLite / DuckDB / logs ディレクトリが `data/` / `logs/` 配下になります。
   - 例:
     ```
     mkdir -p data logs
     ```

5. （AI 機能を使う場合）OpenAI API キーを設定
   - 環境変数: OPENAI_API_KEY を .env に追加

---

## 使い方

主要なエントリポイント／CLI は以下です。いずれもプロジェクトルートで実行します。

- 設定ウィザード（.env の生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、Paper 用 DB（デフォルト: data/paper_trading.db）へ記録します（本番 DB と分離）。
    - プロセス優先度を "high" に設定し、PID ファイル（デフォルト: data/execution.pid）を管理します。
    - data/stop_requested.flag が存在すると起動をせず、既に起動中は検知して停止します。

- Monitoring 起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視ログを残します。
  - 停止判定: プロジェクトルート/data/stop_requested.flag が存在するとループを終了します。

- Paper Trading 検証レポート（CLI）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```
  - PAPER_TRADING_SQLITE_PATH 環境変数でデフォルト DB パスを指定可。

- AI / レジーム・ニュース評価（ライブラリ関数）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続オブジェクトと target_date を受け取り、DB を更新します（OpenAI API キーは引数 or 環境変数 OPENAI_API_KEY）。

ログ
- setup_logging を各エントリポイントで使用していて、デフォルトで `logs/<app_name>.log` に日次ローテートで出力します。`LOG_DIR` 環境変数で変更可。標準出力は stdout。

停止・Kill スイッチ
- KillSwitch は data/kill.flag へ理由を書き込み、ExecutionEngine に停止指示を出します（ExecutionEngine は起動時やループ中にこのフラグを確認して停止します）。
- run_execution / run_monitoring は stop_requested.flag（data/stop_requested.flag）を使って外部からの即時停止制御も行います。

環境変数の自動読み込み
- プロジェクトルートに `.env` / `.env.local` がある場合、起動時に自動で読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要モジュール）

以下は src/kabusys 配下の主要ファイル・パッケージと簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - Settings クラスを提供。環境変数のラップ、.env 自動ロードロジック、検証を担う。
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（プロセス優先度設定、DB 接続、スレッド実行、停止フラグ処理）
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL に対応）
  - monitoring/
    - monitoring_db.py : SQLite による監視ログ永続化層（テーブル作成・読み書きユーティリティ）
    - system_monitor.py : CPU/メモリ/ディスク、プロセス PID、データ鮮度チェック
    - trade_monitor.py : （トレードログ監視、滞留注文検出等 — 実装参照）
    - risk_monitor.py : ドローダウン・ポジション上限監視
    - monitoring_engine.py : 各 Monitor を束ねるエンジン
    - kill_switch.py : kill.flag の管理
    - alert_manager.py : 通知（LINE 等）管理（実装参照）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py 等
    - Execution 系のコアロジック（Broker 層の抽象化により本番/模擬切替）
  - portfolio/
    - portfolio_builder.py、position_sizing.py、risk_adjustment.py
    - 候補選定、重み付け、セクターキャップ、サイズ計算
  - research/
    - factor_research.py、feature_exploration.py
    - DuckDB を使ったファクター計算、IC、統計サマリ
  - ai/
    - news_nlp.py、regime_detector.py
    - OpenAI を用いたニューススコアリング、レジーム判定（失敗時のフォールバックロジックあり）
  - tools/
    - paper_verification_report.py : Paper Trading の整合性・品質検証レポート

（各ファイル内の docstring に設計意図・使用法が記載されています。実装を参照してください）

---

## 環境変数 / 設定の要点

- 必須（実行に必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 主要オプション
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker を使用し paper db に書き込み
    - live: 本番（実際の発注）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - OPENAI_API_KEY: OpenAI を使う機能で必要（news_nlp, regime_detector 等）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

- 注意:
  - monitoring は KABUSYS_ENV に関係なく `SQLITE_PATH`（本番用）を参照します（監視ログは環境を跨いで一箇所に集約する設計）。
  - paper_trading を選んだ場合は Execution 側の DB を `PAPER_TRADING_SQLITE_PATH` に切り替え、発注ログ等を本番 DB から分離します。

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）で実行する前に必ず `python -m kabusys.validate_config` を実行し設定を確認してください。
- .env ファイルは機密情報を含むため絶対にリポジトリにコミットしないでください。
- Kill Switch（data/kill.flag）と Stop フラグ（data/stop_requested.flag）を運用で使ってプロセス制御を行えます。KillFlag の自動クリアは本番では無効（0）推奨です。
- OpenAI を使用する機能は API コスト・レートリミットに注意してください。リトライ・バックオフ実装はありますが、運用負荷は発生します。
- ポートフォリオ設定や risk 設定のパラメータ（max_position_pct / max_utilization / risk_pct 等）は実運用前に慎重にチューニングしてください。

---

README は以上です。より詳細な API 参照や、個別モジュールのユースケース（ExecutionEngine の設定方法や Broker 実装の差し替え方など）が必要であれば、該当モジュールを指定していただければ追加ドキュメントを作成します。