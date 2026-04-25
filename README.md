# KabuSys

日本株自動売買システムの一部モジュール群（実行エンジン、監視、リサーチ、AI 補助等）。  
この README はリポジトリ内の主要スクリプト／モジュールの使い方、セットアップ、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。本リポジトリには以下の主要機能が含まれます。

- ExecutionEngine：発注・注文管理・リスク管理の実行エンジン
- Monitoring：システム状態・注文状況・リスクを定期監視してログ記録・アラート発行、条件による Kill Switch（停止フラグ書き込み）
- Portfolio：銘柄選定・重み計算・ポジションサイズ決定の純粋関数群
- Research：ファクター計算／特徴量解析ユーティリティ（DuckDB を使用）
- AI モジュール：ニュース記事を LLM（OpenAI）でスコアリングしてスコアを DB に保存
- Tools：ペーパートレード検証レポート等のユーティリティスクリプト
- 設定補助：.env の対話式作成（config_setup）、設定検証（validate_config）

設計上の注意点：
- 設定は環境変数（または .env）で行います。必須値は README 内に記載します。
- Paper Trading（KABUSYS_ENV=paper_trading）の場合、SQLite DB は本番 DB と分離されます（data/paper_trading.db がデフォルト）。
- AI（OpenAI）を使用する機能は OPENAI_API_KEY が必要です。

---

## 主な機能一覧

- run_execution (python -m kabusys.run_execution)
  - ExecutionEngine を起動。KABUSYS_ENV によって本番 / ペーパートレードを切替。
  - 停止フラグ（data/stop_requested.flag）で安全に停止可能。
  - プロセス優先度を高く設定（utils/process_priority）。

- run_monitoring (python -m kabusys.run_monitoring)
  - SystemMonitor をポーリングして system_status 等を記録。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。
  - 監視用 DB は環境にかかわらず production の sqlite_path を使用（監視ログの一元化）。

- config_setup (python -m kabusys.config_setup)
  - 対話式ウィザードで .env を生成 / 更新。

- validate_config (python -m kabusys.validate_config)
  - .env と config/*.yaml の存在・基本整合性を事前検証。--strict で警告を fail 扱いにできる。

- AI / Regime / News（kabusys.ai）
  - news_nlp.score_news：raw_news を LLM で評価して ai_scores に保存（OPENAI_API_KEY 必須）。
  - regime_detector.score_regime：ETF の MA と LLM によるマクロセンチメントで市場レジーム判定。

- Tools
  - paper_verification_report：ペーパートレード履歴から検証レポートを生成。

---

## 必須環境変数（最小セット）

最低限設定が必要な環境変数（.env に設定推奨）：

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）

その他主要な環境変数（デフォルト値あり）：

- KABUSYS_ENV：execution モード（development / paper_trading / live） — デフォルト `development`
- DUCKDB_PATH：DuckDB ファイルパス — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH：監視用 SQLite（monitoring）ID — デフォルト `data/monitoring.db`
- PAPER_TRADING_SQLITE_PATH：ペーパートレード専用 SQLite — デフォルト `data/paper_trading.db`
- LOG_LEVEL：ログレベル（DEBUG/INFO/...） — デフォルト `INFO`
- OPENAI_API_KEY：OpenAI API キー（AI 機能利用時必須）
- PAPER_FILL_MODE：ペーパートレードの約定モード（instant/partial/never/reject） — デフォルト `instant`
- MONITOR_POLL_INTERVAL：監視ポーリング間隔（秒） — デフォルト `60`

参考：設定読み込みロジックは `kabusys.config.Settings` に実装されています。

---

## セットアップ手順

1. Python（推奨 3.10+）を用意し仮想環境を作成・有効化：
   ```
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール（主な依存）：
   - duckdb
   - psutil
   - openai (AI 機能を使う場合)
   - PyYAML（validate_config の YAML 検証を行いたい場合）
   例（pip）:
   ```
   pip install duckdb psutil openai PyYAML
   ```

   ※ プロジェクトに requirements.txt がある場合はそれを使ってください。

3. .env を作成する（対話式ウィザード推奨）：
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで入力後、`.env` がプロジェクトルートに生成されます。

4. 設定検証を実行：
   ```
   python -m kabusys.validate_config
   ```
   問題があれば修正してください。`--strict` をつけると警告も失敗扱いになります。

5. データディレクトリなど（logs, data）は自動作成されますが、必要なら事前に作成してください。

---

## 使い方（起動例・運用メモ）

- ExecutionEngine を起動（ローカル、フォアグラウンド）：
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）へ書き込みます。
  - プロセスは `data/execution.pid` に PID を書く設計（設定により変更可）。
  - 停止したい場合はプロセスに SIGINT（Ctrl+C）するか、監視側・運用側から `data/stop_requested.flag` を作成するとループが検知して停止します。

- Monitoring を起動（監視ループ）：
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は `MONITOR_POLL_INTERVAL`（秒）で変更可能。デフォルト 60 秒。
  - 監視は `settings.sqlite_path`（デフォルト `data/monitoring.db`）を使用して永続化します（監視 DB は環境にかかわらず本番用 sqlite_path を使う実装）。
  - 監視ループは `data/stop_requested.flag` による停止をサポート。

- Kill Switch（自動停止）：
  - `kabusys.monitoring.KillSwitch` は `data/kill.flag` に理由文字列を書き込みます。ExecutionEngine 起動時にこのフラグが存在すると起動を抑止したり、Execution 側は kill.flag の存在を確認して停止できます。
  - 本番では KILL_FLAG_CLEAR_ON_START の扱いに注意（Setting で制御）。

- Paper Trading レポート生成：
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  必要なら `--db` でデータベースパスを指定できます。

- AI 機能（ニュース NLP / レジーム判定）
  - 実行前に OPENAI_API_KEY を環境変数に設定してください。
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続を受け取り、DB のテーブルからデータを取得して処理します。
  - API 呼び出しはリトライやフェイルセーフの仕組みが組み込まれていますが、API 料金や rate-limit に注意してください。

- ロギング
  - ログは標準出力（stdout）と日次ローテーションでファイル出力（logs/<app_name>.log）に書かれます。ログディレクトリは環境変数 `LOG_DIR` またはデフォルト `logs/` を使います。
  - ログ設定は `kabusys.utils.logging_setup.setup_logging` で統一されています。

---

## 実行時フラグ・ファイル

- data/stop_requested.flag
  - run_execution/run_monitoring が監視する停止フラグ（存在を検知すると安全に終了）。
- data/kill.flag
  - KillSwitch が書き込む停止指示フラグ。ExecutionEngine 側での扱いに注意（クリア設定など）。
- data/execution.pid
  - ExecutionEngine の PID 保存ファイル（起動時に設定される想定）。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要な Python モジュール構成（`src/kabusys/` 配下）です：

- kabusys/
  - __init__.py
  - config.py                — 環境変数・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — 監視 DB 永続化層
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （注文監視、コード参照）
    - risk_monitor.py        — ドローダウン・ポジション監視
    - monitoring_engine.py   — 各監視を束ねるエンジン
    - kill_switch.py         — kill.flag の生成・管理
    - alert_manager.py       — （アラート送信管理、コード参照）
  - execution/
    - execution_engine.py    — ExecutionEngine 実装（エンジン本体）
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文永続化
    - broker_factory.py      — Broker クライアント生成（Mock / real）
    - reconciler.py          — 約定・状態整合処理
    - risk_manager.py        — 実行時リスク管理
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数決定・資金配分
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（Momentum/Value/Volatility）
    - feature_exploration.py — IC/統計サマリー等
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - data/ (実行時に作成される想定)
  - logs/ (ログ出力先、デフォルト)

（上記は主要ファイルを抜粋したもので、他に補助モジュールがあります）

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では .env を絶対にリポジトリにコミットしないでください。
- kill.flag / stop_requested.flag の扱いは慎重に管理してください。特に本番では自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。
- OpenAI API を利用する場合、API キー管理とコスト管理に注意してください。大量バッチを行うと課金が発生します。
- DuckDB / SQLite のファイルは定期的にバックアップしてください（データ損失対策）。
- validate_config を CI 前に回すことで起動前の基本チェックを自動化できます。

---

## よく使うコマンドまとめ

- .env を作成 / 更新（対話式）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動:
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動:
  ```
  python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README に追記します（サービス化例 / systemd ユニットファイル / DB スキーマ説明 / テスト方法など）。追加で欲しいセクションがあれば教えてください。