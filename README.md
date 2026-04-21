# KabuSys

日本株自動売買システムの軽量モジュール群。ポートフォリオ構築、ポジションサイジング、監視、実行（ExecutionEngine）、AI を用いたニュースセンチメント / レジーム判定などを含むユーティリティ群です。

以下はこのリポジトリの概要、機能、セットアップ・使い方、ディレクトリ構成の簡潔な README です。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのコンポーネント群です。主な目的は次の通りです。

- ファクター計算・研究（DuckDB をデータソースとして利用）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- 実行エンジン（ブローカー抽象化により本番 / ペーパートレードを切り替え）
- 監視（システム状態・注文状態・リスク監視、Kill Switch）
- AI（OpenAI を用いたニュースセンチメント、レジーム判定）
- 開発向けツール（環境ウィザード、設定検証、ペーパートレード検証レポート）

設計上、以下の点に配慮しています。
- 本番 DB とペーパートレード DB の分離
- ルックアヘッドバイアスを避ける設計（API 呼び出しや日付参照の扱い）
- フェイルセーフ（API 失敗時は安全なフォールバックで継続）
- ロギングとログローテーションを統一

---

## 主な機能一覧

- portfolio/
  - 候補選定（score / equal）
  - 重み計算（等配分、スコア重み）
  - ポジションサイズ計算（リスクベース、lot 単位で丸め）
  - セクターキャップ適用、レジーム乗数
- research/
  - momentum / volatility / value ファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- ai/
  - news_nlp: OpenAI を用いたニュースセンチメント集約・スコアリング（ai_scores へ書き込み）
  - regime_detector: ETF (1321) の MA200 とマクロニュースで市場レジーム判定
- monitoring/
  - system_monitor: CPU/メモリ/Disk、データ鮮度、プロセス監視
  - trade_monitor: 注文の滞留・約定異常の監視（trade_logs 参照）
  - risk_monitor: ドローダウン・ポジション上限の監視、ダッシュボード更新
  - kill_switch / monitoring_engine: 条件により ExecutionEngine 停止フラグを書き込む
  - monitoring_db: SQLite を用いた監視ログ永続化（テーブル作成・マイグレーション対応）
- execution/
  - ExecutionEngine（ブローカー抽象化、RiskManager、OrderManager 等）
  - BrokerClientFactory により KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し DB を分離
- utils/
  - logging_setup: stdout と日次ローテートファイルを統合的に設定
  - process_priority: OS に依存しないプロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report: ペーパートレード履歴を解析して PASS/FAIL レポート出力
- CLI 補助
  - config_setup: 対話式で .env を作成
  - validate_config: .env と config/*.yaml の事前チェック

---

## 前提条件 / 依存ライブラリ

（代表的なもの）
- Python 3.8+ （型ヒントなどの利用により互換性のあるバージョンを推奨）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config YAML 内容検証を行う場合、なくても動作はするが検証をスキップ）

インストール例：
```bash
pip install duckdb psutil openai pyyaml
```
※ 実運用では requirements.txt / Poetry 等で管理してください。

---

## セットアップ手順

1. リポジトリをクローン／展開

2. 必要パッケージをインストール（上記参照）

3. 環境変数設定（.env）
   - 対話型で .env を作成する（推奨）
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは .env を手動作成（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` は必須）
   - 自動 .env ロードはデフォルトで有効（プロジェクトルートの .env / .env.local を読み込み）
     - 無効化する場合:
       ```bash
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
       ```

4. 設定検証（起動前に推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL としたい場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / PID / ログ パス:
     - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可）
     - SQLite (monitoring): data/monitoring.db（SQLITE_PATH）
     - Paper trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
     - PID ファイル: data/execution.pid（PID_FILE_PATH）
     - ログディレクトリ: logs/（LOG_DIR で変更可）

---

## 実行方法（使い方）

基本的にモジュールをモジュールモードで起動します。

- 監視ループ起動（Monitoring）
  ```bash
  python -m kabusys.run_monitoring
  ```
  オプション・挙動:
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に settings.sqlite_path（production sqlite_path）を使用します（KABUSYS_ENV に依存しない）。
  - 停止はプロジェクトルートの data/stop_requested.flag を作成することで次回ポーリング時に終了します。

- 実行エンジン起動（ExecutionEngine）
  ```bash
  python -m kabusys.run_execution
  ```
  特記事項:
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）へ記録します。本番 DB と完全に分離されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中に停止させるには data/stop_requested.flag を作成するか、監視側の KillSwitch によって data/kill.flag が作成されるとそのシグナルで止められます。
  - 実行前に kill flag を自動クリアするかは `KILL_FLAG_CLEAR_ON_START` 環境変数（"1" でクリア）で制御可能（本番では "0" 推奨）。

- Paper Trading 検証レポート（ツール）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定できます。

- AI 機能（プログラム API）
  - OpenAI を使う機能（news_nlp, regime_detector）を使うには `OPENAI_API_KEY` を環境変数に設定するか、関数呼び出し時にキーを渡します。
  - 例（Python REPL 等）:
    ```python
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    # score_news(conn, target_date, api_key="sk-...")
    ```

- `.env` / 設定の再検証
  - 設定を変更したら `python -m kabusys.validate_config` で起動前にチェックしてください。

---

## 重要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

運用 / 動作制御:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）

自動ロード制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

監視・停止フラグ:
- data/stop_requested.flag — run_monitoring / run_execution の起動ループを終了させるためのファイル（存在チェック）
- data/kill.flag — KillSwitch が書き込む ExecutionEngine 停止用フラグ（自動クリアは設定次第）

---

## ログと PID

- ログ: `kabusys.utils.logging_setup.setup_logging` により stdout に加え `logs/<app_name>.log` に日次ローテーションで出力（30日保持）。
- PID: デフォルト PID ファイルは `data/execution.pid`（Settings.pid_file_path で変更可）。

---

## 開発者向けメモ

- monitoring_db.init_monitoring_db は冪等でテーブル作成を行い、マイグレーション（カラム追加）処理も一部含みます（例: trade_logs に latency_ms カラム追加など）。
- AI 呼び出し部分はネットワークエラー / レート制限に対してリトライ実装がありますが、API キー未設定時は例外を送出します。 テストでは _call_openai_api をモックしてください。
- 設計は「可能な限り DB 書き込みは冪等に」「ルックアヘッドバイアスを避ける」「部分失敗でも他データを破壊しない」方針です。

---

## ディレクトリ構成

（主要ファイル / モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動ロード / Settings
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — Monitoring ポーリングループ起動
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - monitoring_engine.py    — 各 Monitor を束ねる
    - system_monitor.py       — CPU / メモリ / データ鮮度 / プロセス監視
    - trade_monitor.py        — （注文監視、ファイル内で利用）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みロジック
    - alert_manager.py        — （アラート送信）※実装参照
  - execution/
    - execution_engine.py     — ExecutionEngine（セッション実行）
    - broker_factory.py       — BrokerClientFactory（本番 / Mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI）
    - __init__.py
  - data/                     — 実行時生成される想定ディレクトリ（DB / flags / pid など）
  - config/                   — YAML 設定ファイル（テンプレート / 生成スクリプト参照）

---

## よくある運用フロー（例）

1. 初期セットアップ:
   - pip install ...
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. データ準備（DuckDB に prices_daily 等のテーブルを作る）

3. 監視プロセス起動:
   - `python -m kabusys.run_monitoring` をデーモン化して常駐

4. 実行プロセス起動（本番 / ペーパー切替は KABUSYS_ENV）:
   - `python -m kabusys.run_execution`

5. 問題発生時:
   - run_monitoring が条件を検出すると `data/kill.flag` を書き込み、ExecutionEngine 停止を誘発する
   - 手動停止は `data/stop_requested.flag` を作成してプロセスに停止信号を与える

---

この README はコードベースの現状に基づく簡易ドキュメントです。実運用ではさらに詳細な運用手順書、監視アラート設定、回復手順を整備してください。必要であれば README を拡張して起動オプション、ログの解析方法、テスト手順、CI/CD 設定例などを追加できます。