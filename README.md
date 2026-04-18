# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README（日本語）

この README はリポジトリ内の主要スクリプト・モジュールに基づいて作成しています。実行方法、設定手順、各コンポーネントの概要をまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのプロジェクトです。主な機能は以下の通りです。

- 注文実行エンジン（ExecutionEngine） — ブローカークライアントと統合して発注を行う
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、本番 DB と分離して `data/paper_trading.db` に記録
- 監視（Monitoring） — システム稼働状況、データ鮮度、注文ログ、リスク（ドローダウン・ポジション上限）を監視し、必要に応じて Kill Switch（停止フラグ）を書き込む
- ポートフォリオ構築（Portfolio） — 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数などの純粋関数群
- リサーチ（Research） — DuckDB 上の価格・財務データからファクター計算、将来リターン、IC、統計サマリー等を実行
- AI モジュール（AI） — ニュースの NLP（OpenAI）によるセンチメント集計、マクロニュースを使った市場レジーム判定
- ユーティリティ — ログ設定、プロセス優先度設定、設定ウィザード、設定検証ツール 等
- ツール — ペーパートレード検証レポート生成スクリプト等

---

## 機能一覧（抜粋）

- 設定ウィザード: `.env` を対話形式で作成・更新（`python -m kabusys.config_setup`）
- 設定検証: `.env` と `config/*.yaml` を起動前にチェック（`python -m kabusys.validate_config`）
- 実行エンジン起動スクリプト: `run_execution.py`（`python -m kabusys.run_execution`）
  - `KABUSYS_ENV=paper_trading` では専用 SQLite に記録し、本番 DB とは分離
- 監視ループ起動スクリプト: `run_monitoring.py`（`python -m kabusys.run_monitoring`）
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を指定可能（デフォルト 60 秒）
- Paper Trading 検証レポート: `python -m kabusys.tools.paper_verification_report`
- AI 関連:
  - `kabusys.ai.news_nlp` — raw_news から銘柄ごとのセンチメントを OpenAI へ送信して `ai_scores` に保存
  - `kabusys.ai.regime_detector` — ETF（例: 1321）の MA200 とマクロセンチメントを合成してレジーム判定
- データベース:
  - DuckDB（分析用）: デフォルト `data/kabusys.duckdb`
  - SQLite（監視 / 発注ログ）: デフォルト `data/monitoring.db`
  - Paper Trading 用 SQLite: デフォルト `data/paper_trading.db`

---

## セットアップ手順

1. Python 環境の用意（推奨: Python 3.10+）
   - 仮想環境を作成してアクティベートしてください。

     bash
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows

2. 依存パッケージのインストール（最低限）
   - 以下のパッケージが動作に必要です（一部はオプション）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（`validate_config` が YAML 検証をする場合に推奨）
   - 例:

     bash
     pip install duckdb psutil openai PyYAML

   - 実際のプロジェクトでは requirements.txt があればそれを使ってください。

3. 初期設定（.env）
   - 対話式ウィザードで `.env` を作成するのが簡単です:

     bash
     python -m kabusys.config_setup

   - ウィザード終了後、設定を検証します:

     bash
     python -m kabusys.validate_config

   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI を使う場合に必要
     - KABUSYS_ENV: 実行環境（development | paper_trading | live）
     - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: DB ファイルパス
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（本番では 0 推奨）

   - 自動 `.env` 読み込みはデフォルトで有効です。無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. ディレクトリ作成（デフォルトで使うフォルダ）
   - `data/`（DB・PID・フラグ等）
   - `logs/`（ログ）
   - 例:

     bash
     mkdir -p data logs

---

## 使い方（主要なコマンド例）

- 設定ウィザード（.env 作成・更新）

  bash
  python -m kabusys.config_setup

- 設定検証

  bash
  python -m kabusys.validate_config
  # --strict を付けると警告もエラー扱いで exit 1
  python -m kabusys.validate_config --strict

- 実行エンジン起動

  bash
  # 本番 / 開発: 環境は .env 内の KABUSYS_ENV
  python -m kabusys.run_execution

  挙動:
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）に記録されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動を中止します。
  - `data/execution.pid` に PID を書きます。

- 監視ループ起動

  bash
  # デフォルト監視間隔 60 秒。MONITOR_POLL_INTERVAL で上書き可能
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring

  挙動:
  - `MONITOR_POLL_INTERVAL` (秒) でポーリング。1 秒未満や 0 は無効。
  - 監視は常に本番の sqlite_path を使用（環境に依存しない）。
  - ループ停止は `data/stop_requested.flag` を作成するか Ctrl+C。

- Paper Trading 検証レポート生成

  bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB パスは data/paper_trading.db。--db で指定可能。

- AI 関連（OpenAI が必要）
  - ニュース NLP（銘柄別スコア付与）:
    - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
    - 実行時は `OPENAI_API_KEY` を設定するか `api_key` を渡してください。
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

---

## 動作上の注意事項 / 運用メモ

- Kill Switch / 停止フラグ:
  - `kabusys.monitoring.kill_switch` は `data/kill.flag` を作成して ExecutionEngine に停止シグナルを送ります。`KILL_FLAG_CLEAR_ON_START=1` にすると起動時に自動クリアしますが、本番では 0 を推奨します。
  - 監視ループ・実行エンジンは `data/stop_requested.flag` の存在を見て安全に終了します。

- DB マイグレーション:
  - `monitoring_db.init_monitoring_db` は複数のテーブルと必要なカラムを冪等的に作成・追加します（既存 DB に対する軽いマイグレーション対応あり）。

- ログ:
  - 共通のログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を使用し、`logs/<app_name>.log` に日次ローテーションで出力します。`LOG_DIR` 環境変数で変更可能。

- プロセス優先度:
  - `kabusys.utils.process_priority.set_process_priority` で OS に依存せず優先度を設定しようとします（失敗時は警告を出してスキップ）。

- Paper Trading:
  - `KABUSYS_ENV=paper_trading` にすると MockBroker が使われ、本番 DB と完全分離されます。デフォルト保存先は `data/paper_trading.db`。

- OpenAI API:
  - AI 機能は OpenAI の API を使用します。`OPENAI_API_KEY` を必ず設定してください。API 呼び出しはリトライ・フェイルセーフ（失敗時はスコアを 0.0 にする等）が実装されていますが、コストやレート制限に注意してください。

---

## 主要なディレクトリ構成

（リポジトリの `src/kabusys` 相当の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数 / .env の読み込みと検証
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定
    - process_priority.py — 優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （発注ログ監視など）※詳細は実装参照
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 制御
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — アラート通知（LINE 等）※詳細は実装参照
  - execution/
    - execution_engine.py — 実行エンジン本体（EngineConfig 等）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py / broker_factory.py
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数決定 / 単元丸め / リスク制限
    - risk_adjustment.py — セクター制限 / レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等の計算（DuckDB ベース）
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py — マクロ＋ETF MA によるレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

---

## サンプル .env（抜粋）

.env は Git 管理に含めないでください（秘密情報が含まれます）。例:

KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=sk-...

---

## よくある運用タスク

- 監視を停止したいとき:
  - `data/stop_requested.flag` を作成すると監視ループや実行エンジンが安全に停止します。
- Kill Switch を強制発動（危険なので注意）:
  - `data/kill.flag` を作成すると ExecutionEngine に停止シグナルが送られます。
- ログの確認:
  - `logs/execution.log`, `logs/monitoring.log` などを確認してください。日次ローテーションされます。

---

## 参考・補足

- validate_config は設定ファイル（`config/*.yaml`）の存在と YAML のパースもチェックしますが、PyYAML がインストールされていない場合は YAML 検証をスキップして警告を出します。
- `monitoring` 系は SQLite に監視ログを記録します。DB スキーマは `monitoring_db.init_monitoring_db` で作成・マイグレーションされます。
- DuckDB は分析用データ格納に使用します。リサーチ処理は DuckDB 接続を受け取り SQL と Python を組み合わせて計算します。

---

もし README に追加したい具体的なコマンド例、CI / デプロイ手順、さらに詳細なディレクトリツリー（ファイルごと）などがあれば教えてください。必要に応じて README を拡張します。