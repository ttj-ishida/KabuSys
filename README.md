# KabuSys

日本株向けの自動売買 / 解析プラットフォーム（軽量モジュール群）。  
このリポジトリは以下の主要機能を提供します: 発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築ユーティリティ、ファクター計算・リサーチ、ニュースの NLP によるスコアリング、運用支援ツール類。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境初期化（.env ウィザード）
  - 設定検証
  - 実行: ExecutionEngine / Monitoring
  - ペーパートレード検証レポート
  - プログラムからの利用例（簡易）
- ディレクトリ構成
- 重要な環境変数 / ファイル
- 運用上の注意

---

## プロジェクト概要

KabuSys は日本株自動売買システムのためのモジュール群です。主に以下の用途を想定しています。

- 日次のシグナル生成・ポートフォリオ構築（純粋関数群）
- 発注エンジン（実際のブローカー API またはモックを利用）
- 実行状況・システム状態の監視と Kill Switch
- DuckDB を利用した研究・ファクター計算
- OpenAI を用いたニュースセンチメント計算（ai モジュール）
- ペーパートレードの評価・レポート生成

設計方針の一部:
- DB（SQLite / DuckDB）での永続化と切り分け（paper_trading は別 DB）
- 自動化・運用を考慮したログ・プロセス優先度制御・フラグファイル方式の停止
- ルックアヘッドバイアスに配慮した日付処理（APIやtoday参照を避ける箇所あり）

---

## 機能一覧

主な機能（モジュール単位）

- kabusys.config / config_setup.py / validate_config.py
  - 環境変数の自動ロード（.env / .env.local）、対話式 .env 作成ウィザード、設定検証 CLI
- 実行系
  - run_execution.py — ExecutionEngine の起動スクリプト（本番 / paper_trading 切替）
  - execution.* — ブローカー抽象化、注文管理、リスク管理、リコンサイラ等
- 監視系
  - run_monitoring.py — SystemMonitor を周期実行するスクリプト
  - monitoring.* — SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, MonitoringDB
- ポートフォリオ構築（pure functions）
  - portfolio.* — 候補選定、重み計算、ポジションサイジング、セクター制限、レジーム乗数
- 研究用
  - research.* — ファクター計算（momentum/value/volatility）、将来リターン、IC 等
- AI（LLM）連携
  - ai.news_nlp — ニュースを集約して OpenAI に投げ、銘柄別スコアを ai_scores に書き込む
  - ai.regime_detector — MA200 とマクロニュースの LLM スコアを組み合わせ市場レジーム判定
- ツール
  - tools.paper_verification_report — ペーパートレード DB から検証レポートを生成
- ユーティリティ
  - utils.logging_setup — 統一ログ設定（Stream + 日次ローテート）
  - utils.process_priority — Windows / POSIX を吸収したプロセス優先度・CPU affinity 設定

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. Python 仮想環境を作成・有効化（推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 必要パッケージをインストール（最低限）
   ```
   pip install duckdb psutil openai
   ```
   追加（YAML 検証や便利機能のため）:
   ```
   pip install pyyaml
   ```
   ※ sqlite3 は標準ライブラリです。

4. 環境変数設定
   - 対話式ウィザードで .env を生成:
     ```
     python -m kabusys.config_setup
     ```
     ウィザード完了後は `.env` に設定が保存されます。

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   問題がなければ OK が出ます。厳密モード:
   ```
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリの作成（必要に応じて手動で）
   - デフォルトでは `data/`、ログは `logs/` に出力されます。
   - 実行時に自動作成されることが多いですが、権限等に注意してください。

---

## 使い方

### 基本コマンド

- 実行エンジン（ExecutionEngine）を起動:
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV で切替
  ```
  python -m kabusys.run_execution
  ```
  ペーパートレードを使うには:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  ペーパートレード時は MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` に記録します。

- 監視ループを起動:
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）で上書き可能:
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  DB パスは `--db`、または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定できます。

### .env / 環境変数（主要）

主な環境変数（省略時のデフォルトを併記）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (既定: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — 既定: development
- DUCKDB_PATH (既定: data/kabusys.duckdb)
- SQLITE_PATH (既定: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (既定: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject) — 既定: instant
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — 既定: INFO
- LOG_DIR (既定: logs/)
- OPENAI_API_KEY — ai モジュール使用時に必要
- MONITOR_POLL_INTERVAL — monitoring ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — (0/1) 起動時に kill.flag を自動クリアするか（本番は 0 推奨）

自動 .env 読み込みはデフォルトで有効。もし自動ロードを無効化する場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

### Kill Switch / 停止フラグ

- 監視 -> ExecutionEngine 停止はファイルフラグで行います:
  - kill.flag: ExecutionEngine に対する停止トリガー（監視側が書き込む）
  - stop_requested.flag: 監視ループ・エンジン自身を停止させる際の内部フラグ（`data/stop_requested.flag` など）
- Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` とすると起動時に kill.flag を自動で削除します（本番では推奨されません）。

### プログラムからの利用（簡易）

- ニューススコア計算:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
  ```
- レジームスコア計算:
  ```python
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
  ```

※ 上記は OpenAI API キーが必要です。API 呼び出し失敗時はフェイルセーフとして一定のフォールバック（0.0 など）を行う実装箇所がありますが、実運用ではキーやレート制限の管理に注意してください。

---

## ディレクトリ構成

（root 以下 `src/kabusys` を想定）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理・自動 .env ロード
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - execution/                — 発注エンジン関連（broker, order_manager, risk_manager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard）
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (ランタイムで生成される想定。DB・flag等を保持)
  - logs/ (ログ出力先、setup_logging で作成)

重要ファイル例:
- data/monitoring.db (SQLite: 監視ログデフォルト)
- data/paper_trading.db (SQLite: ペーパートレード時の記録)
- data/kabusys.duckdb (DuckDB: 価格・財務・ニュース等分析用)
- data/kill.flag, data/stop_requested.flag, data/execution.pid

---

## 重要な設計・運用上の注意

- .env は機密情報を含むため絶対に Git にコミットしないこと。
- 本番環境（KABUSYS_ENV=live）では特に LINE 通知設定や Kill Switch 設定を事前に確認してください。validate_config は live 向けの警告を出します。
- OpenAI 等外部 API を使う処理はレート制限やエラーを考慮したロジック（リトライやフェイルセーフ）を実装していますが、運用時は API キー管理とコストに注意してください。
- run_execution / run_monitoring はそれぞれプロセス優先度を高（"high"）に設定します。環境によっては権限不足で設定に失敗する場合がありますが、その場合は警告が出てスキップされます。
- DB マイグレーションは簡易的なチェック（列追加）を行います。複雑なスキーマ変更時は事前にバックアップを取ってください。

---

必要に応じて README を拡張します（例: API 詳細、ExecutionEngine の設定例、monitoring の通知設定、テスト手順など）。どの情報を追加しましょうか？