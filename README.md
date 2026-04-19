# KabuSys

日本株自動売買システムの Python コードベース。戦略・ポートフォリオ構築、実行エンジン、監視、リサーチ、AI（ニュースセンチメント）等のコンポーネントを含みます。

注意: この README はリポジトリ内のソースコードを基に作成した概要です。運用前に必ず `python -m kabusys.validate_config` で設定を検証してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。主要な責務は以下の通りです。

- ExecutionEngine: 注文生成・ブローカー接続・リスク管理を行う実行コンポーネント（`run_execution.py`）。
- Monitoring: システム稼働・注文状況・リスク監視を行い、必要時に Kill Switch（停止フラグ）を発動する（`run_monitoring.py`、`monitoring/*`）。
- Portfolio/Strategy: シグナルを基に候補選定、配分、株数決定を行う純関数群（`portfolio/*`）。
- Research: DuckDB 上の歴史データからファクター計算や特徴量探索を行う（`research/*`）。
- AI: ニュースを LLM（OpenAI）でスコアリングして市場レジーム判定やニュースセンチメントを生成（`ai/*`）。
- Utilities: ロギング・プロセス優先度設定・設定読み込み等の共通ユーティリティ（`utils/*`）。
- CLI ツール: .env 作成ウィザードや設定検証、ペーパートレード検証レポート生成など（`config_setup.py`, `validate_config.py`, `tools/*`）。

---

## 機能一覧

- 環境設定
  - `.env` の対話式ウィザード（`python -m kabusys.config_setup`）
  - 起動前の設定検証（`python -m kabusys.validate_config`）

- 実行エンジン
  - 本番 / ペーパートレード切替（`KABUSYS_ENV`）
  - ブローカークライアントの抽象化（`BrokerClientFactory`）
  - リスク管理（ポジション上限、ドローダウン等）

- 監視
  - システムリソース（CPU/MEM/DISK）監視
  - データ鮮度チェック（DuckDB の株価日付等）
  - 注文の滞留・約定異常検出
  - Kill Switch（`data/kill.flag`）の発動・評価
  - 監視ログの永続化（SQLite）

- リサーチ / ポートフォリオ構築
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 候補選定、等重・スコア加重、リスクベース株数計算
  - セクター集中制限・レジーム乗数適用

- AI 機能
  - ニュースの銘柄別センチメントスコアリング（OpenAI）
  - 市場レジーム判定（MA200 とマクロニュースの合成）

- ツール
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）

---

## セットアップ手順

1. Python 環境準備（推奨: venv）
   - python 3.10+ を推奨
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要パッケージをインストール
   - 主な依存ライブラリ（最低限）:
     - duckdb
     - psutil
     - openai
     - sqlite3 は標準ライブラリに含まれます
     - （任意）PyYAML（`validate_config` の YAML 検証用）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. プロジェクトルートに `.env` を用意
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - 手動で作成する場合はリポジトリに含まれる `.env.example` を参照してください（無ければ README の「重要な環境変数」を参照）。

4. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば指示に従って `.env` や `config/*.yaml` を修正してください。
   - `--strict` を付けると警告も失敗扱いになります。

5. データディレクトリ・ログディレクトリの作成（必要に応じて）
   - デフォルトの DB / PID / フラグは `data/` 以下に作成されます。
   - ログ: `logs/`

---

## 重要な環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- データベース / ファイルパス
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: デフォルト data/paper_trading.db（paper_trading 環境用）
  - PID_FILE_PATH: デフォルト data/execution.pid
  - KILL_FLAG_PATH: デフォルト data/kill.flag

- ロギング
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
  - LOG_DIR: ログディレクトリ（デフォルト logs/）

- AI
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合に必須）

- モニタリング専用
  - MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）

- ペーパートレード挙動
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト "instant"）

- Kill Switch 動作
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" または "0"、本番では 0 推奨）

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env を対話作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に書き込む
    - 起動時に data/stop_requested.flag があれば起動をスキップ
    - 実行中に stop フラグ（stop_requested.flag）を置くとエンジンが停止します

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
    - 監視は常に本番用 sqlite_path を使用（環境にかかわらず）
    - 停止フラグ: プロジェクトの data/stop_requested.flag を作成するとループが終了

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD（開始日）
    - --to YYYY-MM-DD（終了日）
    - --db PATH（DB パスを直接指定）

- AI 機能（プログラム的に呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 監視・停止フラグの運用

- Kill Switch（Execution 停止）:
  - `KillSwitch` は `data/kill.flag` を書き込むことで ExecutionEngine に停止を促します（実行エンジンは起動時とループで kill.flag を確認します）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動でクリアしますが、本番では推奨されません。

- 外部による即時停止（開発用）
  - `data/stop_requested.flag` を作成すると、`run_execution.py` / `run_monitoring.py` のループが終了します（主にローカルデバッグ用）。

---

## データベース（監視用 SQLite）構造（概略）

init_monitoring_db により作成される主なテーブル:

- system_status: CPU/MEM/DISK/プロセス生存などの時系列
- trade_logs: 発注イベントログ（Created / Sent / Filled 等）
- positions: 保有ポジション
- risk_logs: リスク系イベントログ
- dashboard: ダッシュボード集計（id=1 の単一行で保持）

monitoring モジュールはこれらのテーブルを読み書きします。

---

## 開発者向けディレクトリ構成（主要部分）

プロジェクトルート（`src/kabusys` をトップパッケージとする想定）:

- kabusys/
  - __init__.py
  - config.py                      -- 環境変数/設定読み込みロジック
  - config_setup.py                -- .env 対話ウィザード
  - validate_config.py             -- 設定検証 CLI
  - run_execution.py               -- ExecutionEngine 起動スクリプト
  - run_monitoring.py              -- SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                      -- 実行エンジン関連（BrokerFactory, Engine 等）
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

（上記は実際のファイルツリーの要約です。細かなファイルはリポジトリを参照してください。）

---

## 実運用時の注意点

- 本番環境（KABUSYS_ENV=live）では必須環境変数・通知（LINE）などを必ず設定してください。`validate_config` によるチェックを必ず通すこと。
- OpenAI を利用する機能は API 呼び出しにコストとレイテンシが発生します。API キーの管理と呼び出し頻度制御に注意してください。
- データベース（DuckDB/SQLite）は十分なバックアップ・権限設定を行ってください。
- Kill Switch / stop フラグの運用ポリシーを事前に定め、本番での誤発動を防いでください。
- ログは `logs/<app_name>.log` に日次ローテーションで出力されます。ディスク容量に注意。

---

## サンプルワークフロー（ローカルで確認する最短手順）

1. 仮想環境作成・依存インストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で検証
4. python -m kabusys.run_monitoring を別ターミナルで起動（監視開始）
5. python -m kabusys.run_execution を起動（paper_trading/開発モードで動作確認）
6. 発生したログや `data/monitoring.db` を参照して挙動を確認

---

必要に応じて README を拡張して、環境変数のサンプル `.env.example`、ユニットテスト/CI 実行方法、デプロイ手順（systemd / Docker / supervisor 等）などを追加できます。どの情報を優先して追加したいか教えてください。