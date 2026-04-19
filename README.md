# KabuSys

日本株向け自動売買システム（ライブラリ & 起動スクリプト群）

このリポジトリは下記機能群を持つ小規模な自動売買フレームワークです。  
監視（Monitoring）、注文実行（Execution）、ポートフォリオ構築、リサーチ（ファクター計算）、AI を使ったニュース評価などをモジュール化しています。

バージョン: 0.1.0

---

## プロジェクト概要

- 自動売買のコアロジック（発注・リスク管理・約定ログ）と、監視/アラート基盤を含む。
- DuckDB / SQLite によるデータ管理（DuckDB: 分析、SQLite: 監視/発注ログ）。
- Paper Trading モードを用意し、本番 DB と完全分離して動作可能。
- OpenAI を利用したニュース NLP（センチメント）やレジーム判定機能を内包。
- 監視コンポーネントは稼働率・データ鮮度・滞留注文・ドローダウンなどを検出し、Kill Switch（フラグファイル）で発注エンジンを停止可能。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine を起動（実発注 / ペーパートレードを切替）
  - run_monitoring: SystemMonitor のポーリングループ起動
- 設定管理
  - .env 自動読み込み（.env, .env.local）と Settings クラス
  - config_setup: .env の対話式ウィザード
  - validate_config: 起動前の設定検証 CLI（--strict オプション有）
- 監視（monitoring）
  - SystemMonitor: CPU/Mem/Disk、プロセス生存、データ鮮度を監視
  - TradeMonitor: 注文ログ / 滞留注文の検出（実装ファイル群あり）
  - RiskMonitor: ドローダウン・ポジション上限の監視・リスクログ記録
  - KillSwitch: リスク条件により kill.flag を書き込み、ExecutionEngine 停止
  - MonitoringDB: SQLite ベースの永続化層（system_status, trade_logs, positions 等）
- Execution（発注関連）
  - BrokerClientFactory（テスト用 MockBroker など切替）
  - ExecutionEngine / OrderManager / Reconciler / RiskManager etc.
  - paper_trading モードでは MockBrokerClient を使用し `data/paper_trading.db` に記録
- ポートフォリオ構築
  - 候補選定、重み計算（等金額・スコア加重）、ポジションサイズ算出、セクター制限、レジーム乗数
- リサーチ
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC 計算、統計サマリ
- AI（OpenAI）
  - ニュースを LLM に送りセンチメントを算出し ai_scores に書き込み（news_nlp）
  - マクロニュース + ETF MA200 乖離から市場レジームを判定（regime_detector）
- ツール
  - paper_verification_report: Paper Trading の検証レポート生成

---

## 前提（依存パッケージ）

（実行環境に合わせてインストールしてください）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能使用時)
- PyYAML（config の内容検証を行う場合、validate_config で推奨。なくても動作はする）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ
2. 仮想環境を作成・有効化し、必要パッケージをインストール
3. 環境変数を用意
   - 推奨: `python -m kabusys.config_setup` を実行して対話式に .env を生成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要なオプション / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - OPENAI_API_KEY（AI 機能を使う場合）
4. 設定検証
```
python -m kabusys.validate_config
# strict モード（警告もエラー扱い）:
python -m kabusys.validate_config --strict
```
5. 必要に応じてデータディレクトリを作成（.env のパス設定に依存）
```
mkdir -p data logs
```
注: monitoring / execution 起動時に DB 初期化（テーブル作成）は自動で行われます。

---

## 使い方（主なコマンド）

- 実行エンジン起動（本番 / ペーパートレード切替は KABUSYS_ENV で決定）
```
# ペーパートレード例
KABUSYS_ENV=paper_trading python -m kabusys.run_execution

# 本番（慎重に）
KABUSYS_ENV=live python -m kabusys.run_execution
```
- 監視ループ起動（ポーリング）
```
# ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- 設定ウィザード（.env 作成/更新）
```
python -m kabusys.config_setup
```
- 設定検証
```
python -m kabusys.validate_config
```
- Paper Trading 検証レポート出力
```
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report \
    --from 2026-04-01 --to 2026-04-11

# 別 DB を指定する例
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

注意点:
- run_execution は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）へ記録し、本番 DB と分離します。
- run_monitoring と run_execution はプロセス優先度を "high" に設定します（プラットフォームに依存し設定できない場合は警告のみ）。
- 停止制御:
  - 管理用の停止フラグ: data/stop_requested.flag（run_monitoring/run_execution はこれを検知してグレースフルに終了します）
  - Kill Switch: KillSwitch は data/kill.flag（デフォルト）を作成して ExecutionEngine に「発注停止」を指示します。KILL_FLAG_CLEAR_ON_START が 1 の場合、自動クリア設定に注意（本番では 0 推奨）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必須
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_DIR: ログ出力先（デフォルト: logs/）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KILL_FLAG_CLEAR_ON_START: 本番環境での自動クリア禁止のため通常 0

.env の自動読み込み:
- OS環境変数 > .env.local > .env の順で読み込まれます。
- 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 実装上の補足 / 運用メモ

- ログ設定:
  - 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を使って stdout と日次ローテーションファイルを設定します（logs/<app_name>.log）。
- DB 初期化:
  - monitoring 用テーブルは起動時に自動作成（init_monitoring_db）。
  - マイグレーション処理（カラム追加）も一部実装されています（冪等処理）。
- Paper Trading:
  - PAPER_FILL_MODE（instant, partial, never, reject）で MockBroker の約定挙動を制御できます。
- OpenAI 呼び出し:
  - LLM 呼び出しはレート制限・ネットワーク断・タイムアウト・5xx を想定したリトライロジックを持ちます。API キーが未設定の場合は例外を投げます。
- 停止フラグ:
  - 運用でプロセスを安全に停止したい場合は data/stop_requested.flag を作成してください（run_* スクリプトは検知して終了します）。
  - KillSwitch（自動停止ロジック）は data/kill.flag を書き込みます。誤って本番でクリアされないよう注意してください。

---

## ディレクトリ構成（主要ファイル）

推定プロジェクトルート（src 配下）:

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / Settings
    - config_setup.py               — .env 対話ウィザード CLI
    - validate_config.py            — 設定検証 CLI
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - run_monitoring.py             — SystemMonitor 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading レポート CLI
    - ai/
      - __init__.py
      - news_nlp.py                 — ニュース NLP（OpenAI）
      - regime_detector.py          — 市場レジーム判定（OpenAI）
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py (想定)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (想定)
    - execution/
      - execution_engine.py (想定)
      - order_manager.py (想定)
      - order_repository.py (想定)
      - broker_factory.py (想定)
      - reconciler.py (想定)
      - risk_manager.py (想定)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - monitoring/ (上に示した)
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/ (実行時に生成/使用される)
      - monitoring.db (default)
      - paper_trading.db (paper_trading)
      - kill.flag
      - stop_requested.flag
    - logs/
      - execution.log, monitoring.log, ... （デフォルト）

※ 上記はリポジトリ内の主要ファイルを抜粋して構成を示しています。

---

## 開発者向けヒント

- 単体関数設計: ポートフォリオ / リサーチ系は副作用がなく純粋関数に近い形で実装されているためユニットテストが書きやすいです。
- DuckDB を使った分析関数は接続オブジェクトを受け取り SQL を実行するスタイルのため、ローカルのテスト DB を用意して検証するとよいです。
- AI を利用する機能は外部 API 依存が強いため、ユニットテスト時は `_call_openai_api` などをモックする設計が既に考慮されています。

---

もし README に追加してほしい内容（例: サンプル .env のテンプレート、詳細な API 使用手順、実際の ExecutionEngine の起動オプションなど）があれば教えてください。必要に応じて補足の章を作成します。