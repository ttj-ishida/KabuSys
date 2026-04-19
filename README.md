# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、戦略の研究・ポートフォリオ構築・注文実行・監視・AIによるニュース評価までを含む自動売買フレームワークです。README は開発者・運用者向けの概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

主な役割:

- ファクター計算・リサーチ（duckdb ベース）
- ポートフォリオ構築（候補選定・重み計算・株数決定）
- ExecutionEngine による注文発行（本番 / ペーパートレード分離）
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- OpenAI を利用したニュースセンチメント評価（AIモジュール）
- 紙トレード検証レポート作成ツール

設計上のポイント:

- 環境変数 / .env による設定（自動ロード機能あり）
- Paper trading は本番 DB と分離（デフォルト: `data/paper_trading.db`）
- ログは stdout と日次ローテートされたファイル（`logs/<app>.log`）
- 安全措置: Kill Switch、停止フラグファイル、プロセス優先度設定 等

---

## 主な機能一覧

- config
  - .env の自動読み込み / 設定管理（`kabusys.config.Settings`）
  - 対話式ウィザードで .env を生成（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）
- execution
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
  - ブローカークライアントファクトリ（本番/Mock 切替）
  - リスク管理・オーダー管理・整合処理
- monitoring
  - System / Trade / Risk の各モニタ
  - Monitoring DB (SQLite) の初期化・永続化（`monitoring_db.py`）
  - MonitoringEngine / KillSwitch / Alert 管理
  - 起動スクリプト（`run_monitoring.py`）
- portfolio
  - 候補選定（スコア順）、重み計算（等配分・スコア配分）
  - ポジションサイジング（リスクベース、上限・単元調整）
  - セクターキャップ・レジーム乗数適用
- research
  - ファクター計算（momentum / volatility / value）
  - 前方リターン計算、IC（Spearman）など
- ai
  - ニュース NLP（OpenAI）による銘柄別センチメント評価（`score_news`）
  - 市場レジーム判定（`score_regime`）
- tools
  - Paper Trading の検証レポート生成（`tools/paper_verification_report.py`）

---

## セットアップ手順（ローカル開発・運用）

前提: Python 3.10+（typing の union 表記などを利用しています）

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール
   ※requirements.txt が無い場合は下記主要パッケージをインストールしてください。
   ```
   pip install duckdb psutil openai
   # 任意: YAML ファイルの検証に PyYAML を使用
   pip install pyyaml
   ```
   （実運用ではバージョン固定した requirements.txt を用意することを推奨します）

4. 環境変数設定
   - 対話式ウィザードで .env を生成:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは手動で `.env` をプロジェクトルートに作成。`.env.example` を参考にしてください（このリポジトリ内で自動生成スクリプトが用意されています）。

   主な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB の上書き）
   - LOG_LEVEL（DEBUG / INFO / ...）
   - OPENAI_API_KEY（AI機能使用時に必要）

   注意:
   - 自動ロード: `kabusys.config` はプロジェクトルートに `.env` を見つけると自動的に読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
   - `.env` は絶対にコミットしないでください。

5. 設定検証（推奨）
   ```
   python -m kabusys.validate_config        # 警告は無視して OK
   python -m kabusys.validate_config --strict  # 警告があると exit(1)
   ```

---

## 使い方（主要スクリプト例）

- 監視ループを起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は常に「本番 SQLite（Settings.sqlite_path）」を使用します（環境にかかわらず）。

- Execution エンジンを起動（注文実行）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用して `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録します。
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - 実行中は `data/execution.pid` に PID を書きます。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config [--strict]
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール（プログラムから呼ぶ例）
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
  print("written:", written)
  ```

ログ:
- デフォルトは `logs/` ディレクトリに日次ローテートで出力されます（ファイル名はアプリ名: `monitoring.log`, `execution.log` 等）。
- 出力先は環境変数 `LOG_DIR` または `setup_logging(..., log_dir=...)` で変更できます。

停止 / Kill Switch:
- 監視コンポーネントは危険条件を検出すると `data/kill.flag` を書き込み、ExecutionEngine に停止を促します（実際は監視エンジンが `KillSwitch` を使ってフラグを作成）。
- 手動停止は `data/stop_requested.flag` を作成すると各起動スクリプトが検知してループを抜けます。
- 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると kill flag を自動クリアします（本番では `0` 推奨）。

---

## 監視用（Monitoring DB）について

監視用 SQLite（`monitoring_db.py`）は以下のテーブルを持ちます（init は冪等）:

- system_status: cpu/memory/disk/プロセス生存などのポーリングログ
- trade_logs: 発注・約定・送信イベントログ（latency_ms カラムあり）
- positions: 保有ポジション（code を主キー）
- risk_logs: リスク関連イベント（重複検出機能あり）
- dashboard: ダッシュボード集計（id=1 の単一行）

MonitoringDB クラスはこれらの読み書きを抽象化しています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数 / .env 自動ロード
  - config_setup.py                # .env 対話式ウィザード
  - validate_config.py             # 設定検証 CLI
  - run_execution.py               # ExecutionEngine 起動スクリプト
  - run_monitoring.py              # SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  # 紙トレード検証レポート CLI
  - ai/
    - news_nlp.py                   # ニュース NLP（OpenAI）スコアリング
    - regime_detector.py            # 市場レジーム判定（OpenAI併用）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - (その他: execution, data, strategy 等のサブパッケージ)

プロジェクトルート内に `data/`（DB / pid / flag を格納）と `logs/`（ログ）を想定しています。必要に応じて環境変数でパスを変更できます。

---

## 運用上の注意・ベストプラクティス

- .env は機密情報を含むため決して Git にコミットしないこと。
- 本番（KABUSYS_ENV=live）では LINE の通知設定等を必ず確認してください（`validate_config` に警告あり）。
- Kill Switch / stop flag の誤設定に注意。`KILL_FLAG_CLEAR_ON_START=1` は本番では危険です。
- OpenAI API を使用する機能は API キーの漏洩とコストに注意して運用してください。
- DuckDB・SQLite のファイルパスはバックアップ / 権限 / ディスク容量に注意して設定してください。
- 実行時にプロセス優先度を上げる処理を行いますが、OS によっては権限不足で失敗する場合があります（ログに警告が出ます）。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視プロセス起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Execution 起動（ペーパートレード例）
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README に以下を追加できます:
- 依存パッケージの正確なバージョン一覧（requirements.txt）
- デプロイ / systemd / supervisor の Unit サンプル
- CI / テスト実行方法、ユニットテストの書き方例
- 各モジュール（ExecutionEngine, MonitoringEngine 等）の詳細設計図

どの追加情報が必要か教えてください。