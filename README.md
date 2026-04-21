# KabuSys

日本株向け自動売買システムのコードベース説明書（README）。  
この README はリポジトリ内の主要スクリプト・モジュールに基づき、日本語で利用方法・セットアップ手順・ディレクトリ構成をまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買向けの統合フレームワークです。主な役割は以下の通りです。

- データ取り込み／分析（DuckDB を利用）
- ファクター計算・研究（research モジュール）
- ポートフォリオ構築（portfolio モジュール）
- 発注ロジックと ExecutionEngine（execution モジュール）
- 監視・アラート（monitoring モジュール）
- AI（ニュース NLP / レジーム判定）連携（OpenAI）
- ペーパートレード用の分離DBを使った検証・レポート生成（tools）

設計方針として、実運用における安全性（ペーパートレードと本番の分離、Kill Switch、監視ログの永続化など）を重視しています。

---

## 主な機能一覧

- 環境設定ウィザード（`.env` 自動作成支援）: `kabusys.config_setup`
- 設定検証 CLI（環境変数・config/*.yaml の検証）: `kabusys.validate_config`
- ExecutionEngine 起動スクリプト: `kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、paper_trading 用 DB に記録
  - 起動時にプロセス優先度を high に設定
  - 停止フラグ（data/stop_requested.flag）で安全に停止
- Monitoring 起動スクリプト: `kabusys.run_monitoring`
  - システム・発注・リスクの定期チェックを実行（デフォルト60秒）
  - 監視ログは SQLite（monitoring.db）に永続化（monitoring_db）
  - Kill Switch（条件を満たすと data/kill.flag に書き込み）で ExecutionEngine を停止可能
- 監視用 DB 層（SQLite、冪等 SQL 実行でスキーマ自動作成）
  - テーブル: system_status, trade_logs, positions, risk_logs, dashboard
- ポートフォリオ構築ユーティリティ（純粋関数群）
  - 候補選定、重み計算（等分・スコア加重）、位置サイズ計算、セクターキャップ、レジーム乗数
- リサーチ機能（DuckDB を用いたファクター計算／IC 計算）
- AI モジュール
  - ニュース NLP に基づく銘柄ごとのセンチメントスコア（OpenAI）
  - レジーム判定（MA200 + マクロセンチメントの合成）
  - OpenAI API 呼び出しはリトライ・パースチェックを備える
- ツール
  - Paper Trading 検証レポート生成（期間指定可）: `kabusys.tools.paper_verification_report`

---

## セットアップ手順

前提
- Python 3.10 以上（コードは `X | Y` などの型ヒントを使用）
- SQLite（組み込み）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を利用する場合）

例: 仮想環境を作成して必要パッケージをインストールする
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil openai pyyaml
```

1. リポジトリをクローンして作業ディレクトリへ移動
2. `.env` を作成
   - 対話式ウィザードを使う（推奨）
     ```bash
     python -m kabusys.config_setup
     ```
   - 必須: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`
   - OpenAI 機能を使う場合は `OPENAI_API_KEY` を設定
   - 主要な環境変数（デフォルト値は .env.example 等を参照）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL, LOG_DIR, PID_FILE_PATH, KILL_FLAG_PATH
3. 設定検証（起動前に推奨）
```bash
python -m kabusys.validate_config
# 警告も失敗扱いにする場合:
python -m kabusys.validate_config --strict
```
4. 必要に応じてデータディレクトリを作成（.env のパス先がなければログや DB の作成時に自動生成されます）

注意:
- 自動で `.env` を読み込む仕組みがあり、プロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を読みます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方

基本的な起動・運用コマンドの例。

- ExecutionEngine（発注エンジン）を起動する
  - 本番・ペーパートレードは `.env` の `KABUSYS_ENV` に依存（paper_trading 時は別 DB を使用）
  ```bash
  python -m kabusys.run_execution
  ```
  - 実行中は `data/execution.pid` が作成されます。停止は `data/stop_requested.flag` を作るか、ExecutionEngine 自体が kill.flag を検出して停止します。

- Monitoring を起動する
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - Monitoring は常に本番用の sqlite_path（`SQLITE_PATH`）を利用して監視ログを記録します（環境に依らず）。

- Paper Trading 検証レポートを生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

ログ:
- ログはデフォルト `logs/` ディレクトリに出力され、日次ローテーション（30日保持）されます。ログファイル名はアプリ名 (`execution.log`, `monitoring.log` など)。

Kill / Stop フラグ:
- `data/kill.flag` — Kill Switch が発動した際に書き込まれる（ExecutionEngine を停止するトリガー）。
- `data/stop_requested.flag` — 手動で作成すると run_monitoring / run_execution のポーリングループが検知して安全に終了します。
- Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

AI 機能:
- OpenAI を使う機能（ニューススコア、レジーム検出）を使うには `OPENAI_API_KEY` の設定が必要です。
- API 呼び出しではリトライ・応答バリデーションを実装済みです。

プログラム API:
- 多くの機能は import してプログラムから利用可能です（例: `from kabusys.ai import score_news`、`from kabusys.portfolio import calc_position_sizes` など）。

---

## 主要ファイル／モジュール説明（抜粋）

- src/kabusys/config.py
  - 環境変数読み込み・Settings クラス。自動で .env を読み込みます。
- src/kabusys/config_setup.py
  - 対話式 .env ウィザード
- src/kabusys/validate_config.py
  - 設定チェック CLI
- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（プロセス優先度設定・DB 接続・スレッド実行・停止フラグ対応）
- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
- src/kabusys/monitoring/*
  - Monitoring 関連（監視 DB、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、AlertManager 等）
  - monitoring_db.py: SQLite スキーマ作成 / 永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
- src/kabusys/portfolio/*
  - ポートフォリオ構築の純粋関数群（候補選定、重み付け、位置サイズ計算、セクター制限、レジーム乗数）
- src/kabusys/research/*
  - ファクター計算・特徴量探索・IC など（DuckDB を利用）
- src/kabusys/ai/*
  - ニュース NLP（news_nlp.py）・レジーム判定（regime_detector.py） — OpenAI を利用
- src/kabusys/tools/paper_verification_report.py
  - ペーパートレード検証レポート出力ツール

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要ディレクトリ／ファイル構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - execution/             # ExecutionEngine 周り（broker, order_manager, risk_manager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - (その他: data/, config/ YAML 等)

プロジェクトルートに存在する想定ファイル・ディレクトリ:
- .env, .env.local
- config/ (system_config.yaml などのテンプレート)
- data/（SQLite, pid, flag 等を格納）
  - data/monitoring.db (デフォルト)
  - data/paper_trading.db (paper_trading 用)
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag
- logs/（ログ出力先）

---

## 注意事項 / 運用上のポイント

- 本番環境では `KABUSYS_ENV=live` を設定してください。validate_config は live の場合に追加警告を行います（LINE 通知設定など）。
- Paper trading は DB を完全に分離しているため、本番データや発注 API に影響を与えません（`KABUSYS_ENV=paper_trading`）。
- 監視（monitoring）は環境にかかわらず本番用の `SQLITE_PATH` を参照する実装箇所があるため、監視ログの取り扱いに注意してください（run_monitoring は常に `settings.sqlite_path` を使用）。
- ログは stdout とファイルの両方に出力されます。ログディレクトリのパーミッションに注意してください。
- Stop / Kill フラグはファイルベースでシンプルに実装されています。運用時は flag ファイルの作成・削除を適切に扱ってください。
- OpenAI の利用は API 料金が発生します。API キーは `.env` に保存せず運用の最適化（Secrets 管理）を検討してください。

---

## 参考コマンドまとめ

- .env 作成ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```
- Execution 起動:
  ```bash
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、この README をベースにより詳しいインストール手順（requirements.txt や systemd ユニット定義、Dockerfile、CI 設定例など）を追加できます。どの情報を優先して追加しますか？