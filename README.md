# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ向け README（日本語）

概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。  
主な目的は以下です。

- 日次・リアルタイムのマーケットデータを用いたファクター計算とシグナル生成（research）
- ポートフォリオ構築、ポジションサイズ計算、セクター制限などの投資判断ロジック（portfolio）
- 発注エンジン（ExecutionEngine）と注文管理、リスク管理（execution）
- システム稼働・注文・リスクの監視（monitoring）
- ニュース NLP を用いた銘柄・マクロセンチメント評価（AI モジュール）
- ペーパートレード用の分離 DB と検証ツール（tools）

本 README はローカル実行やデプロイ時の基本的な流れを説明します。

---

## 機能一覧（主なモジュール）

- config / config_setup / validate_config
  - 環境変数（.env）管理、対話式ウィザード、起動前設定検証
- run_execution.py
  - ExecutionEngine の起動スクリプト
  - `KABUSYS_ENV=paper_trading` のときは MockBroker を使用し、paper_trading 用 DB（分離）へ記録
- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可）
- monitoring
  - system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_engine
  - 監視ログ永続化（SQLite）、Kill Switch（停止フラグ）など
- execution
  - ブローカーファクトリ、ExecutionEngine、OrderManager、RiskManager、Reconciler（発注ワークフロー）
- portfolio
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- research
  - ファクター計算（momentum, volatility, value 等）、将来リターン、IC 計算、統計サマリ
  - DuckDB を用いた分析処理を想定
- ai
  - news_nlp: OpenAI を用いたニュースセンチメント → ai_scores テーブルへ書き込み
  - regime_detector: マクロセンチメントと ETF の MA に基づく市場レジーム判定
- tools
  - paper_verification_report: ペーパートレード DB から検証レポート生成
- utils
  - logging_setup（統一ログ設定）、process_priority（プロセス優先度 / CPU affinity）

---

## 前提 / 必要な環境

- Python 3.9+（実際の要件ファイルに従ってください）
- 主要依存（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証時に推奨）
- ローカルに `data/` と `logs/` ディレクトリが作成される（自動作成される箇所もありますが手動で作ると確実）

依存はプロジェクトの requirements.txt があればそれを使ってください。無い場合の例:

```
pip install duckdb psutil openai pyyaml
```

（プロダクションでは仮想環境を用いることを推奨）

---

## 環境変数（主なもの）

主に .env ファイルで管理します。対話式ウィザードで作成可能（後述）。

必須（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要な設定例
- KABUSYS_ENV: execution モード（development | paper_trading | live）
- DUCKDB_PATH: DuckDB ファイル（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視 DB（デフォルト `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など

特記事項
- Monitoring は run_monitoring では環境に関わらず本番 sqlite_path を使用します（監視ログは共通で記録）。
- Paper trading は発注 DB を明確に分離（PAPER_TRADING_SQLITE_PATH）します。

---

## セットアップ手順（簡易）

1. リポジトリをクローンしてワークディレクトリに移動
2. 仮想環境を作成・有効化
3. 依存をインストール
   - 例: `pip install -r requirements.txt` または上記パッケージを個別インストール
4. 環境変数ファイル作成（対話式ウィザード推奨）
   - 実行: `python -m kabusys.config_setup`
   - ウィザードは `.env`（デフォルト）を生成します
5. 設定検証
   - 実行: `python -m kabusys.validate_config`
   - 警告も厳格に扱う場合: `python -m kabusys.validate_config --strict`
6. データディレクトリを手動で準備（任意）
   - `mkdir -p data logs`
   - 実行スクリプトが自動で作ることもありますが事前に作成することでパーミッション問題を回避できます

---

## 使い方（起動 / 停止 / ツール）

基本的にパッケージをモジュールとして実行します。

1. ExecutionEngine 起動（本番 or paper_trading）
   - 本番（KABUSYS_ENV が .env に設定されている場合はそのまま）
     ```
     python -m kabusys.run_execution
     ```
   - 環境変数で明示する例（ペーパートレードで起動）
     ```
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     ```
   - 起動時に `data/execution.pid` に PID が書かれます（デフォルト）。停止フラグ `data/stop_requested.flag` があれば起動しません。
   - ペーパートレード時は MockBroker を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録されます。

2. Monitoring 起動
   - 起動:
     ```
     python -m kabusys.run_monitoring
     ```
   - ポーリング間隔を環境変数で上書き:
     ```
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     ```
     デフォルトは 60 秒。0 や負数は無効で 60 秒にフォールバックします。
   - 監視は `SQLITE_PATH`（デフォルト `data/monitoring.db`）を使用してログを永続化します（環境に依らず本番用 path を使う設計になっています）。
   - 停止: 実行中に `data/stop_requested.flag` を作成するとループ検知して終了します。

3. Stop / Kill
   - Kill Switch（条件を満たした場合）で `data/kill.flag` が書き込まれ、ExecutionEngine 側で停止シグナルとして利用できます。
   - 起動時に `KILL_FLAG_CLEAR_ON_START=1` が設定されていると kill flag を自動クリアします（本番では `0` を推奨）。

4. AI / レジーム判定（OpenAI）
   - news_nlp / regime_detector を使うには `OPENAI_API_KEY` を設定してください。
   - API 呼び出しは `gpt-4o-mini` を使う構成になっています（コストに注意）。

5. ペーパートレード検証レポート
   - 実行:
     ```
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     ```
   - デフォルト DB: `data/paper_trading.db`、`--db` オプション、または `PAPER_TRADING_SQLITE_PATH` 環境変数で指定可能。

---

## ログ / DB / データファイル

- ログ
  - デフォルトのログディレクトリ: `logs/`
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）により console（stdout）と日次ローテーションファイルを出力します
  - 環境変数 `LOG_DIR` で変更可能

- データ / DB（デフォルト）
  - DuckDB: `data/kabusys.duckdb`（分析用）
  - 監視 SQLite: `data/monitoring.db`
  - ペーパートレード SQLite: `data/paper_trading.db`（paper_trading モード用）
  - PID / フラグ:
    - 実行 PID: `data/execution.pid`（ExecutionEngine が使用）
    - 停止フラグ（run scripts 停止）: `data/stop_requested.flag`
    - Kill フラグ（KillSwitch）: `data/kill.flag`

- DB 初期化
  - run_monitoring / run_execution 起動時に `init_monitoring_db()` で必要なテーブル（system_status, trade_logs, positions, risk_logs, dashboard）を冪等に作成します。追加のマイグレーション（列追加等）も自動処理されます。

---

## 開発者向けメモ / 注意点

- Paper trading 安全設計
  - `paper_trading` モードでは MockBroker を使い、本番 DB と完全に分離する設計になっています（DB パスに注意）。
- ルックアヘッドバイアス対策
  - research / ai / regime_detector 等の関数は日付参照で明示的に target_date を受け取り、内部で `date.today()` に依存しない設計です。
- OpenAI 呼び出し
  - rate limit / 5xx / タイムアウトは指数バックオフでリトライ、失敗時はフェイルセーフ（スコア 0 へフォールバックまたはスキップ）で継続する実装です。
- プロセス優先度
  - 起動スクリプトは最初に `set_process_priority("high")` を呼びます。環境によっては権限不足で失敗し警告に留まります。
- logging_setup
  - 既存ハンドラを一旦削除して再設定するため、別途ログ設定を行う際は挙動に注意してください。

---

## ディレクトリ構成（抜粋）

以下はソースツリー内の主要なディレクトリとモジュールの概略です（`src/kabusys/` 起点）。

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - ai/
    - news_nlp.py           — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py    — 市場レジーム判定（MA + macro sentiment）
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層（テーブル生成・操作）
    - system_monitor.py     — CPU/メモリ/ディスク・データ鮮度監視
    - trade_monitor.py      — 注文滞留や約定の監視（省略ファイル残存）
    - risk_monitor.py       — ドローダウン / ポジション数監視
    - kill_switch.py        — kill.flag 管理
    - monitoring_engine.py  — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py      — アラート送信（LINE 等、実装に依存）
  - execution/
    - execution_engine.py   — 実行ロジック（セッション管理）
    - broker_factory.py     — BrokerClient の生成（Mock / 実運用）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py  — 候補選定 / 重み
    - position_sizing.py    — 株数算出・aggregate cap
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py    — momentum/value/volatility 等の計算
    - feature_exploration.py— forward returns / IC / summary
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity
  - data/                   — 実行時に使用されるデータ・DB・フラグ（git 管理しない）

（上記はソース内に存在する主要ファイルを抜粋したものです）

---

## よく使うコマンドまとめ

- .env 作成（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution 起動
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動（ポーリング間隔変更）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 最後に / 注意事項

- .env は機密情報（API トークンやパスワード）を含むため、絶対に Git にコミットしないでください。
- 本レポジトリには実際のブローカー連携を行うコードが含まれます。`KABUSYS_ENV=live` の設定は慎重に行ってください（validate_config は live 設定時に警告を出します）。
- OpenAI 等の外部 API を使用する機能は API 使用量・コストに依存します。鍵やコスト管理に注意してください。

---

README の補足や追記したい項目があれば教えてください。必要に応じてコマンド例や設定のサンプル .env（プレースホルダ）も用意できます。