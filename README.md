# KabuSys

日本株向け自動売買システムのライブラリ／実行スクリプト群です。本リポジトリは売買ロジック、ポートフォリオ構築、監視、AI を使ったニュース評価などのモジュールを収録しています。

以下はこのコードベースの README（日本語）です。

目次
- プロジェクト概要
- 主な機能一覧
- 要求環境 / 依存
- セットアップ手順
- 使い方（コマンド例）
- 環境変数（主要）
- 停止 / Kill Switch の運用
- ディレクトリ構成（主要ファイル）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム群です。戦略（リサーチ）、ポートフォリオ構築、発注エンジン、監視機能、AI（ニュース NLP／レジーム判定）などをモジュール化して備えています。ローカル開発 / ペーパートレード / 本番（live）を環境切替で扱えるよう設計されています。

主な設計方針：
- モジュールは可能な限り純粋関数・副作用の少ない実装を志向
- DBは SQLite（監視・ペーパートレード）と DuckDB（分析）を併用
- 外部 API（kabuステーション、J-Quants、OpenAI）は設定により切替・分離
- 監視・Kill Switch 機能で本番リスクを低減

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて実ブローカー／MockBroker を切替
  - Paper trading 用 DB (data/paper_trading.db) を使用して発注を完全分離
  - プロセス優先度設定、PID ファイル管理、停止フラグ対応

- Monitoring / MonitoringEngine（run_monitoring.py 等）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねるポーリング監視
  - SQLite ベースの監視ログ（system_status, trade_logs, risk_logs, positions, dashboard）
  - KillSwitch によるフラグファイル書き込み（停止指示）
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、重み計算（等配分・スコア加重）、ポジションサイズ計算
  - セクター集中制限やレジーム乗数の適用

- リサーチ（kabusys.research）
  - Momentum / Volatility / Value ファクター算出（DuckDB による SQL+Python）
  - 将来リターン・IC（Spearman）・ファクター統計

- AI モジュール（kabusys.ai）
  - news_nlp: OpenAI を用いたニュースセンチメント集約・ai_scores への書込
  - regime_detector: ma200 とマクロニュースの LLM 評価を合成して日次レジーム判定

- ユーティリティ
  - 設定ウィザード（config_setup.py）で .env を対話的に作成
  - validate_config.py で起動前チェック（必須環境変数、ファイル存在、YAML 構文など）
  - ロギング設定ユーティリティ、プロセス優先度設定ユーティリティ

- ツール
  - paper_verification_report: ペーパートレード DB を集計し検証レポートを標準出力へ出力

---

## 要求環境 / 依存

- Python 3.10 以上（typing の新構文を使用）
- 必須ライブラリ（起動する機能により変動）
  - duckdb
  - psutil
  - openai （AI 機能利用時）
  - PyYAML（validate_config の YAML 検証を有効にする場合）
- 標準ライブラリ：sqlite3, logging, threading, datetime など

インストール例（仮）:
```
python -m pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. レポジトリをクローン／配置
2. Python 仮想環境を作成・有効化
3. 依存ライブラリをインストール（上記参照）
4. .env を作成
   - 対話式ウィザードで作る:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env.example を参考に手動作成
   - 自動ロードはデフォルトで有効（プロジェクトルートに .env / .env.local がある場合、自動で読み込まれます）
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. 設定の検証（任意）:
```
python -m kabusys.validate_config
# 警告も FAIL 扱いにする場合:
python -m kabusys.validate_config --strict
```

6. 必要な DB ファイル（data ディレクトリなど）の作成は多くが自動で行われますが、`logs/` や `data/` のパーミッションに注意してください。

---

## 使い方（実行例）

- ExecutionEngine を起動（通常はサービス起動方法で利用）:
```
python -m kabusys.run_execution
```
- Monitoring を起動:
```
python -m kabusys.run_monitoring
```
（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で上書き可能。例: `export MONITOR_POLL_INTERVAL=30`）

- 設定ウィザード:
```
python -m kabusys.config_setup
```

- 設定検証:
```
python -m kabusys.validate_config
```

- Paper trading 検証レポート生成:
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# デフォルト DB: data/paper_trading.db。別 DB を指定する場合:
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- AI 機能（ニュース NLP / レジーム判定）を実行する際は OpenAI API キーが必要:
```
export OPENAI_API_KEY="sk-..."
# プログラム内 API 呼び出しで引数経由でも可
```

注意:
- KABUSYS_ENV=paper_trading の場合、発注は MockBroker を使いペーパートレード用 DB（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリは環境変数 LOG_DIR で上書き可能。

---

## 主要な環境変数

必須（起動前に設定が必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API（必要な場合）
- KABU_API_PASSWORD — kabuステーション API のパスワード

一般（デフォルトあり／任意）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring) パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEFAULT: INFO）
- LOG_DIR — ログディレクトリ（DEFAULT: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で使用）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動でクリアするか（0/1）

設定ファイルの自動読み込み:
- プロジェクトルートにある .env / .env.local は自動で読み込まれます（OS 環境変数が優先）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

---

## 停止 / Kill Switch / フラグ

- Execution 停止フロー
  - 監視（MonitoringEngine）側や運用者が KillSwitch を評価して必要なら data/kill.flag を書き込みます。ExecutionEngine は起動時に KillFlag を確認し、存在する場合は起動しません。
  - 実行中に kill.flag が書かれると ExecutionEngine は停止動作を行います（run_execution のループで監視）。
  - 停止フラグをプロジェクトルートで検知するためのファイル:
    - data/stop_requested.flag — run_monitoring / run_execution が停止フラグの検知に使用
    - data/kill.flag — KillSwitch が書き込む（Execution を停止させる）
    - data/execution.pid — ExecutionEngine の PID 管理に使用（run_execution）

- KillFlag の自動クリアに関して:
  - KILL_FLAG_CLEAR_ON_START=1 に設定すると Execution 起動時に kill.flag を自動クリアします（開発用。production では 0 推奨）。

---

## ディレクトリ構成（主要）

以下はリポジトリ内の主要ファイル／モジュールの抜粋です（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定読み込みロジック
  - config_setup.py              — 対話式 .env ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py           — ロギング初期化ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（テーブル作成・書込み API）
    - system_monitor.py          — システム状態監視
    - trade_monitor.py           — （注文関連監視; 省略したが存在）
    - risk_monitor.py            — ドローダウン / ポジション上限監視
    - kill_switch.py             — kill.flag 書込みユーティリティ
    - monitoring_engine.py       — 各 Monitor を束ねるエンジン
    - alert_manager.py           — （アラート送信管理; 実装に依存）
  - execution/
    - execution_engine.py        — ExecutionEngine 本体（起動・停止）
    - broker_factory.py          — ブローカクライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み付け
    - position_sizing.py         — 株数算出、資金配分ロジック
    - risk_adjustment.py         — セクター制限・レジーム乗数
  - research/
    - factor_research.py         — Momentum/Volatility/Value ファクター計算
    - feature_exploration.py     — 将来リターン、IC、統計サマリ
  - data/
    - （スクリプト外のデータ / DB 等を配置する想定）
  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py         — レジーム判定（MA + マクロニュース）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

注: 一部ファイルは省略/略記しています。詳細は各モジュールの docstring を参照してください。

---

## 運用上の注意点

- 本番運用（KABUSYS_ENV=live）では環境変数や LINE 通知設定を十分に検証してください（validate_config で警告が出ます）。
- AI（OpenAI）呼び出しは API 料金とレイテンシを伴います。API キーの管理に注意し、必要ならレート制御やバッチ化設定を確認してください。
- DuckDB／SQLite のパスやログディレクトリは環境に合わせて設定してください。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- run_monitoring / run_execution はプロセス優先度を "high" に設定しようとしますが、権限不足等で設定できない場合は警告が出ます（処理は継続します）。

---

必要であれば、README を運用手順（systemd サービス設定例、Dockerfile、CI 用のコマンド等）や各コンポーネントの図（フロー図）付きで拡張できます。どの部分を詳しく追記するか教えてください。