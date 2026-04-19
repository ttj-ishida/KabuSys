# KabuSys

日本株向け自動売買システムのパッケクト（コード断片ベースの README）。  
以下はこのリポジトリの主要コンポーネント、セットアップ、起動方法、ディレクトリ構成の概略です。

注意: 実行には環境変数の設定や外部ライブラリが必要です。実行前に必ず設定検証を行ってください（`kabusys.validate_config` を参照）。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ／監視を目的としたモジュール群です。主な責務は次のとおりです。

- ExecutionEngine（発注処理）: ブローカークライアント経由で注文を作成・管理する（本番 / ペーパートレード対応）。
- Monitoring（監視）: システム状態、発注ログ、リスク（ドローダウン／ポジション上限）を定期的にチェックし、アラートや Kill Switch（停止フラグ）を管理する。
- Research / AI: DuckDB 上の市場データからファクター計算や将来リターン、ニュース NLP によるセンチメント評価、レジーム判定を行う。
- Portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制約などの純粋関数群。
- Tools: ペーパートレード検証レポート生成などのユーティリティ。

---

## 主な機能一覧

- 環境設定ウィザード（対話式 .env 作成）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の検証）: kabusys.validate_config
- Execution 起動スクリプト（本番 / ペーパートレード切り替え）: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に分離保存
- Monitoring 起動スクリプト（ポーリング監視）: run_monitoring.py
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用
- 監視永続化（SQLite）: monitoring_db — system_status / trade_logs / positions / risk_logs / dashboard
- RiskMonitor / TradeMonitor / SystemMonitor / KillSwitch / AlertManager（監視フロー）
- Portfolio 構築: 候補選定、等金額/スコア加重、リスクベースのポジション数計算、セクター上限、レジーム乗数
- Research: ファクター（モメンタム／ボラティリティ／バリュー）計算、将来リターン、IC 計算、統計サマリー
- AI: ニュース NLP による銘柄別センチメント（OpenAI 利用）、市場レジーム判定（MA + LLM）
- ツール: Paper Trading の検証レポート生成（paper_verification_report）

---

## 必要な依存関係（主なもの）

このコードベースから判別できる主要依存ライブラリ:

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config YAML のチェックはオプショナル。インストールされていない場合は警告でスキップ）

インストール例（仮の requirements ファイルがない場合の一例）:
```
python -m pip install "duckdb>=0.7" psutil openai PyYAML
```

（バージョンは利用環境に合わせて調整してください）

---

## セットアップ手順

1. リポジトリをクローン / パッケージを展開する。

2. Python 3.10+ の仮想環境を作成・有効化：
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows (PowerShell / CMD による)
   ```

3. 必要なパッケージをインストール（上記参照）:
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. 環境変数設定（.env）:
   - 対話式ウィザードで .env を作成:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）が設定されていることを確認してください。
   - .env の自動読み込みはデフォルトで有効（Settings モジュールがプロジェクトルートを探索して .env / .env.local を読み込みます）。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 設定検証を実行:
   ```
   python -m kabusys.validate_config
   # Strict モード（警告もエラー扱い）:
   python -m kabusys.validate_config --strict
   ```

6. 必要に応じてデータディレクトリ作成:
   - デフォルトのパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading DB: data/paper_trading.db
     - ログ: logs/
   - ログディレクトリは自動作成されますが、権限等を確認してください。

---

## 使い方（起動・主要コマンド）

以下は最小限の起動・実行例。

- ExecutionEngine（発注エンジン）起動:
  - 本番モード:
    ```
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - ペーパートレード（MockBroker を使用、専用 DB に保存）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 備考:
    - ペーパートレード用 DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可能（デフォルト: data/paper_trading.db）。
    - `PAPER_FILL_MODE`（instant/partial/never/reject）で Mock の約定挙動を制御できます。
    - 起動時、`data/stop_requested.flag` や `data/kill.flag` 等のフラグ類により起動・停止挙動が制御されます。
    - 実行中は `data/execution.pid` に PID が書き込まれます。

- Monitoring（監視）起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録します。

- 設定ウィザード（.env 作成）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（CLI）:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` で DB を指定することも可能。

- AI / Regime / News スコア関連（プログラム API）:
  - OpenAI を使う処理（news_nlp.score_news, ai.regime_detector.score_regime）は `OPENAI_API_KEY` を環境変数か関数引数で渡す必要があります。
  - 失敗時はフェイルセーフ（多くのケースで 0.0 を使う等）で継続するよう設計されています。

---

## 運用に関する重要な点

- Kill Switch / stop フラグ:
  - kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は ExecutionEngine に対する停止シグナルです（KillSwitch により書き込まれます）。
  - stop_requested.flag（data/stop_requested.flag）は run_monitoring.py/run_execution.py が検出してループを終了するために使われます。
  - 本番での誤操作防止のため、`KILL_FLAG_CLEAR_ON_START` 環境変数を 1 にすると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

- ログ:
  - デフォルトで console（stdout）と日次ローテートファイル（logs/<app_name>.log）へ出力します。ログディレクトリは自動で作成されますが、権限等を確認してください。

- Database:
  - Monitoring 用 SQLite（monitoring.db）と分析用 DuckDB（kabusys.duckdb）を使用します。ペーパートレード時は paper_trading.db に分離されます。
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` は冪等的にテーブルと必要なカラムのマイグレーションを行います。

---

## ディレクトリ構成（抜粋）

（このリポジトリで提供されている主要モジュールを反映）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading レポート生成 CLI
  - utils/
    - logging_setup.py        — 統一ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite 永続化層
    - system_monitor.py       — システム状態監視
    - risk_monitor.py         — ドローダウン・ポジション監視
    - kill_switch.py          — kill.flag の管理
    - monitoring_engine.py    — モニタリングの束ね
    - ...                     — trade_monitor, alert_manager 等（実装ファイルが存在する想定）
  - execution/                — エンジン周り（ブローカーファクトリ等）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 発注株数計算
    - risk_adjustment.py      — セクター制約・レジーム乗数
  - research/
    - factor_research.py      — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py  — 将来リターン / IC / サマリー
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 経由）による銘柄スコア
    - regime_detector.py      — レジーム判定（MA + LLM）
  - data/                     — データファイル（例: monitoring.db, paper_trading.db 等、起動時に作成される）
  - logs/                     — ログ出力先（デフォルト）

---

## 環境変数（代表的なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development|paper_trading|live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
- LOG_LEVEL — デフォルト INFO
- OPENAI_API_KEY — ニュース NLP / レジーム判定で必要
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1）

詳細は `src/kabusys/config.py` と `src/kabusys/config_setup.py` を参照してください。

---

## 開発・拡張のヒント

- DuckDB 接続を受け取るリサーチ関数（research/*.py）は外部 API を使わずに SQL + Python で完結するよう設計されています。単体テストが書きやすい純粋関数群が多く含まれます。
- AI (OpenAI) 関連はリトライや入力トリミング、レスポンス検証を慎重に実装しており、API 失敗時もシステムが堅牢に継続するように設計されています。
- 監視ロジックは MonitoringDB を通して永続化され、RiskMonitor / KillSwitch により自動停止やアラートが発生します。運用時は `KILL_FLAG_CLEAR_ON_START` の設定に注意してください。

---

必要であれば README に含めるサンプル .env テンプレート、起動スクリプトの systemd ユニット例、コンテナ化（Dockerfile）や CI の設定例なども作成できます。どの情報を追加しますか？