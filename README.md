# KabuSys — README

日本株自動売買システム (KabuSys) のドキュメントです。  
本リポジトリはトレーディングエンジン、監視、ポートフォリオ構築、リサーチ、AI 補助モジュールなどを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。以下の主要コンポーネントを含みます。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（本番 / ペーパートレード対応）
- Monitoring：システム稼働・注文状況・リスクを定期監視し、必要時に Kill Switch を発動
- Portfolio：候補選定、重み付け、株数決定、セクター制約などのポートフォリオ構築ロジック
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI：ニュースを LLM(OpenAI) でスコアリングし市場レジーム判定等を支援
- Tools：ペーパートレード検証レポート等のユーティリティスクリプト
- 設定ユーティリティ：.env 生成ウィザード・設定検証 CLI

設計上の注意点：
- .env ファイル（または環境変数）で設定を管理します。プロジェクトルートの `.env` / `.env.local` は自動で読み込まれます（無効化可）。
- `KABUSYS_ENV` によって動作モードを切替（development / paper_trading / live）。
- Paper Trading（`paper_trading`）は本番 DB と完全分離された SQLite（デフォルト `data/paper_trading.db`）を使用します。
- 監視（monitoring）は環境にかかわらず本番の `sqlite_path` を参照する挙動があります（重要）。

---

## 主な機能一覧

- SystemMonitor：CPU / メモリ / ディスク使用率、データ鮮度、実行プロセス検出
- TradeMonitor：発注イベントの滞留・約定異常検出（trade_logs）
- RiskMonitor：ドローダウン監視、ポジション上限監視、ダッシュボード更新
- KillSwitch：条件に応じて `data/kill.flag` を書き込み ExecutionEngine に停止信号を送る
- ExecutionEngine：Broker クライアント（実口座 or Mock）による注文処理、OrderManager、RiskManager、Reconciler 等
- Portfolio モジュール：候補選定、等配分 / スコア重み、リスクベースサイズ計算、セクター制限
- Research モジュール：モメンタム／ボラティリティ／バリューのファクター計算、IC 計算など
- AI モジュール：ニュースの LLM センチメント -> ai_scores テーブル書込、レジーム判定
- ユーティリティ：ログ設定、プロセス優先度 / CPU Affinity 設定、.env ウィザード、設定検証 CLI
- Tools：Paper Trading 検証レポート出力 (期間指定可能)

---

## セットアップ手順（開発向け）

前提
- Python 3.10+（typing の `X | Y` などを使用）
- Git リポジトリルートをプロジェクトルートとして使用

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必要パッケージの一例：
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML のパースを行う場合）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - （実運用では requirements.txt を用意してください。）

3. 環境変数 / .env を用意
   - 対話式ウィザードで .env を生成:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、設定内容を検証:
     ```
     python -m kabusys.validate_config
     ```
   - 自動読み込みを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. データディレクトリ等
   - デフォルトで使用されるファイル・ディレクトリ:
     - data/kabusys.duckdb (DuckDB) — 環境変数 DUCKDB_PATH
     - data/monitoring.db (SQLite) — 環境変数 SQLITE_PATH
     - data/paper_trading.db (Paper Trading 専用 SQLite)
     - data/execution.pid, data/stop_requested.flag, data/kill.flag
     - logs/ ディレクトリ（デフォルト）にログファイル出力

---

## 主要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 時の DB、デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject ; デフォルト: instant)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL ; デフォルト: INFO)
- LOG_DIR (ログ出力先ディレクトリ)
- OPENAI_API_KEY (AI モジュール使用時に必要)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか; 0/1)

サンプル（最小） .env の例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方（実行例）

- 監視ループを起動（Monitoring）:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視はデフォルトで本番用 sqlite_path を使用（KABUSYS_ENV に依らず）。
  - 停止: プロジェクトルートの `data/stop_requested.flag` を作成するとループは終了します（監視側はこのファイルを監視）。

- 実行エンジンを起動（Execution Engine）:
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使い `data/paper_trading.db` に記録（本番 DB と分離）。
  - 起動時、`data/stop_requested.flag` が既に存在する場合は起動せず終了します。
  - 実行中は `data/execution.pid` が使用されます。停止は `data/stop_requested.flag` の作成で行います。

- 設定ウィザード（.env の生成・編集）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）:
  ```
  python -m kabusys.validate_config
  ```
  - `--strict` を付けると警告も失敗扱い（exit code 1）になります。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプション、または環境変数 `PAPER_TRADING_SQLITE_PATH` を指定可能。

- ロギング:
  - すべての起動スクリプトは `kabusys.utils.logging_setup.setup_logging` を通じてログを設定します。
  - デフォルトはコンソール出力 + 日次ローテーションされたファイル出力（logs/<app_name>.log、30日保存）。
  - ログディレクトリは `LOG_DIR` 環境変数または引数で変更可能。

- プロセス優先度:
  - 起動スクリプトは最初に `set_process_priority("high")` を呼びます（psutil を使用）。権限不足時は警告になりスキップされます。

- Kill Switch / 停止フロー:
  - RiskMonitor 等が条件を満たすと `KillSwitch` が `data/kill.flag` を書き込みます。ExecutionEngine はこれを検出して安全停止します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番環境では推奨されません）。

---

## 開発者向けメモ

- DuckDB 接続を多用しており、リサーチ系は DuckDB の SQL を組み合わせて計算します（prices_daily / raw_financials 等のテーブルを前提）。
- AI モジュール（news_nlp, regime_detector）は OpenAI を利用します。API キーの扱いに注意してください。API エラー時はフェイルセーフ（スコア = 0 など）で継続する設計です。
- DB マイグレーションの軽い処理（列追加など）を `monitoring_db.init_monitoring_db` が担います。冪等な初期化コードになっています。
- テスト時はモジュールの API 呼び出し（OpenAI 等）をモックすることを想定した設計になっています（内部で呼び出す関数をパッチ可能）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理、自動 .env ロードロジック
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループのエントリ
  - run_execution.py — ExecutionEngine のエントリ
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ永続化層（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （発注ログ監視；実装参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — 通知（LINE 等）管理（実装参照）
  - execution/
    - execution_engine.py — ExecutionEngine（エンジン本体）
    - broker_factory.py — Broker クライアント生成（Mock / 実ブローカー）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注系ロジック
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 発注株数計算、サイズ調整
    - risk_adjustment.py — セクター制約、レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 計算
    - feature_exploration.py — forward returns, IC, summary...
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力

（上記は主要ファイルの抜粋です。ファイル内の関数／クラスはそれぞれ詳細な docstring が付与されています。）

---

## よくある運用上の注意

- 本番モード（KABUSYS_ENV=live）では設定ミスが重大な損失につながるため、`python -m kabusys.validate_config` を必ず実行して警告・エラーを確認してください。
- kill.flag / stop_requested.flag の取り扱いに注意：手動で削除する際は本当に意図した操作か確認してください。
- OpenAI を利用する処理は API コストが発生します。スコアリング周波数やバッチサイズの調整を推奨します。
- ログディレクトリの権限やディスク容量の監視を行ってください（ログが溜まる可能性）。

---

必要に応じて README に追記します。特定のセットアップ（例：Docker、systemd サービス化、CI テスト）を希望する場合は詳細を教えてください。