# KabuSys

日本株向け自動売買システムの一部を構成する Python モジュール群です。本リポジトリには、実行エンジン、監視/アラート、ポートフォリオ構築、リサーチ（ファクター計算）、AI ベースのニュース解析などの主要機能が含まれます。

以下はこのコードベースの概要、機能、セットアップ・使い方、ディレクトリ構成の簡潔な README です。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 取引実行（ExecutionEngine）／ペーパートレード対応
- システム・トレード監視（モニタリング）、Kill Switch による自動停止
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算、将来リターン、IC 計算など）
- AI を使ったニュース解析（OpenAI を利用したセンチメント算出）
- 各種ユーティリティ（設定ウィザード、設定検証、ログ設定など）

設計方針としては「可能な限り外部システムに直接触れず、DB 経由でのデータ取得／永続化」「本番とペーパートレードの分離」「ルックアヘッドバイアス対策」「フェイルセーフ動作」を重視しています。

---

## 主な機能一覧

- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` のときは MockBroker を使い専用 SQLite（data/paper_trading.db）に記録。
- 監視（モニタリング）
  - run_monitoring.py: SystemMonitor のポーリングループを起動。システム負荷、データ鮮度、Execution プロセスの生存などを評価。
  - MonitoringEngine: System/Trade/Risk モニタを束ねて定期実行、KillSwitch 評価、AlertManager への通知。
- データ永続化（監視用 SQLite）
  - monitoring_db.py: system_status / trade_logs / positions / risk_logs / dashboard テーブルの初期化・読み書き API。
- リスク監視
  - risk_monitor.py: ドローダウン・ポジション上限の監視、必要に応じてリスクログ記録・Kill Switch トリガー。
- ポートフォリオ構築
  - portfolio/*.py: 候補選定、スコア・等金額重み、ポジションサイズ決定、セクターキャップやレジーム乗数適用。
- リサーチ
  - research/*.py: ファクター計算（Momentum/Volatility/Value 等）、将来リターン、IC、統計サマリーなど（DuckDB による SQL 処理）。
- AI（OpenAI）連携
  - ai/news_nlp.py: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメント（ai_scores）を算出・保存。
  - ai/regime_detector.py: ETF の ma200 とマクロニュースから市場レジーム（bull/neutral/bear）を判定・保存。
- 開発補助ツール
  - config_setup.py: .env を対話式で作成・更新するウィザード。
  - validate_config.py: .env と config/*.yaml の簡易チェック CLI。
  - tools/paper_verification_report.py: ペーパートレードの実績を集計して検証レポート出力。

---

## 前提・依存（例）

必須ライブラリ（少なくとも以下をインストールしてください）:

- Python 3.9+
- duckdb
- psutil
- openai
- （オプション）PyYAML（config ファイル検証で使用）

例:
```bash
pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン／展開する。

2. 仮想環境を作成して依存をインストールする（推奨）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install duckdb psutil openai pyyaml
   ```

3. .env の作成（対話式ウィザード推奨）:
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードで J-Quants トークン、kabuAPI パスワード、KABUSYS_ENV（development/paper_trading/live）などを設定します。

   自動読み込み:
   - パッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # または厳密モード
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ作成（必要に応じて）:
   ```bash
   mkdir -p data logs
   ```
   デフォルト DB / PID ファイル等は `data/` に作成されます（パスは .env で変更可能）。

---

## 環境変数（主要なもの）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite（paper_trading 時の分離 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/...）
- LOG_DIR: ログの出力先ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1, 本番は 0 推奨）

---

## 使い方（実行例）

すべての起動スクリプトはモジュール実行可能です。

- 実行エンジン（ExecutionEngine）を起動:
  - 本番／開発（KABUSYS_ENV を .env で設定）
  ```bash
  python -m kabusys.run_execution
  ```
  - 特記事項:
    - `KABUSYS_ENV=paper_trading` の場合、MockBroker を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に分離して記録します。
    - 起動前に `data/stop_requested.flag` が存在すると起動せずに終了します。
    - 実行中の停止は `data/stop_requested.flag` を作成することで通知します（外部プロセスがフラグを書き込む運用）。

- 監視ループを起動:
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 説明:
    - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（正の整数のみ）。
    - monitoring は環境にかかわらず本番の sqlite_path（SQLITE_PATH）を使用します（監視は常に本番 DB を見る設計）。
    - 停止は `data/stop_requested.flag` の検出で行われます。

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- 設定ウィザード／検証:
  ```bash
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

---

## ファイル・ディレクトリ構成（主要部分）

以下は主要モジュールの階層例（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py          — .env 対話的ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB スキーマ & API
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — 注文ログ監視（滞留注文・異常約定検出）※（実装参照）
    - risk_monitor.py        — ドローダウン/ポジション制限監視
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - kill_switch.py         — kill.flag の管理
    - alert_manager.py       — アラート送信（LINE など）※（実装参照）
  - execution/
    - execution_engine.py    — ExecutionEngine（注文発行セッション制御）※（実装参照）
    - broker_factory.py      — BrokerClient の生成（本番/Mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 発注株数計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — IC/統計/将来リターン
  - ai/
    - news_nlp.py            — ニュースセンチメント算出（OpenAI）
    - regime_detector.py     — 市場レジーム判定（ma200 + マクロニュース）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

注: 上記のうち一部ファイル（order_manager 等）は本 README で全ての実装を網羅しているわけではありません。実装の詳細は各モジュールの docstring を参照してください。

---

## 運用上の注意・補足

- データベースの初期化:
  - run_execution/run_monitoring 実行時に必要なテーブルは初期化（冪等）されます（init_monitoring_db を利用）。
- Kill Switch / Stop フラグ:
  - `data/kill.flag`：実行エンジンに停止を促すためのフラグ（KillSwitch が作成）。
  - `data/stop_requested.flag`：run_* スクリプト自体を安全に停止させるためのフラグ（外部から作成してプロセスを終了させる）。
- ログ:
  - デフォルトは `logs/` にアプリ名ごとの日次ローテーションログが作成されます。`LOG_DIR` で変更可能。
- OpenAI:
  - news_nlp / regime_detector は OpenAI API（gpt-4o-mini 等）へリクエストを送ります。`OPENAI_API_KEY` の設定が必要です。
  - API の失敗時にはフェイルセーフ（スコア 0 とみなす等）で継続する実装です。

---

## 開発・デバッグ向けヒント

- ログレベルを上げる:
  ```bash
  LOG_LEVEL=DEBUG python -m kabusys.run_monitoring
  ```
- .env の自動読み込みを無効化してユニットテストや一時的な変数注入を行う:
  ```bash
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 python -m kabusys.validate_config
  ```
- モジュール単体テストや対話的確認には各パッケージの関数を直接呼び出して DI（DuckDB 接続など）を差し替えると便利です。

---

README は以上です。実行や設定で不明点があれば、どのコマンド／モジュールでつまずいているかを教えてください。必要に応じてサンプル .env テンプレートや起動用 systemd ユニット例なども作成します。