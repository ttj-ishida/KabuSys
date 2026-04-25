# KabuSys

日本株自動売買システムのコードベース（ライブラリ + 起動スクリプト群）の説明書です。  
この README は開発者・運用担当者向けにプロジェクトの概要、機能、セットアップ方法、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な責務は以下の通りです：

- データ取得・分析（DuckDB を想定）
- シグナル生成・ポートフォリオ構築（ポートフォリオ重み・サイズ計算）
- 発注・発注管理（本番・ペーパートレード切替）
- 監視（システム状態、注文状態、リスク監視）と Kill Switch
- 研究用ユーティリティ（ファクター計算・特徴量解析）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- 運用用 CLI ツール（環境セットアップ・設定検証・検証レポート生成など）

設計方針としては、本番発注ロジックと分析／研究ロジックの分離、フェイルセーフ（API失敗時の安全なフォールバック）、およびルックアヘッドバイアス回避を重視しています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動（実際の発注 / paper_trading 切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動
- 環境設定 / 検証
  - config_setup.py: .env 対話式ウィザード（.env の作成・更新）
  - validate_config.py: .env および config/*.yaml の事前検証
- 監視 / リスク管理
  - monitoring/*: SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringDB, MonitoringEngine
  - kill.flag / stop_requested.flag による安全停止機構
- ポートフォリオ構築
  - portfolio/*: 候補選定、重み付け、セクター制約、位置サイズ計算（単位株丸め含む）
- 研究用分析
  - research/*: ファクター計算（モメンタム・ボラティリティ・バリュー）や特徴量探索
- AI（ニュース NLP / レジーム判定）
  - ai/news_nlp.py: OpenAI を用いたニュースセンチメントスコア生成（ai_scores への書込み）
  - ai/regime_detector.py: ETF MA とマクロニュースを組合せたレジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

---

## 必要な依存パッケージ

最低限必要なパッケージ（例）:

- Python 3.10+
- duckdb
- psutil
- openai (AI機能を使う場合)
- pyyaml（config の YAML 検証を行う場合）

インストール例:

```bash
python -m pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt があればそれを利用してください）

---

## 環境変数 / 設定

- 自動ロード: プロジェクトルートにある `.env` / `.env.local` が自動で読み込まれます（OS 環境変数が優先）。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 重要な環境変数（必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- よく使う設定例
  - KABUSYS_ENV: execution コンテキスト。`development` / `paper_trading` / `live`
    - paper_trading: MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH, default: data/paper_trading.db）に記録します。
  - DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
  - LOG_LEVEL, LOG_DIR
  - OPENAI_API_KEY: OpenAI を使用する AI モジュールで必要

推奨: `python -m kabusys.config_setup` を実行して .env を作成してください（対話式）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンしワークディレクトリへ移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - python -m pip install --upgrade pip
   - python -m pip install duckdb psutil openai pyyaml
4. .env を作成
   - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
5. 設定検証
   - python -m kabusys.validate_config
   - 本番用に `--strict` を付けると警告も失敗扱いになります

---

## 使い方（主要コマンド）

- 実行エンジン（ExecutionEngine）を起動
  - デフォルト: 環境に応じて本番 DB / paper_trading DB を分離
  - 実行例:
    - 本番（デフォルト）:
      - python -m kabusys.run_execution
    - ペーパートレード:
      - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止: プロセス内で `data/stop_requested.flag` が見つかると優雅に停止します。
  - 実行時に PID は data/execution.pid に書き込まれます（設定で変更可能）。

- 監視（SystemMonitor）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト60）で上書き可能
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番用の sqlite_path を使用します（環境に関係なく監視 DB は production path を使う設計）。
  - 監視ループの停止は `data/stop_requested.flag` を作成することで行います。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可能

- AI 機能（プログラム呼出し）
  - ニュース NLP スコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key 引数 or OPENAI_API_KEY 環境変数
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

注意: AI 関連は OpenAI API キーが必要です。API 呼び出しは冪等や失敗時の安全側フォールバックが組み込まれていますが、API 制限・料金に注意してください。

---

## 停止 / Kill Switch / フラグファイル

- stop_requested.flag
  - run_execution / run_monitoring のポーリングループが見ている停止用フラグ（data/stop_requested.flag）。
  - このファイルが存在するとループは終了します（再起動時に削除してください）。

- kill.flag
  - KillSwitch が条件を満たした場合に書き込まれる（ExecutionEngine に対して停止シグナル）。
  - 設定 `KILL_FLAG_CLEAR_ON_START=1` にすると起動時に自動でクリアする挙動になります（本番ではデフォルト 0 推奨）。

- PID ファイル
  - 実行エンジンは実行中の PID を `data/execution.pid`（デフォルト）へ書き込みます（Settings.pid_file_path で変更可）。

---

## ログ

- ログは root ロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次、デフォルト logs/以下）を設定します。
- ログレベルは `LOG_LEVEL`、ログディレクトリは `LOG_DIR`（デフォルト: logs/）で制御できます。
- `kabusys.utils.logging_setup.setup_logging(app_name="execution")` の呼び出しにより各サブシステムのログファイルは `logs/execution.log` のように出力されます。

---

## ディレクトリ構成（主要ファイル/モジュール）

src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings 管理（.env 自動ロード含む）
- config_setup.py — .env 対話ウィザード
- validate_config.py — 起動前の設定検証 CLI

- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- ai/
  - news_nlp.py — ニュースの NLP スコアリング（OpenAI）
  - regime_detector.py — レジーム判定（MA + マクロニュース）
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム状態 / データ鮮度監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - trade_monitor.py —（注文滞留/約定異常の検出）※コードベースの他ファイルに実装あり
  - kill_switch.py — Kill Switch ロジック
  - monitoring_engine.py — 監視コンポジットエンジン
  - alert_manager.py —（通知ラッパー。LINE 等と接続する実装が想定される）
- execution/  — 発注エンジン関連（BrokerClientFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等）
- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 発注株数決定（単元株丸め・リスク調整）
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

プロジェクトルート（想定）
- .env, .env.local, .env.example
- data/ (DBファイルやフラグファイル、pid ファイル)
- logs/（ログファイル）
- config/（yaml 設定ファイル群: system_config.yaml 等）
- src/（上記パッケージ）

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では .env を慎重に管理し、`.env` は決して Git にコミットしないこと。
- `KILL_FLAG_CLEAR_ON_START=1` を本番で有効にしない（自動クリアは危険）。
- AI 機能は OpenAI API を呼ぶため、API キー管理とコスト制御に注意すること。
- DB ファイル（DuckDB / SQLite）は運用上のバックアップを検討すること。
- ログディレクトリのパーミッション・ディスク容量の監視を行ってください（ログ肥大化の可能性）。
- `MONITOR_POLL_INTERVAL` で監視間隔を調整可能（デフォルト 60 秒）。短くしすぎると負荷増。

---

## 開発・拡張のヒント

- 研究用関数群（research/*）は DuckDB 接続を受け取り純粋関数で結果を返す設計なので、ローカルの DuckDB を使えば簡単に検証できます。
- BrokerClientFactory を拡張すれば新しいブローカー実装を追加できます（本番 / ペーパーの切替は Settings.is_paper を参照）。
- logging_setup はアプリ名を渡すだけで一貫したログ運用が可能です。テスト時はログレベルを DEBUG に切り替えるとよいです。

---

この README はコードベースの主要な使い方・構成をまとめたものです。追加で「詳しい ExecutionEngine の挙動」「TradeMonitor の実装」「AlertManager の使い方」など特定ファイルのドキュメントが必要であれば指示してください。