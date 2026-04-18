# KabuSys

日本株向け自動売買システム（ライブラリ + 起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・ポジションサイジング・注文実行（本番／ペーパートレード）・監視・AI（ニュースのセンチメント／レジーム判定）・レポート生成などを含む自動売買基盤の実装群です。

---

## 概要

- Python パッケージ `kabusys` として各種モジュールを提供します。
- 実行系（ExecutionEngine）と監視系（MonitoringEngine）は独立したプロセスとして起動して運用します。
- 設定は環境変数（`.env`）で管理。対話式ウィザードや事前検証ツールを備えています。
- Paper Trading（ペーパートレード）用に本番 DB と完全分離された SQLite を利用できます。
- DuckDB を分析用途（ファクター計算、ニュース集約等）に使用します。
- OpenAI API を利用したニュース NLP / レジーム判定機能を備えています（APIキー必須）。

---

## 主な機能一覧

- 設定管理
  - `.env` 自動ロード（プロジェクトルートの `.env` / `.env.local`）
  - `kabusys.config_setup` による対話式設定ウィザード
  - `kabusys.validate_config` による起動前設定チェック

- 実行（Execution）
  - `run_execution.py`：ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=`paper_trading` では MockBrokerClient を使用し `data/paper_trading.db` に記録（本番 DB と分離）
  - プロセス優先度設定 / PID ファイル管理 / stop フラグ検知

- 監視（Monitoring）
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプト
  - System / Trade / Risk モニタ、Kill Switch、AlertManager の組合せで自動検出・通知（監視 DB: SQLite）
  - `MONITOR_POLL_INTERVAL` 環境変数で間隔上書き可能（デフォルト 60 秒）
  - 監視用 SQLite の自動初期化（テーブル作成・簡易マイグレーション）

- 研究・ファクター計算
  - `kabusys.research`：モメンタム / ボラティリティ / バリュー等のファクター計算
  - DuckDB を使った SQL ベースの実装で高速集計

- ポートフォリオ構築
  - 候補選定、等配分／スコア配分、リスクに基づく株数計算、セクター上限等の純粋関数（副作用なし）

- AI（OpenAI）
  - `kabusys.ai.news_nlp`：ニュースを LLM でスコアリング → `ai_scores` に書込
  - `kabusys.ai.regime_detector`：ETF の MA とマクロニュース LLM を合成して日次レジーム判定

- ツール
  - `kabusys.tools.paper_verification_report`：ペーパートレード検証レポート生成（稼働率 / 成功率 / レイテンシ 等を評価）

- ユーティリティ
  - ロギング設定（コンソール + 日次ファイルローテーション）
  - プロセス優先度 / CPU affinity 設定
  - 監視 DB 永続層（MonitoringDB）

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（型記法で `X | Y` を使用）
- システムに `sqlite3`（標準）、`duckdb`、`psutil` 等が必要

1. リポジトリをクローン・チェックアウト
   - プロジェクトルートには `src/`、`config/`、`.env.example`（任意）等を置きます。

2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最小（本番で必要なもの）:
     - duckdb
     - psutil
     - openai  (AI 機能を使う場合)
     - PyYAML (config YAML の検証を行う場合に推奨)
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれに従ってください）

4. 環境変数設定（`.env` ファイル作成）
   - 対話式で作る: `python -m kabusys.config_setup`
   - もしくは `.env` を手動で作成（`.env.example` を参照）
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、例: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
     - LOG_LEVEL（DEBUG/INFO/...）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - MONITOR_POLL_INTERVAL（監視の間隔秒数；デフォルト 60）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動削除するか。開発用に 1 が使われる）

   自動ロード:
   - パッケージは起動時にプロジェクトルートの `.env` および `.env.local` を自動ロードします（OS 環境変数を上書きするのは `.env.local` のみ）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. ディレクトリの準備
   - `data/`（DB・PID・フラグファイル保管）と `logs/`（ログ）を用意（多くの起動処理で自動作成しますが権限等に注意）。

---

## 使い方（主要コマンド）

- 設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL とする）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 振る舞い:
    - 起動時に環境変数 `KABUSYS_ENV` を参照
    - `paper_trading` の場合は専用の Paper DB（`PAPER_TRADING_SQLITE_PATH`）を使用し、MockBrokerClient を利用
    - 停止は `data/stop_requested.flag` を作成すると検知して終了
    - 実行中は `data/execution.pid` に PID を書き込み

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 振る舞い:
    - 監視用 SQLite（`SQLITE_PATH`）を使って SystemMonitor のポーリングを実行
    - 環境変数 `MONITOR_POLL_INTERVAL` によってポーリング間隔を秒で上書き可能（デフォルト 60）
    - 監視は本番 sqlite_path を利用（KABUSYS_ENV に依らず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI スコア / レジーム判定は各 API を呼び出す関数として利用可能
  - 例: `kabusys.ai.score_news` / `kabusys.ai.regime_detector.score_regime` を Python コードから直接呼ぶ際は `OPENAI_API_KEY` を環境変数か引数で渡してください。

---

## 停止・Kill スイッチ挙動

- 監視プロセス（run_monitoring）はプロジェクトルート下の `data/stop_requested.flag` の存在を監視し、存在する場合にループを終了します。
- ExecutionEngine 側の停止シグナルは `KillSwitch` によって `data/kill.flag` を書き込むことで行われます。KillSwitch はリスク（ドローダウン超過、ポジション上限超過など）を検出した場合にフラグを書き込みます。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると ExecutionEngine 起動時に既存の `kill.flag` をクリアします（本番では `0` を推奨）。

---

## ログ

- ログは `kabusys.utils.logging_setup.setup_logging` により統一的に設定されます。
- 出力先:
  - コンソール（stdout）
  - 日次ローテートされたファイル: `logs/<app_name>.log`（デフォルト）
- ログディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/` を使用します。

---

## 主要ディレクトリ構成（抜粋）

プロジェクトルート想定:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/                (注文実行関連: Engine, OrderManager, BrokerFactory 等)
    - monitoring/
      - monitoring_db.py
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
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/
  - monitoring.db (default)
  - paper_trading.db (paper trading)
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/
  - execution.log
  - monitoring.log
  - ...

（上記は主要ファイルの一例です。実際のリポジトリ構成はツリーを参照してください）

---

## 監視 DB（SQLite）について

- テーブル（自動作成 / マイグレーション対応）
  - system_status: CPU/メモリ/ディスク/プロセス状態の時系列
  - trade_logs: 発注イベントログ（event_type: Created/Sent/Filled 等、latency_ms カラムあり）
  - positions: 現在ポジション（qty, avg_price, current_price）
  - risk_logs: リスクイベントログ（DRAWDOWN_ALERT 等）
  - dashboard: ダッシュボード集計（id=1 の単一行を保持）

- 初回起動時に `init_monitoring_db` が呼ばれてテーブルを作成、既存 DB に対する軽微なマイグレーションもサポートします。

---

## 依存関係（代表）

- duckdb
- psutil
- openai
- PyYAML（任意、validate_config の YAML 検証で利用）
- sqlite3（標準ライブラリ）

必要に応じて requirements.txt を用意して pip install を行ってください。

---

## 開発時メモ / 注意点

- KABUSYS_ENV が `live` の場合は本番動作になります。`validate_config` は `live` 時に追加の注意喚起を行います。設定とアクセスキーの取り扱いに注意してください。
- `.env` は絶対にリポジトリにコミットしないでください（機密情報保護）。
- OpenAI API 呼び出し部分はリトライやフォールバック（失敗時は安全側の値で継続）を考慮して実装されていますが、実運用では API のレートやコストにも注意してください。
- プロセス優先度・CPU affinity は `psutil` を使って設定します。設定に失敗する場合はログ警告となり処理は継続します。
- DuckDB へ実データを投入して使う前に、`config/*.yaml` の設定を用意してください（`validate_config` が存在のみチェック・簡易パースチェックを行います）。

---

## サポート / 拡張ポイント

- Broker クライアントの実装はファクトリパターンで分離されているため、新しい接続方式（別証券会社／API）を追加しやすい設計です。
- ポートフォリオ構築ロジックは純粋関数群になっているため単体テストしやすく、バックテストや最適化が可能です。
- AI スコアのパイプラインはバッチ化されており、結果を ai_scores テーブルに保存することで downstream に利用できます。

---

README はここまでです。動作や導入について不明点があれば、実際の環境（OS、Python バージョン、利用する DB ファイルパス、OpenAI 利用の可否など）を教えてください。具体的なセットアップ手順や systemd/cron での運用例、Docker 化などの補助もできます。