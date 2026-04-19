# KabuSys

日本株向け自動売買システムの一部コンポーネント群（ランタイム起動スクリプト・監視・ポートフォリオ構築・リサーチ・AI 連携など）。  
この README はコードベース（src/kabusys）に基づき、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するためのライブラリ／実行コンポーネント群です。主要な責務は以下です。

- ExecutionEngine（発注エンジン）起動スクリプト（run_execution）
  - 本番・ペーパートレード切替（`KABUSYS_ENV`）
  - ブローカークライアントの抽象化（Mock を含む）
- Monitoring（監視）コンポーネント（run_monitoring / MonitoringEngine）
  - システム状態、注文・約定ログ、リスク（ドローダウン・ポジション上限）監視
  - Kill Switch（条件を満たすと `data/kill.flag` を書いて Execution を停止）
- 研究・リサーチモジュール（factor 計算、特徴量解析）
- Portfolio 構築（候補選定・重み計算・ポジションサイジング・セクター制限）
- AI 連携（OpenAI を使ったニュースセンチメント、レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定読み込みウィザード/検証）

設計上の注記：
- .env（環境変数）を読み込み、`Settings` クラス経由で設定を参照します。
- データ永続化に DuckDB（分析用）と SQLite（監視・発注ログ用）を使用します。
- 本番実行時は慎重な取り扱い（`KABUSYS_ENV=live`）が必要です。警告を多く含む仕組みがあります。

---

## 主な機能一覧

- 実行関連
  - run_execution.py: ExecutionEngine を起動（`KABUSYS_ENV=paper_trading` の場合は MockBroker）
  - 停止フラグ（`data/stop_requested.flag` / `data/kill.flag`）で安全停止

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動（デフォルト 60秒）
  - MonitoringEngine: System/Trade/Risk 各 Monitor を統合し定期実行
  - MonitoringDB: SQLite に監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）を保持
  - KillSwitch: リスク条件に応じ kill.flag を書き込み Execution を停止

- ポートフォリオ構築
  - 候補選定、等金額／スコア重み付け
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（lot 単位丸め、aggregate cap）

- リサーチ
  - momentum / volatility / value 等のファクター計算（DuckDB を使用）
  - forward return / IC / 統計サマリー

- AI（OpenAI）
  - ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）

- ツール
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: 環境変数・config/*.yaml の事前検証 CLI
  - tools.paper_verification_report: Paper Trading の検証レポート生成

- ユーティリティ
  - ログ設定（ログの stdout / 日次ローテートファイル出力）
  - プロセス優先度 / CPU affinity 設定

---

## 前提（Prerequisites）

- Python 3.9+（型アノテーションの union などを含むため概ね 3.9 以降を想定）
- 推奨パッケージ（主要な依存性）
  - duckdb
  - psutil
  - openai（AI 関連を使う場合）
  - PyYAML（validate_config の YAML 検証時に任意で使用）

（プロジェクトに requirements.txt があればそれを使ってインストールしてください）

例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. レポジトリをクローン / ソースを入手
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. .env の準備
   - 対話式ウィザードで作成（推奨）:
     ```bash
     python -m kabusys.config_setup
     ```
   - または手動で `./.env` に必要なキーを書き込む（.env.example を参照して構成）。
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能使用時）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか。0/1）
4. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data logs
   ```

注意:
- validate_config.py で事前チェックが可能です:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

---

## 使い方（主要スクリプトと API）

- ExecutionEngine を起動（本番/ペーパートレードの振る舞いは KABUSYS_ENV に依存）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` に記録されます（本番 DB と分離）。
  - 実行中、`data/stop_requested.flag` の存在で安全に停止します。
  - Execution 用の PID ファイル: `data/execution.pid`（デフォルト）

- Monitoring（SystemMonitor）を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は、KABUSYS_ENV にかかわらず Settings.sqlite_path（本番 sqlite path）を使用します（監視 DB は環境に依存しない扱い）。
  - `data/stop_requested.flag` を検知するとループを終了します。

- 設定ウィザード（.env 生成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（CLI）
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラム API）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、指定日付のニュースウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を評価して ai_scores テーブルへ書き込む。
    - OpenAI API キーは引数 or 環境変数 OPENAI_API_KEY を使用。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF(1321) の MA200 とマクロニュースを組み合わせて market_regime テーブルに書き込む。

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live  (default: development)
  - paper_trading: MockBroker を使い DB を分離
  - live: 本番モード（警告多数）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (default: INFO)
- OPENAI_API_KEY (AI を使用する場合)
- MONITOR_POLL_INTERVAL (監視ポーリング秒、default: 60)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag をクリアするか: "0" or "1")

---

## ログ・DB・フラグファイル

- ログ:
  - デフォルトは `logs/` ディレクトリ。アプリ名ごとにファイルが作成されます（例: logs/execution.log, logs/monitoring.log）
  - ログは stdout にも出力されます（StreamHandler）。ファイルは日次ローテーションで 30 日分保持。

- データベース:
  - DuckDB: 分析用（prices_daily 等のテーブル）
  - SQLite:
    - monitoring.db（監視ログ: system_status, trade_logs, positions, risk_logs, dashboard）
    - paper_trading.db（ペーパートレード専用 SQLite）

- フラグ / PID:
  - stop フラグ: `data/stop_requested.flag`（run_* スクリプトはこれを監視して安全終了）
  - kill フラグ（Execution 停止用）: `data/kill.flag`（KillSwitch により書き込まれる）
  - PID ファイル: `data/execution.pid`（ExecutionEngine が使用）

---

## ディレクトリ構成

（src/kabusys 以下の主要ファイル/フォルダを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数の読み込みと Settings クラス
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI 連携）
    - regime_detector.py         — 市場レジーム判定（OpenAI 連携）
  - monitoring/
    - monitoring_db.py           — SQLite 監視 DB 層
    - system_monitor.py          — システムデータ鮮度・プロセス監視
    - trade_monitor.py           — （注文関連監視: code 適所）
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - monitoring_engine.py       — 各 Monitor を束ねるエンジン
    - kill_switch.py             — kill.flag の評価・書き込み
    - alert_manager.py           —（アラート送信の管理）
  - execution/
    - execution_engine.py        — ExecutionEngine（起動ロジック）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - etc.
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 発注株数計算
    - risk_adjustment.py         — セクターキャップ等
  - research/
    - factor_research.py         — ファクター計算（momentum/volatility/value）
    - feature_exploration.py     — 将来リターン / IC / 統計
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity 設定
  - data/ (実行時に作られることが多い)
    - monitoring.db              — SQLite 監視 DB（デフォルト）
    - paper_trading.db           — ペーパートレード用 DB（paper_trading）
    - kabusys.duckdb             — DuckDB（デフォルトパス: data/kabusys.duckdb）
    - execution.pid
    - stop_requested.flag
    - kill.flag

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では、LINE の通知設定や kill switch 設定を必ず確認してください。
- `KILL_FLAG_CLEAR_ON_START=1` は本番での自動クリアは危険です（デフォルトは 0）。
- 実行前に `python -m kabusys.validate_config` で設定チェックを行ってください。
- AI（OpenAI）を使う機能は外部 API を呼ぶため、レート制限やコストに注意。API キーは安全に管理してください。
- run_monitoring は監視 DB に接続する際、環境にかかわらず本番 sqlite_path を参照します（監視情報は中央 DB に集約する設計）。

---

この README はコードベースの主要点を簡潔にまとめたものです。個別モジュールの詳細（各関数の引数/戻り値、DB スキーマの詳細、ExecutionEngine の挙動など）はソース内の docstring を参照してください。必要があれば、導入手順のより具体的な手順（systemd の Unit 作成例や Docker 化、CI/CD 用の設定例など）も追記できます。希望があれば教えてください。