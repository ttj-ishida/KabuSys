# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README。  
このドキュメントはコードベース（src/kabusys 以下）の主要機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのプロジェクトです。  
主な機能群は以下の通りです：

- 注文実行エンジン（ExecutionEngine）とブローカークライアント抽象化
- 監視（Monitoring）: システム状態、注文ログ、リスク（ドローダウン・保有数）監視とアラート
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- リサーチ / ファクター計算（DuckDB を用いたファクター計算・IC 計算等）
- AI モジュール（ニュースのセンチメント分析、レジーム判定） — OpenAI API を利用
- 開発支援ツール: .env ウィザード、設定検証、ペーパートレード検証レポート など

設計方針の抜粋:
- 実行環境（KABUSYS_ENV）により挙動を分離（development / paper_trading / live）
- Paper Trading は本番 DB と完全に分離（data/paper_trading.db を使用）
- DuckDB を分析用に使用、SQLite を監視ログ・トレードログに使用
- OpenAI を使う処理は API キーを外部で与える形（テストで差し替えやすい設計）

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動するランチャースクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、専用の paper_trading DB を利用
  - 停止フラグ（data/stop_requested.flag）を検知して安全に停止
  - 起動時にプロセス優先度を "high" に設定（psutil を利用）

- run_monitoring.py
  - SystemMonitor のポーリングループを起動
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）で間隔を上書き可能
  - 監視は常に本番用 sqlite_path を参照してログを残す（環境にかかわらず）

- monitoring モジュール
  - system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_engine, monitoring_db 等
  - system_status / trade_logs / risk_logs / dashboard / positions テーブルの作成・永続化
  - Kill Switch による強制停止（kill.flag 書き込み）

- portfolio モジュール
  - 候補選定（select_candidates）、等重・スコア重み、ポジション決定ロジック（calc_position_sizes）
  - セクターキャップやレジーム乗数適用（apply_sector_cap, calc_regime_multiplier）

- research モジュール
  - ファクター計算（momentum, volatility, value 等）
  - 将来リターン / IC / 統計サマリー（feature_exploration）

- ai モジュール
  - news_nlp: raw_news を集約して OpenAI に送信し銘柄ごとの ai_score を生成
  - regime_detector: ETF やマクロ記事を用いて日次レジーム判定（bull/neutral/bear）
  - OpenAI 呼び出しはリトライ・バリデーションを実装

- tools
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを生成

- 設定ツール
  - config_setup.py: 対話式で .env を生成 / 更新（ウィザード）
  - validate_config.py: 起動前の環境・設定検証 CLI

- utils
  - logging_setup: stdout と日次ローテートファイルハンドラを統一的に設定
  - process_priority: psutil 経由でプロセス優先度 / CPU affinity を扱うユーティリティ

---

## セットアップ手順（開発環境向け）

以下はリポジトリをクローンした前提の一般的な手順です。環境や運用方法に応じて適宜変更してください。

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - requirements.txt がある場合: pip install -r requirements.txt  
     （本コードでは duckdb, psutil, openai, PyYAML などを使っています）
   - 最低限推奨パッケージ:
     - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手作業で作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（代表例）:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG/INFO/...)
     - OPENAI_API_KEY (ai モジュール使用時に必須)

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. ログディレクトリ
   - デフォルトは `logs/`。`LOG_DIR` 環境変数で変更可能。
   - ログファイルは日次ローテーション、30日分保持。

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 / ペーパートレード）
  - python -m kabusys.run_execution
  - ペーパートレードに切り替えるには KABUSYS_ENV=paper_trading を .env に設定
  - 停止:
    - run_execution は起動中にプロジェクトルート/data/stop_requested.flag ファイルが作成されていると停止します
    - Kill Switch (monitoring が判定して作成する data/kill.flag) により停止される場合もあります

- Monitoring 起動（システム監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔の変更:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  - 停止:
    - run_monitoring はプロジェクトルート/data/stop_requested.flag を検出するとループを終了します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスを指定する場合:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI スコア / レジーム判定（プログラム的に呼び出す）
  - OpenAI API キー（OPENAI_API_KEY）が必要
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼ぶ（DuckDB 接続と target_date を渡す）

---

## 重要なファイル / フラグ

- data/stop_requested.flag
  - manual stop 用のフラグ。run_execution / run_monitoring がこれを検知して安全に終了します。

- data/kill.flag
  - Monitoring の KillSwitch が条件を満たしたときに書き込むフラグ（ExecutionEngine を停止させる目的）
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアされる（本番では 0 を推奨）

- data/execution.pid
  - ExecutionEngine が PID 情報を書き込むファイル

---

## 設定（環境変数）主要一覧

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード
  - KABUSYS_ENV: development | paper_trading | live

- データベース
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading DB, デフォルト: data/paper_trading.db)

- AI / OpenAI
  - OPENAI_API_KEY

- ログ
  - LOG_LEVEL (例: INFO)
  - LOG_DIR (デフォルト: logs/)

- Monitoring
  - MONITOR_POLL_INTERVAL (秒、デフォルト 60)
  - CPU / MEM / DISK 閾値: CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

- その他
  - PAPER_FILL_MODE (paper_trading の MockBrokerClient の fill mode。instant/partial/never/reject)
  - KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか。0/1)

---

## ディレクトリ構成（主要ファイル抜粋）

以下は src/kabusys 以下の主要なディレクトリ / ファイル構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings
  - config_setup.py            — .env ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (存在する前提)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在する前提)
  - execution/
    - execution_engine.py (存在する前提)
    - broker_factory.py (存在する前提)
    - order_manager.py (存在する前提)
    - order_repository.py (存在する前提)
    - reconciler.py (存在する前提)
    - risk_manager.py (存在する前提)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                       — 実行時ファイル用ディレクトリ（data/*.db, flags, pid 等）
  - logs/                       — ログ出力ディレクトリ（デフォルト）

（注）一部ファイルは README 内で参照されているが抜粋外の実装ファイルも存在します。

---

## 運用上の注意点 / トラブルシューティング

- .env は絶対に Git にコミットしないでください（config_setup でも明示されています）。
- validate_config で警告が出る場合は内容を確認してから本番実行してください（特に KABUSYS_ENV=live の場合は警告が重要）。
- Paper Trading は本番 DB と完全に分離しているため、運用テストには paper_trading モードを推奨します。
- OpenAI を利用するモジュールは API キーとコストに注意してください。API の失敗時はフェイルセーフで継続する実装になっていますが、挙動を理解しておくこと。
- run_execution/run_monitoring の終了には data/stop_requested.flag を作成する方法（手動）または Monitoring による kill.flag 発動が使えます。運用スクリプト / systemd / supervisor 等を用いる場合は PID ファイル（data/execution.pid）とフラグ参照の扱いを考慮してください。
- ログディレクトリ作成に失敗するとファイルロギングは無効化され stdout のみになります。アクセス権等を確認してください。

---

## 開発メモ / 参考情報

- ロギングはルートロガーへ Stream と TimedRotatingFileHandler（日次・30世代）を設定します。アプリ名ごとに logs/<app_name>.log に出力されます。
- process_priority.set_process_priority は起動時に呼ばれ、Windows/Linux の差を吸収して High/Normal/Low を設定します（psutil が必要）。
- MonitoringDB は起動時に必要なテーブルを冪等に作成し、簡単なマイグレーション（カラム追加）もサポートします。

---

必要であれば、この README をベースに以下の補足を作成できます：
- 開発向けの依存関係一覧（requirements.txt 例）
- systemd / supervisor 用のユニットファイル例
- データベースの初期化スクリプト例
- API 利用時のサンプルコード（OpenAI 呼び出し例）

ご希望があればどれを追加するか指示してください。